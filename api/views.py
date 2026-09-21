from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from accounts.models import User
from workspaces.models import Workspace, WorkspaceMembership, WorkspaceInvitation
from projects.models import Project, Task
from billing.models import Plan, Subscription
from core.models import AuditLog, log_audit_event
from .serializers import (
    UserSerializer,
    WorkspaceSerializer,
    WorkspaceMemberSerializer,
    WorkspaceInviteSerializer,
    ProjectSerializer,
    TaskSerializer,
    AuditLogSerializer,
    PlanSerializer,
    SubscriptionSerializer,
)
from .permissions import IsWorkspaceMember, IsWorkspaceAdmin, IsWorkspaceOwner


class WorkspaceViewSet(viewsets.ModelViewSet):
    """
    Manage tenant Workspaces, RBAC memberships, and invitations.
    """
    serializer_class = WorkspaceSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'slug'

    def get_queryset(self):
        return Workspace.objects.filter(
            memberships__user=self.request.user
        ).select_related('owner', 'subscription__plan').distinct()

    def perform_create(self, serializer):
        with transaction.atomic():
            workspace = serializer.save(owner=self.request.user)
            # Create Owner membership
            WorkspaceMembership.objects.create(
                workspace=workspace,
                user=self.request.user,
                role=WorkspaceMembership.Role.OWNER
            )
            # Assign Default Free Plan
            free_plan, _ = Plan.objects.get_or_create(
                tier_code=Plan.Tier.FREE,
                defaults={'name': 'Free Starter', 'price_monthly': 0.00, 'max_members': 3, 'max_projects': 5}
            )
            Subscription.objects.create(
                workspace=workspace,
                plan=free_plan,
                status=Subscription.Status.ACTIVE
            )
            # Audit log
            log_audit_event(
                actor=self.request.user,
                action=AuditLog.Action.CREATE,
                resource_type='Workspace',
                resource_id=str(workspace.id),
                description=f"Created workspace '{workspace.name}' with Free tier",
                workspace=workspace
            )

    @action(detail=True, methods=['get', 'post'], permission_classes=[permissions.IsAuthenticated, IsWorkspaceMember])
    def members(self, request, slug=None):
        workspace = self.get_object()
        if request.method == 'GET':
            memberships = workspace.memberships.select_related('user').all()
            serializer = WorkspaceMemberSerializer(memberships, many=True)
            return Response(serializer.data)

        # POST: Add/Invite member
        if not workspace.is_admin_or_owner(request.user):
            return Response({'error': 'Only Workspace Admins can add members.'}, status=status.HTTP_403_FORBIDDEN)

        # Check subscription quota
        subscription = getattr(workspace, 'subscription', None)
        if subscription and not subscription.can_invite_member():
            return Response({
                'error': f"Seat limit reached ({subscription.plan.max_members} max). Please upgrade to Pro or Enterprise."
            }, status=status.HTTP_400_BAD_REQUEST)

        user_id = request.data.get('user_id')
        role = request.data.get('role', WorkspaceMembership.Role.MEMBER)
        target_user = get_object_or_404(User, pk=user_id)

        if WorkspaceMembership.objects.filter(workspace=workspace, user=target_user).exists():
            return Response({'error': 'User is already a member of this workspace.'}, status=status.HTTP_400_BAD_REQUEST)

        membership = WorkspaceMembership.objects.create(
            workspace=workspace,
            user=target_user,
            role=role
        )
        log_audit_event(
            actor=request.user,
            action=AuditLog.Action.ROLE_CHANGE,
            resource_type='WorkspaceMembership',
            resource_id=str(membership.id),
            description=f"Added {target_user.username} as {role}",
            workspace=workspace
        )
        return Response(WorkspaceMemberSerializer(membership).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsWorkspaceAdmin])
    def change_role(self, request, slug=None):
        workspace = self.get_object()
        user_id = request.data.get('user_id')
        new_role = request.data.get('role')

        if new_role not in WorkspaceMembership.Role.values:
            return Response({'error': 'Invalid role'}, status=status.HTTP_400_BAD_REQUEST)

        membership = get_object_or_404(WorkspaceMembership, workspace=workspace, user_id=user_id)
        if membership.role == WorkspaceMembership.Role.OWNER and request.user != workspace.owner:
            return Response({'error': 'Cannot alter role of the primary workspace owner.'}, status=status.HTTP_403_FORBIDDEN)

        old_role = membership.role
        membership.role = new_role
        membership.save()

        log_audit_event(
            actor=request.user,
            action=AuditLog.Action.ROLE_CHANGE,
            resource_type='WorkspaceMembership',
            resource_id=str(membership.id),
            description=f"Changed {membership.user.username} role from {old_role} to {new_role}",
            workspace=workspace
        )
        return Response(WorkspaceMemberSerializer(membership).data)


class ProjectViewSet(viewsets.ModelViewSet):
    """
    Manage projects within an isolated tenant workspace.
    """
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated, IsWorkspaceMember]

    def get_queryset(self):
        user = self.request.user
        queryset = Project.objects.filter(
            workspace__memberships__user=user
        ).select_related('workspace', 'created_by').prefetch_related('tasks')

        workspace_slug = self.request.query_params.get('workspace')
        if workspace_slug:
            queryset = queryset.filter(workspace__slug=workspace_slug)

        project_status = self.request.query_params.get('status')
        if project_status:
            queryset = queryset.filter(status=project_status)

        return queryset

    def perform_create(self, serializer):
        workspace_id = self.request.data.get('workspace')
        workspace = get_object_or_404(Workspace, pk=workspace_id, memberships__user=self.request.user)

        # Quota check
        subscription = getattr(workspace, 'subscription', None)
        if subscription and not subscription.can_create_project():
            raise serializers.ValidationError(
                f"Project limit reached ({subscription.plan.max_projects} max). Upgrade plan to create more."
            )

        project = serializer.save(workspace=workspace, created_by=self.request.user)
        log_audit_event(
            actor=self.request.user,
            action=AuditLog.Action.CREATE,
            resource_type='Project',
            resource_id=str(project.id),
            description=f"Created project '{project.name}'",
            workspace=workspace
        )


class TaskViewSet(viewsets.ModelViewSet):
    """
    Manage tasks, assignees, and kanban statuses across workspace projects.
    """
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated, IsWorkspaceMember]

    def get_queryset(self):
        user = self.request.user
        queryset = Task.objects.filter(
            workspace__memberships__user=user
        ).select_related('project', 'assignee', 'created_by', 'workspace')

        workspace_slug = self.request.query_params.get('workspace')
        if workspace_slug:
            queryset = queryset.filter(workspace__slug=workspace_slug)

        project_id = self.request.query_params.get('project')
        if project_id:
            queryset = queryset.filter(project_id=project_id)

        task_status = self.request.query_params.get('status')
        if task_status:
            queryset = queryset.filter(status=task_status)

        priority = self.request.query_params.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)

        return queryset

    def perform_create(self, serializer):
        project_id = self.request.data.get('project')
        project = get_object_or_404(
            Project,
            pk=project_id,
            workspace__memberships__user=self.request.user
        )
        task = serializer.save(
            project=project,
            workspace=project.workspace,
            created_by=self.request.user
        )
        log_audit_event(
            actor=self.request.user,
            action=AuditLog.Action.CREATE,
            resource_type='Task',
            resource_id=str(task.id),
            description=f"Created task '{task.title}' in project '{project.name}'",
            workspace=project.workspace
        )

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        task = self.get_object()
        new_status = request.data.get('status')
        if new_status not in Task.Status.values:
            return Response({'error': 'Invalid status choice'}, status=status.HTTP_400_BAD_REQUEST)

        old_status = task.status
        task.status = new_status
        task.save()

        log_audit_event(
            actor=request.user,
            action=AuditLog.Action.TASK_STATUS,
            resource_type='Task',
            resource_id=str(task.id),
            description=f"Updated task '{task.title}' status from {old_status} to {new_status}",
            workspace=task.workspace
        )
        return Response(TaskSerializer(task).data)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Immutable activity and compliance logs with tenant isolation and plan gating.
    """
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated, IsWorkspaceMember]

    def get_queryset(self):
        user = self.request.user
        queryset = AuditLog.objects.filter(
            workspace__memberships__user=user
        ).select_related('actor', 'workspace')

        workspace_slug = self.request.query_params.get('workspace')
        if workspace_slug:
            workspace = get_object_or_404(Workspace, slug=workspace_slug)
            subscription = getattr(workspace, 'subscription', None)
            # Enterprise/Pro feature gating demo:
            if subscription and not subscription.plan.has_audit_logs:
                # Return empty or subset
                return AuditLog.objects.none()
            queryset = queryset.filter(workspace=workspace)

        action_filter = self.request.query_params.get('action')
        if action_filter:
            queryset = queryset.filter(action=action_filter)

        return queryset


class BillingViewSet(viewsets.ViewSet):
    """
    Subscription tiers and mock checkout simulation.
    """
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def plans(self, request):
        plans = Plan.objects.filter(is_active=True)
        return Response(PlanSerializer(plans, many=True).data)

    @action(detail=False, methods=['post'])
    def upgrade_workspace(self, request):
        workspace_slug = request.data.get('workspace_slug')
        tier_code = request.data.get('tier_code')

        workspace = get_object_or_404(Workspace, slug=workspace_slug)
        if not workspace.is_admin_or_owner(request.user):
            return Response({'error': 'Only Workspace Owners or Admins can modify billing.'}, status=status.HTTP_403_FORBIDDEN)

        plan = get_object_or_404(Plan, tier_code=tier_code)
        subscription, _ = Subscription.objects.get_or_create(workspace=workspace, defaults={'plan': plan})
        old_plan_name = subscription.plan.name
        subscription.plan = plan
        subscription.status = Subscription.Status.ACTIVE
        subscription.current_period_end = timezone.now() + timezone.timedelta(days=30)
        subscription.save()

        log_audit_event(
            actor=request.user,
            action=AuditLog.Action.PLAN_CHANGE,
            resource_type='Subscription',
            resource_id=str(subscription.id),
            description=f"Upgraded plan from '{old_plan_name}' to '{plan.name}'",
            workspace=workspace
        )
        return Response({
            'message': f"Workspace successfully upgraded to {plan.name}!",
            'subscription': SubscriptionSerializer(subscription).data
        })
