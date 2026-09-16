import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.tenancy.models import Tenant


class ImmutableAuditQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("Audit events are append-only and cannot be updated.")

    def delete(self):
        raise ValidationError("Audit events are append-only and cannot be deleted.")


class AuditEventManager(models.Manager.from_queryset(ImmutableAuditQuerySet)):
    def bulk_create(self, objs, **kwargs):
        raise ValidationError("Use record_audit_event() so audit-chain integrity is preserved.")

    def bulk_update(self, objs, fields, **kwargs):
        raise ValidationError("Audit events are append-only and cannot be bulk-updated.")


class AuditEvent(models.Model):
    class Outcome(models.TextChoices):
        SUCCESS = "success", "Success"
        FAILURE = "failure", "Failure"
        DENIED = "denied", "Denied"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, null=True, blank=True, on_delete=models.PROTECT, related_name="audit_events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    actor_username = models.CharField(max_length=150, blank=True)
    action = models.CharField(max_length=100)
    category = models.CharField(max_length=64, default="application")
    outcome = models.CharField(max_length=16, choices=Outcome.choices, default=Outcome.SUCCESS)
    object_type = models.CharField(max_length=100)
    object_id = models.UUIDField(null=True, blank=True)
    object_repr = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    old_data = models.JSONField(default=dict, blank=True)
    new_data = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    http_method = models.CharField(max_length=12, blank=True)
    path = models.CharField(max_length=500, blank=True)
    request_id = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    previous_hash = models.CharField(max_length=64, blank=True, editable=False)
    event_hash = models.CharField(max_length=64, blank=True, editable=False, db_index=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False, db_index=True)

    objects = AuditEventManager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "created_at"]),
            models.Index(fields=["action", "created_at"]),
            models.Index(fields=["tenant", "actor", "created_at"]),
            models.Index(fields=["tenant", "object_type", "object_id"]),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Audit events are append-only and cannot be modified.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Audit events are append-only and cannot be deleted.")
