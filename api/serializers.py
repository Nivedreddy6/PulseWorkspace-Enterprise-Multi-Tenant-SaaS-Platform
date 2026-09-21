from rest_framework import serializers
from accounts.models import User
from workspaces.models import Workspace, WorkspaceMembership, WorkspaceInvitation
from projects.models import Project, Task
from billing.models import Plan, Subscription
from core.models import AuditLog


class UserSerializer(serializers.ModelSerializer):
    display_name = serializers.ReadOnlyField()
    initials = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'display_name', 'initials', 'role_title', 'avatar_color']
        read_only_fields = ['id', 'display_name', 'initials']


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = ['id', 'name', 'tier_code', 'price_monthly', 'max_members', 'max_projects', 'has_audit_logs', 'has_api_access', 'has_custom_roles']


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)
    plan_id = serializers.PrimaryKeyRelatedField(
        queryset=Plan.objects.filter(is_active=True),
        source='plan',
        write_only=True,
        required=False
    )

    class Meta:
        model = Subscription
        fields = ['id', 'plan', 'plan_id', 'status', 'current_period_end', 'created_at']
        read_only_fields = ['id', 'status', 'current_period_end', 'created_at']


class WorkspaceMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), source='user', write_only=True)

    class Meta:
        model = WorkspaceMembership
        fields = ['id', 'user', 'user_id', 'role', 'joined_at']
        read_only_fields = ['id', 'joined_at']


class WorkspaceSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    member_count = serializers.ReadOnlyField()
    subscription = SubscriptionSerializer(read_only=True)
    user_role = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = ['id', 'name', 'slug', 'description', 'owner', 'member_count', 'subscription', 'user_role', 'created_at', 'updated_at']
        read_only_fields = ['id', 'slug', 'owner', 'member_count', 'subscription', 'user_role', 'created_at', 'updated_at']

    def get_user_role(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.get_user_role(request.user)
        return None


class WorkspaceInviteSerializer(serializers.ModelSerializer):
    invited_by = UserSerializer(read_only=True)

    class Meta:
        model = WorkspaceInvitation
        fields = ['id', 'email', 'role', 'token', 'status', 'invited_by', 'created_at', 'expires_at']
        read_only_fields = ['id', 'token', 'status', 'invited_by', 'created_at', 'expires_at']


class ProjectSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    total_tasks = serializers.ReadOnlyField()
    completed_tasks = serializers.ReadOnlyField()
    progress_percentage = serializers.ReadOnlyField()

    class Meta:
        model = Project
        fields = [
            'id', 'workspace', 'name', 'slug', 'description', 'status',
            'target_date', 'created_by', 'total_tasks', 'completed_tasks',
            'progress_percentage', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'created_by', 'total_tasks', 'completed_tasks', 'progress_percentage', 'created_at', 'updated_at']


class TaskSerializer(serializers.ModelSerializer):
    assignee_detail = UserSerializer(source='assignee', read_only=True)
    created_by_detail = UserSerializer(source='created_by', read_only=True)
    project_name = serializers.ReadOnlyField(source='project.name')

    class Meta:
        model = Task
        fields = [
            'id', 'workspace', 'project', 'project_name', 'title', 'description',
            'status', 'priority', 'assignee', 'assignee_detail',
            'due_date', 'created_by_detail', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'workspace', 'project_name', 'created_by_detail', 'created_at', 'updated_at']


class AuditLogSerializer(serializers.ModelSerializer):
    actor_detail = UserSerializer(source='actor', read_only=True)

    class Meta:
        model = AuditLog
        fields = ['id', 'actor', 'actor_detail', 'action', 'resource_type', 'resource_id', 'description', 'ip_address', 'metadata', 'created_at']
        read_only_fields = fields
