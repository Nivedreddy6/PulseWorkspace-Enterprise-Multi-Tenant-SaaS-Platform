from django.db import models


class Plan(models.Model):
    """
    Subscription tier specifications with feature gating and quota limits.
    """
    class Tier(models.TextChoices):
        FREE = 'FREE', 'Free Starter'
        PRO = 'PRO', 'Pro Growth'
        ENTERPRISE = 'ENTERPRISE', 'Enterprise Scale'

    name = models.CharField(max_length=60)
    tier_code = models.CharField(max_length=20, choices=Tier.choices, unique=True)
    price_monthly = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    max_members = models.PositiveIntegerField(default=3)
    max_projects = models.PositiveIntegerField(default=5)
    has_audit_logs = models.BooleanField(default=False)
    has_api_access = models.BooleanField(default=True)
    has_custom_roles = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['price_monthly']

    def __str__(self):
        return f"{self.name} (${self.price_monthly}/mo)"


class Subscription(models.Model):
    """
    Active subscription linking a Workspace tenant to its Plan tier.
    """
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        TRIALING = 'TRIALING', 'Trialing'
        PAST_DUE = 'PAST_DUE', 'Past Due'
        CANCELED = 'CANCELED', 'Canceled'

    workspace = models.OneToOneField(
        'workspaces.Workspace',
        on_delete=models.CASCADE,
        related_name='subscription'
    )
    plan = models.ForeignKey(
        Plan,
        on_delete=models.PROTECT,
        related_name='subscriptions'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    current_period_end = models.DateTimeField(null=True, blank=True)
    stripe_customer_id = models.CharField(max_length=120, blank=True, default='')
    stripe_subscription_id = models.CharField(max_length=120, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.workspace.name} -> {self.plan.name} ({self.status})"

    def can_invite_member(self):
        """Validates if workspace member quota has been reached."""
        current_members = self.workspace.memberships.count()
        return current_members < self.plan.max_members

    def can_create_project(self):
        """Validates if workspace project quota has been reached."""
        current_projects = self.workspace.projects.count()
        return current_projects < self.plan.max_projects
