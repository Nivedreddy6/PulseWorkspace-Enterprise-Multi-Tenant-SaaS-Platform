import logging
from django.conf import settings
from django.db import models

logger = logging.getLogger(__name__)


class AuditLog(models.Model):
    """
    Enterprise-grade immutable audit trail.
    Tracks critical workspace actions, security mutations, and compliance events.
    """
    class Action(models.TextChoices):
        CREATE = 'CREATE', 'Create'
        UPDATE = 'UPDATE', 'Update'
        DELETE = 'DELETE', 'Delete'
        ROLE_CHANGE = 'ROLE_CHANGE', 'Role Change'
        MEMBER_INVITE = 'MEMBER_INVITE', 'Member Invite'
        MEMBER_REMOVE = 'MEMBER_REMOVE', 'Member Remove'
        PLAN_CHANGE = 'PLAN_CHANGE', 'Subscription Plan Change'
        TASK_STATUS = 'TASK_STATUS', 'Task Status Update'
        LOGIN = 'LOGIN', 'User Login'

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    workspace = models.ForeignKey(
        'workspaces.Workspace',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=32, choices=Action.choices, db_index=True)
    resource_type = models.CharField(max_length=64, db_index=True)
    resource_id = models.CharField(max_length=64, blank=True, default='')
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['workspace', '-created_at']),
            models.Index(fields=['resource_type', 'resource_id']),
        ]

    def __str__(self):
        actor_name = self.actor.username if self.actor else 'System'
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {actor_name} -> {self.action} on {self.resource_type}"


def log_audit_event(
    actor=None,
    action=AuditLog.Action.UPDATE,
    resource_type='General',
    description='',
    workspace=None,
    resource_id='',
    ip_address=None,
    metadata=None
):
    """
    Safe utility function to record an immutable audit log entry.
    """
    try:
        return AuditLog.objects.create(
            actor=actor,
            workspace=workspace,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id),
            description=description,
            ip_address=ip_address,
            metadata=metadata or {}
        )
    except Exception as e:
        logger.error("Failed to record audit log: %s", e)
        return None
