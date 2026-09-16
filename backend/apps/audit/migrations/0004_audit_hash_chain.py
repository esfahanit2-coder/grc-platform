import hashlib
import json

from django.core.serializers.json import DjangoJSONEncoder
from django.db import migrations, models
from django.utils import timezone


def _canonical_payload(event, previous_hash):
    return {
        "id": str(event.id),
        "tenant_id": str(event.tenant_id) if event.tenant_id else None,
        "actor_username": event.actor_username,
        "action": event.action,
        "category": event.category,
        "outcome": event.outcome,
        "object_type": event.object_type,
        "object_id": str(event.object_id) if event.object_id else None,
        "object_repr": event.object_repr,
        "metadata": event.metadata or {},
        "old_data": event.old_data or {},
        "new_data": event.new_data or {},
        "ip_address": str(event.ip_address) if event.ip_address else None,
        "user_agent": event.user_agent,
        "http_method": event.http_method,
        "path": event.path,
        "request_id": str(event.request_id),
        "created_at": event.created_at.isoformat(),
        "previous_hash": previous_hash,
    }


def _digest(event, previous_hash):
    encoded = json.dumps(
        _canonical_payload(event, previous_hash),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        cls=DjangoJSONEncoder,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def backfill_hash_chain(apps, schema_editor):
    AuditEvent = apps.get_model("audit", "AuditEvent")
    alias = schema_editor.connection.alias
    tenant_ids = list(
        AuditEvent.objects.using(alias)
        .exclude(tenant_id__isnull=True)
        .values_list("tenant_id", flat=True)
        .distinct()
    )
    for tenant_id in [None, *tenant_ids]:
        previous_hash = ""
        events = (
            AuditEvent.objects.using(alias)
            .filter(tenant_id=tenant_id)
            .order_by("created_at", "id")
        )
        for event in events.iterator():
            event_hash = _digest(event, previous_hash)
            AuditEvent.objects.using(alias).filter(pk=event.pk).update(
                previous_hash=previous_hash,
                event_hash=event_hash,
            )
            previous_hash = event_hash


class Migration(migrations.Migration):
    dependencies = [
        ("audit", "0003_sync_index_names"),
    ]

    operations = [
        migrations.AddField(
            model_name="auditevent",
            name="previous_hash",
            field=models.CharField(blank=True, editable=False, max_length=64),
        ),
        migrations.AddField(
            model_name="auditevent",
            name="event_hash",
            field=models.CharField(blank=True, db_index=True, editable=False, max_length=64),
        ),
        migrations.AlterField(
            model_name="auditevent",
            name="created_at",
            field=models.DateTimeField(db_index=True, default=timezone.now, editable=False),
        ),
        migrations.RunPython(backfill_hash_chain, migrations.RunPython.noop),
    ]
