from rest_framework import permissions
from workspaces.models import Workspace, WorkspaceMembership


class IsWorkspaceMember(permissions.BasePermission):
    """
    Object-level or view-level permission to ensure user belongs to the tenant workspace.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        workspace_slug = view.kwargs.get('workspace_slug') or request.query_params.get('workspace')
        if not workspace_slug:
            return True  # Handled at query filter level
        return WorkspaceMembership.objects.filter(
            workspace__slug=workspace_slug,
            user=request.user
        ).exists()

    def has_object_permission(self, request, view, obj):
        workspace = getattr(obj, 'workspace', obj if isinstance(obj, Workspace) else None)
        if not workspace:
            return True
        return WorkspaceMembership.objects.filter(
            workspace=workspace,
            user=request.user
        ).exists()


class IsWorkspaceAdmin(permissions.BasePermission):
    """
    Ensures user is an OWNER or ADMIN of the target workspace.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        workspace_slug = view.kwargs.get('workspace_slug') or request.query_params.get('workspace')
        if not workspace_slug:
            return True
        return WorkspaceMembership.objects.filter(
            workspace__slug=workspace_slug,
            user=request.user,
            role__in=[WorkspaceMembership.Role.OWNER, WorkspaceMembership.Role.ADMIN]
        ).exists()

    def has_object_permission(self, request, view, obj):
        workspace = getattr(obj, 'workspace', obj if isinstance(obj, Workspace) else None)
        if not workspace:
            return False
        return WorkspaceMembership.objects.filter(
            workspace=workspace,
            user=request.user,
            role__in=[WorkspaceMembership.Role.OWNER, WorkspaceMembership.Role.ADMIN]
        ).exists()


class IsWorkspaceOwner(permissions.BasePermission):
    """
    Strict permission allowing only the tenant Workspace Owner.
    """
    def has_object_permission(self, request, view, obj):
        workspace = getattr(obj, 'workspace', obj if isinstance(obj, Workspace) else None)
        if not workspace:
            return False
        return workspace.owner == request.user or WorkspaceMembership.objects.filter(
            workspace=workspace,
            user=request.user,
            role=WorkspaceMembership.Role.OWNER
        ).exists()
