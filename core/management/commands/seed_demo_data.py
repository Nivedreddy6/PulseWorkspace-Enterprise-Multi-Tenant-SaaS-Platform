from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from accounts.models import User
from workspaces.models import Workspace, WorkspaceMembership
from projects.models import Project, Task
from billing.models import Plan, Subscription
from core.models import AuditLog, log_audit_event


class Command(BaseCommand):
    help = 'Seeds realistic enterprise demo data for PulseWorkspace showcase'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding PulseWorkspace enterprise demo data..."))

        with transaction.atomic():
            # 1. Ensure Subscription Plans exist
            free_plan, _ = Plan.objects.get_or_create(
                tier_code=Plan.Tier.FREE,
                defaults={
                    'name': 'Free Starter',
                    'price_monthly': 0.00,
                    'max_members': 3,
                    'max_projects': 5,
                    'has_audit_logs': False,
                    'has_api_access': True,
                    'has_custom_roles': False,
                }
            )
            pro_plan, _ = Plan.objects.get_or_create(
                tier_code=Plan.Tier.PRO,
                defaults={
                    'name': 'Pro Growth',
                    'price_monthly': 49.00,
                    'max_members': 15,
                    'max_projects': 25,
                    'has_audit_logs': True,
                    'has_api_access': True,
                    'has_custom_roles': True,
                }
            )
            enterprise_plan, _ = Plan.objects.get_or_create(
                tier_code=Plan.Tier.ENTERPRISE,
                defaults={
                    'name': 'Enterprise Scale',
                    'price_monthly': 199.00,
                    'max_members': 100,
                    'max_projects': 500,
                    'has_audit_logs': True,
                    'has_api_access': True,
                    'has_custom_roles': True,
                }
            )

            # 2. Create standard users
            admin_user, _ = User.objects.get_or_create(
                username='admin',
                defaults={
                    'email': 'admin@acmecloud.io',
                    'first_name': 'David',
                    'last_name': 'Chen',
                    'role_title': 'Chief Architect & Owner',
                    'avatar_color': '#4f46e5',
                    'is_staff': True,
                    'is_superuser': True,
                }
            )
            admin_user.set_password('password123')
            admin_user.save()

            sarah_user, _ = User.objects.get_or_create(
                username='sarah_lead',
                defaults={
                    'email': 'sarah@acmecloud.io',
                    'first_name': 'Sarah',
                    'last_name': 'Connor',
                    'role_title': 'VP of Engineering',
                    'avatar_color': '#06b6d4',
                }
            )
            sarah_user.set_password('password123')
            sarah_user.save()

            alex_user, _ = User.objects.get_or_create(
                username='alex_dev',
                defaults={
                    'email': 'alex@acmecloud.io',
                    'first_name': 'Alex',
                    'last_name': 'Mercer',
                    'role_title': 'Senior Backend Engineer',
                    'avatar_color': '#10b981',
                }
            )
            alex_user.set_password('password123')
            alex_user.save()

            # 3. Create Workspaces
            acme_ws, _ = Workspace.objects.get_or_create(
                slug='acme-cloud-technologies',
                defaults={
                    'name': 'Acme Cloud Technologies',
                    'owner': admin_user,
                    'description': 'Enterprise infrastructure, distributed systems, and real-time APIs.',
                }
            )

            apex_ws, _ = Workspace.objects.get_or_create(
                slug='apex-robotics',
                defaults={
                    'name': 'Apex Robotics',
                    'owner': admin_user,
                    'description': 'Autonomous fleet operations and robotics software.',
                }
            )

            # Subscriptions
            Subscription.objects.update_or_create(
                workspace=acme_ws,
                defaults={'plan': pro_plan, 'status': Subscription.Status.ACTIVE}
            )
            Subscription.objects.update_or_create(
                workspace=apex_ws,
                defaults={'plan': free_plan, 'status': Subscription.Status.ACTIVE}
            )

            # Memberships in Acme
            WorkspaceMembership.objects.get_or_create(
                workspace=acme_ws,
                user=admin_user,
                defaults={'role': WorkspaceMembership.Role.OWNER}
            )
            WorkspaceMembership.objects.get_or_create(
                workspace=acme_ws,
                user=sarah_user,
                defaults={'role': WorkspaceMembership.Role.ADMIN}
            )
            WorkspaceMembership.objects.get_or_create(
                workspace=acme_ws,
                user=alex_user,
                defaults={'role': WorkspaceMembership.Role.MEMBER}
            )

            # Membership in Apex
            WorkspaceMembership.objects.get_or_create(
                workspace=apex_ws,
                user=admin_user,
                defaults={'role': WorkspaceMembership.Role.OWNER}
            )

            # 4. Create Projects
            p1, _ = Project.objects.get_or_create(
                workspace=acme_ws,
                slug='cloud-api-gateway',
                defaults={
                    'name': 'Cloud API Gateway v2',
                    'description': 'High-performance distributed API gateway supporting rate-limiting and token verification.',
                    'status': Project.Status.ACTIVE,
                    'target_date': timezone.now().date() + timedelta(days=21),
                    'created_by': admin_user
                }
            )

            p2, _ = Project.objects.get_or_create(
                workspace=acme_ws,
                slug='real-time-analytics',
                defaults={
                    'name': 'Real-Time Analytics Pipeline',
                    'description': 'Event streaming and anomaly detection pipeline with automated alerting.',
                    'status': Project.Status.PLANNING,
                    'target_date': timezone.now().date() + timedelta(days=45),
                    'created_by': sarah_user
                }
            )

            # 5. Create Tasks
            Task.objects.get_or_create(
                workspace=acme_ws,
                project=p1,
                title='Implement Token Bucket Rate Limiter in Redis',
                defaults={
                    'description': 'Enforce per-tenant throughput throttling to protect downstream microservices.',
                    'status': Task.Status.DONE,
                    'priority': Task.Priority.URGENT,
                    'assignee': alex_user,
                    'due_date': timezone.now().date() - timedelta(days=2),
                    'created_by': admin_user
                }
            )

            Task.objects.get_or_create(
                workspace=acme_ws,
                project=p1,
                title='Design OpenAPI 3.0 Spectacular Schemas',
                defaults={
                    'description': 'Expose self-documenting Swagger UI with JWT and token auth scopes.',
                    'status': Task.Status.IN_PROGRESS,
                    'priority': Task.Priority.HIGH,
                    'assignee': sarah_user,
                    'due_date': timezone.now().date() + timedelta(days=5),
                    'created_by': admin_user
                }
            )

            Task.objects.get_or_create(
                workspace=acme_ws,
                project=p1,
                title='Audit Trail Export to S3 / Cloud Storage',
                defaults={
                    'description': 'Enable scheduled batch dumps of immutable audit events for external compliance audits.',
                    'status': Task.Status.IN_REVIEW,
                    'priority': Task.Priority.MEDIUM,
                    'assignee': alex_user,
                    'due_date': timezone.now().date() + timedelta(days=8),
                    'created_by': sarah_user
                }
            )

            Task.objects.get_or_create(
                workspace=acme_ws,
                project=p1,
                title='Unit & Integration Test Matrix with Mock Fixtures',
                defaults={
                    'description': 'Increase test coverage for multi-tenant isolation and role-based permissions.',
                    'status': Task.Status.TODO,
                    'priority': Task.Priority.HIGH,
                    'assignee': alex_user,
                    'due_date': timezone.now().date() + timedelta(days=12),
                    'created_by': admin_user
                }
            )

            Task.objects.get_or_create(
                workspace=acme_ws,
                project=p2,
                title='Kafka Consumer Group Optimization',
                defaults={
                    'description': 'Benchmark partition assignment latency under peak ingestion workloads.',
                    'status': Task.Status.TODO,
                    'priority': Task.Priority.LOW,
                    'assignee': sarah_user,
                    'due_date': timezone.now().date() + timedelta(days=30),
                    'created_by': sarah_user
                }
            )

            # 6. Create realistic Audit Logs
            log_audit_event(
                actor=admin_user,
                action=AuditLog.Action.CREATE,
                resource_type='Workspace',
                resource_id=str(acme_ws.id),
                description="Initialized workspace 'Acme Cloud Technologies'",
                workspace=acme_ws
            )
            log_audit_event(
                actor=admin_user,
                action=AuditLog.Action.ROLE_CHANGE,
                resource_type='WorkspaceMembership',
                resource_id=str(sarah_user.id),
                description=f"Promoted {sarah_user.username} to Workspace Admin",
                workspace=acme_ws
            )
            log_audit_event(
                actor=admin_user,
                action=AuditLog.Action.PLAN_CHANGE,
                resource_type='Subscription',
                resource_id=str(acme_ws.subscription.id),
                description="Upgraded plan from 'Free Starter' to 'Pro Growth'",
                workspace=acme_ws
            )
            log_audit_event(
                actor=alex_user,
                action=AuditLog.Action.TASK_STATUS,
                resource_type='Task',
                resource_id='1',
                description="Completed 'Implement Token Bucket Rate Limiter in Redis'",
                workspace=acme_ws
            )

        self.stdout.write(self.style.SUCCESS("Successfully seeded demo data!"))
        self.stdout.write(self.style.SUCCESS("Demo Logins: admin / password123, sarah_lead / password123, alex_dev / password123"))
