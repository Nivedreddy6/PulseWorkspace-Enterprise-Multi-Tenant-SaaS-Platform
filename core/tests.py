from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from accounts.models import User
from workspaces.models import Workspace, WorkspaceMembership
from projects.models import Project, Task
from billing.models import Plan, Subscription
from core.models import AuditLog


class MultiTenantIsolationAndRBACTest(APITestCase):
    def setUp(self):
        # Plans
        self.free_plan = Plan.objects.create(
            name='Free Starter',
            tier_code=Plan.Tier.FREE,
            max_members=2,
            max_projects=2
        )
        self.pro_plan = Plan.objects.create(
            name='Pro Growth',
            tier_code=Plan.Tier.PRO,
            max_members=15,
            max_projects=25,
            has_audit_logs=True
        )

        # Users
        self.owner = User.objects.create_user(username='tenant_owner', password='password123')
        self.admin = User.objects.create_user(username='tenant_admin', password='password123')
        self.member = User.objects.create_user(username='tenant_member', password='password123')
        self.external_user = User.objects.create_user(username='outsider', password='password123')

        # Workspace 1 (Tenant A)
        self.ws_a = Workspace.objects.create(name='Tenant A Corp', owner=self.owner)
        Subscription.objects.create(workspace=self.ws_a, plan=self.free_plan)
        WorkspaceMembership.objects.create(workspace=self.ws_a, user=self.owner, role=WorkspaceMembership.Role.OWNER)
        WorkspaceMembership.objects.create(workspace=self.ws_a, user=self.admin, role=WorkspaceMembership.Role.ADMIN)

        # Workspace 2 (Tenant B)
        self.ws_b = Workspace.objects.create(name='Tenant B Corp', owner=self.external_user)
        Subscription.objects.create(workspace=self.ws_b, plan=self.free_plan)
        WorkspaceMembership.objects.create(workspace=self.ws_b, user=self.external_user, role=WorkspaceMembership.Role.OWNER)

        # Project & Task in Tenant A
        self.proj_a = Project.objects.create(workspace=self.ws_a, name='Secret Project A', created_by=self.owner)
        self.task_a = Task.objects.create(workspace=self.ws_a, project=self.proj_a, title='Secret Task A', created_by=self.owner)

    def test_tenant_isolation_prevents_unauthorized_data_access(self):
        """External user in Tenant B cannot query data from Tenant A (HTTP 403 Forbidden)."""
        self.client.force_authenticate(user=self.external_user)
        
        # Query tasks endpoint targeting Tenant A
        response = self.client.get(f'/api/v1/tasks/?workspace={self.ws_a.slug}')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_rbac_admin_can_invite_or_change_roles(self):
        """Workspace Admin can alter member roles."""
        self.client.force_authenticate(user=self.admin)

        # First add member to ws_a
        WorkspaceMembership.objects.create(workspace=self.ws_a, user=self.member, role=WorkspaceMembership.Role.MEMBER)

        # Admin changes member to VIEWER
        response = self.client.post(f'/api/v1/workspaces/{self.ws_a.slug}/change_role/', {
            'user_id': self.member.id,
            'role': WorkspaceMembership.Role.VIEWER
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        membership = WorkspaceMembership.objects.get(workspace=self.ws_a, user=self.member)
        self.assertEqual(membership.role, WorkspaceMembership.Role.VIEWER)

    def test_audit_log_recorded_on_task_status_update(self):
        """Task status transition creates an immutable AuditLog."""
        self.client.force_authenticate(user=self.owner)
        initial_log_count = AuditLog.objects.filter(workspace=self.ws_a).count()

        response = self.client.post(f'/api/v1/tasks/{self.task_a.id}/update_status/', {
            'status': Task.Status.DONE
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        new_log_count = AuditLog.objects.filter(workspace=self.ws_a).count()
        self.assertEqual(new_log_count, initial_log_count + 1)
        
        latest_log = AuditLog.objects.filter(workspace=self.ws_a).first()
        self.assertEqual(latest_log.action, AuditLog.Action.TASK_STATUS)

    def test_billing_quota_enforcement(self):
        """Free plan seat limit prevents adding excess members beyond max_members quota."""
        # ws_a already has owner and admin (2 members), max_members = 2
        subscription = self.ws_a.subscription
        self.assertFalse(subscription.can_invite_member())
