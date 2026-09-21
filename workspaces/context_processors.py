from .models import Workspace, WorkspaceMembership


def active_workspace_context(request):
    """
    Supplies the active tenant workspace and role context to all templates.
    """
    if not request.user.is_authenticated:
        return {
            'active_workspace': None,
            'user_workspaces': [],
            'active_membership': None,
            'is_workspace_admin': False,
            'is_workspace_owner': False,
            'active_plan': None,
        }

    memberships = (
        WorkspaceMembership.objects
        .filter(user=request.user)
        .select_related('workspace', 'workspace__subscription__plan')
    )
    user_workspaces = [m.workspace for m in memberships]

    active_slug = request.session.get('active_workspace_slug')
    active_membership = None

    if active_slug:
        active_membership = next((m for m in memberships if m.workspace.slug == active_slug), None)

    if not active_membership and memberships:
        active_membership = memberships[0]
        request.session['active_workspace_slug'] = active_membership.workspace.slug

    active_workspace = active_membership.workspace if active_membership else None
    role = active_membership.role if active_membership else None
    subscription = getattr(active_workspace, 'subscription', None) if active_workspace else None

    return {
        'active_workspace': active_workspace,
        'user_workspaces': user_workspaces,
        'active_membership': active_membership,
        'user_workspace_role': role,
        'is_workspace_admin': role in (WorkspaceMembership.Role.OWNER, WorkspaceMembership.Role.ADMIN),
        'is_workspace_owner': role == WorkspaceMembership.Role.OWNER,
        'active_plan': subscription.plan if subscription else None,
    }
