from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from accounts.models import User
from workspaces.models import Workspace, WorkspaceMembership, WorkspaceInvitation
from projects.models import Project, Task
from billing.models import Plan, Subscription
from core.models import AuditLog, log_audit_event


def get_current_workspace(request):
    slug = request.session.get('active_workspace_slug')
    memberships = WorkspaceMembership.objects.filter(user=request.user).select_related('workspace', 'workspace__subscription__plan')
    if slug:
        mem = next((m for m in memberships if m.workspace.slug == slug), None)
        if mem:
            return mem.workspace, mem
    if memberships.exists():
        mem = memberships.first()
        request.session['active_workspace_slug'] = mem.workspace.slug
        return mem.workspace, mem
    return None, None


@login_required
def dashboard_view(request):
    workspace, membership = get_current_workspace(request)
    if not workspace:
        return render(request, 'core/no_workspace.html')

    projects = Project.objects.filter(workspace=workspace).prefetch_related('tasks')
    tasks = Task.objects.filter(workspace=workspace).select_related('project', 'assignee')
    recent_tasks = tasks.order_by('-created_at')[:6]
    audit_logs = AuditLog.objects.filter(workspace=workspace).select_related('actor')[:6]

    total_projects = projects.count()
    total_tasks = tasks.count()
    completed_tasks = tasks.filter(status=Task.Status.DONE).count()
    pending_tasks = total_tasks - completed_tasks
    members_count = workspace.memberships.count()

    subscription = getattr(workspace, 'subscription', None)

    context = {
        'workspace': workspace,
        'membership': membership,
        'projects': projects[:4],
        'recent_tasks': recent_tasks,
        'audit_logs': audit_logs,
        'total_projects': total_projects,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'pending_tasks': pending_tasks,
        'members_count': members_count,
        'subscription': subscription,
    }
    return render(request, 'core/dashboard.html', context)


@login_required
def switch_workspace_view(request, slug):
    membership = WorkspaceMembership.objects.filter(user=request.user, workspace__slug=slug).first()
    if membership:
        request.session['active_workspace_slug'] = slug
        messages.success(request, f"Switched to workspace: {membership.workspace.name}")
    else:
        messages.error(request, "Access denied to that workspace.")
    return redirect(request.META.get('HTTP_REFERER') or 'dashboard')


@login_required
def projects_view(request):
    workspace, membership = get_current_workspace(request)
    if not workspace:
        return redirect('dashboard')

    if request.method == 'POST':
        if not workspace.is_admin_or_owner(request.user):
            messages.error(request, "Only Admins can create projects.")
            return redirect('projects')

        subscription = getattr(workspace, 'subscription', None)
        if subscription and not subscription.can_create_project():
            messages.error(request, f"Project limit reached ({subscription.plan.max_projects} max). Upgrade your plan to create more projects!")
            return redirect('projects')

        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        target_date = request.POST.get('target_date') or None

        if name:
            project = Project.objects.create(
                workspace=workspace,
                name=name,
                description=description,
                target_date=target_date,
                created_by=request.user
            )
            log_audit_event(
                actor=request.user,
                action=AuditLog.Action.CREATE,
                resource_type='Project',
                resource_id=str(project.id),
                description=f"Created project '{project.name}'",
                workspace=workspace
            )
            messages.success(request, f"Project '{project.name}' created successfully!")
            return redirect('projects')

    projects = Project.objects.filter(workspace=workspace).prefetch_related('tasks').order_by('-created_at')
    subscription = getattr(workspace, 'subscription', None)
    return render(request, 'core/projects.html', {
        'workspace': workspace,
        'projects': projects,
        'subscription': subscription,
    })


@login_required
def project_detail_view(request, slug):
    workspace, membership = get_current_workspace(request)
    project = get_object_or_404(Project, workspace=workspace, slug=slug)

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        status_val = request.POST.get('status', Task.Status.TODO)
        priority = request.POST.get('priority', Task.Priority.MEDIUM)
        assignee_id = request.POST.get('assignee_id')
        due_date = request.POST.get('due_date') or None

        assignee = User.objects.filter(pk=assignee_id).first() if assignee_id else None

        if title:
            task = Task.objects.create(
                workspace=workspace,
                project=project,
                title=title,
                description=description,
                status=status_val,
                priority=priority,
                assignee=assignee,
                due_date=due_date,
                created_by=request.user
            )
            log_audit_event(
                actor=request.user,
                action=AuditLog.Action.CREATE,
                resource_type='Task',
                resource_id=str(task.id),
                description=f"Created task '{task.title}' in project '{project.name}'",
                workspace=workspace
            )
            messages.success(request, f"Task '{task.title}' added!")
            return redirect('project_detail', slug=project.slug)

    tasks = project.tasks.select_related('assignee').order_by('-created_at')
    members = workspace.memberships.select_related('user').all()

    return render(request, 'core/project_detail.html', {
        'workspace': workspace,
        'project': project,
        'tasks': tasks,
        'members': members,
    })


@login_required
def kanban_view(request):
    workspace, _ = get_current_workspace(request)
    if not workspace:
        return redirect('dashboard')

    tasks = Task.objects.filter(workspace=workspace).select_related('project', 'assignee')
    projects = Project.objects.filter(workspace=workspace)
    members = workspace.memberships.select_related('user').all()

    kanban_columns = {
        'TODO': tasks.filter(status=Task.Status.TODO),
        'IN_PROGRESS': tasks.filter(status=Task.Status.IN_PROGRESS),
        'IN_REVIEW': tasks.filter(status=Task.Status.IN_REVIEW),
        'DONE': tasks.filter(status=Task.Status.DONE),
    }

    return render(request, 'core/kanban.html', {
        'workspace': workspace,
        'kanban_columns': kanban_columns,
        'projects': projects,
        'members': members,
    })


@login_required
@require_POST
def update_task_status_ajax(request, task_id):
    workspace, _ = get_current_workspace(request)
    task = get_object_or_404(Task, pk=task_id, workspace=workspace)
    new_status = request.POST.get('status')

    if new_status in Task.Status.values:
        old_status = task.status
        task.status = new_status
        task.save()
        log_audit_event(
            actor=request.user,
            action=AuditLog.Action.TASK_STATUS,
            resource_type='Task',
            resource_id=str(task.id),
            description=f"Updated task '{task.title}' status from {old_status} to {new_status}",
            workspace=workspace
        )
        return JsonResponse({'success': True, 'new_status': new_status})
    return JsonResponse({'error': 'Invalid status'}, status=400)


@login_required
def team_view(request):
    workspace, membership = get_current_workspace(request)
    if not workspace:
        return redirect('dashboard')

    if request.method == 'POST':
        action_type = request.POST.get('action_type')

        if action_type == 'invite':
            if not workspace.is_admin_or_owner(request.user):
                messages.error(request, "Only Admins or Owners can invite members.")
                return redirect('team')

            subscription = getattr(workspace, 'subscription', None)
            if subscription and not subscription.can_invite_member():
                messages.error(request, f"Seat limit reached ({subscription.plan.max_members} max). Upgrade your plan to add more members!")
                return redirect('team')

            email = request.POST.get('email', '').strip()
            role = request.POST.get('role', WorkspaceMembership.Role.MEMBER)

            # Check if user already exists
            existing_user = User.objects.filter(email=email).first()
            if existing_user:
                if WorkspaceMembership.objects.filter(workspace=workspace, user=existing_user).exists():
                    messages.error(request, f"{email} is already in this workspace.")
                else:
                    new_mem = WorkspaceMembership.objects.create(workspace=workspace, user=existing_user, role=role)
                    log_audit_event(
                        actor=request.user,
                        action=AuditLog.Action.ROLE_CHANGE,
                        resource_type='WorkspaceMembership',
                        resource_id=str(new_mem.id),
                        description=f"Added member {existing_user.username} as {role}",
                        workspace=workspace
                    )
                    messages.success(request, f"Added {existing_user.display_name} to the workspace!")
            else:
                invitation = WorkspaceInvitation.objects.create(
                    workspace=workspace,
                    email=email,
                    role=role,
                    invited_by=request.user
                )
                log_audit_event(
                    actor=request.user,
                    action=AuditLog.Action.MEMBER_INVITE,
                    resource_type='WorkspaceInvitation',
                    resource_id=str(invitation.id),
                    description=f"Sent invitation to {email} ({role})",
                    workspace=workspace
                )
                messages.success(request, f"Invitation created for {email}! (Token: {str(invitation.token)[:8]}...)")

            return redirect('team')

        elif action_type == 'change_role':
            if not workspace.is_admin_or_owner(request.user):
                messages.error(request, "Permission denied.")
                return redirect('team')

            member_id = request.POST.get('membership_id')
            new_role = request.POST.get('role')
            target_mem = get_object_or_404(WorkspaceMembership, pk=member_id, workspace=workspace)

            if target_mem.role == WorkspaceMembership.Role.OWNER and request.user != workspace.owner:
                messages.error(request, "Cannot alter the role of the workspace owner.")
                return redirect('team')

            old_role = target_mem.role
            target_mem.role = new_role
            target_mem.save()

            log_audit_event(
                actor=request.user,
                action=AuditLog.Action.ROLE_CHANGE,
                resource_type='WorkspaceMembership',
                resource_id=str(target_mem.id),
                description=f"Changed {target_mem.user.username} role from {old_role} to {new_role}",
                workspace=workspace
            )
            messages.success(request, f"Updated {target_mem.user.username}'s role to {new_role}.")
            return redirect('team')

    members = workspace.memberships.select_related('user').all()
    invitations = workspace.invitations.filter(status=WorkspaceInvitation.Status.PENDING)
    subscription = getattr(workspace, 'subscription', None)

    return render(request, 'core/team.html', {
        'workspace': workspace,
        'members': members,
        'invitations': invitations,
        'subscription': subscription,
    })


@login_required
def audit_logs_view(request):
    workspace, _ = get_current_workspace(request)
    if not workspace:
        return redirect('dashboard')

    subscription = getattr(workspace, 'subscription', None)
    logs = AuditLog.objects.filter(workspace=workspace).select_related('actor')

    action_filter = request.GET.get('action')
    if action_filter:
        logs = logs.filter(action=action_filter)

    return render(request, 'core/audit_logs.html', {
        'workspace': workspace,
        'subscription': subscription,
        'logs': logs[:50],
        'action_choices': AuditLog.Action.choices,
        'selected_action': action_filter or '',
    })


@login_required
def billing_view(request):
    workspace, _ = get_current_workspace(request)
    if not workspace:
        return redirect('dashboard')

    subscription = getattr(workspace, 'subscription', None)
    plans = Plan.objects.filter(is_active=True).order_by('price_monthly')

    if request.method == 'POST':
        if not workspace.is_admin_or_owner(request.user):
            messages.error(request, "Only Admins or Owners can modify subscriptions.")
            return redirect('billing')

        tier_code = request.POST.get('tier_code')
        target_plan = get_object_or_404(Plan, tier_code=tier_code)

        if subscription:
            old_name = subscription.plan.name
            subscription.plan = target_plan
            subscription.status = Subscription.Status.ACTIVE
            subscription.current_period_end = timezone.now() + timezone.timedelta(days=30)
            subscription.save()

            log_audit_event(
                actor=request.user,
                action=AuditLog.Action.PLAN_CHANGE,
                resource_type='Subscription',
                resource_id=str(subscription.id),
                description=f"Upgraded subscription from '{old_name}' to '{target_plan.name}'",
                workspace=workspace
            )
            messages.success(request, f"Successfully upgraded workspace to {target_plan.name}!")
        return redirect('billing')

    return render(request, 'core/billing.html', {
        'workspace': workspace,
        'subscription': subscription,
        'plans': plans,
    })
