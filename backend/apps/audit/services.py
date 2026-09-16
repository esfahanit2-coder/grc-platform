import hashlib
import json
import uuid

from django.core.serializers.json import DjangoJSONEncoder
from django.db import connection, transaction
from django.utils import timezone

from .models import AuditEvent


def _client_ip(request):
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _category_from_action(action):
    return action.split(".", 1)[0] if "." in action else "application"


def _lock_audit_stream(tenant_id):
    if connection.vendor != "postgresql":
        return
    stream_key = f"grc:audit:{tenant_id or 'global'}"
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", [stream_key])


def _canonical_payload(values):
    return {
        "id": str(values["id"]),
        "tenant_id": str(values["tenant_id"]) if values.get("tenant_id") else None,
        "actor_username": values.get("actor_username", ""),
        "action": values.get("action", ""),
        "category": values.get("category", ""),
        "outcome": values.get("outcome", ""),
        "object_type": values.get("object_type", ""),
        "object_id": str(values["object_id"]) if values.get("object_id") else None,
        "object_repr": values.get("object_repr", ""),
        "metadata": values.get("metadata") or {},
        "old_data": values.get("old_data") or {},
        "new_data": values.get("new_data") or {},
        "ip_address": str(values["ip_address"]) if values.get("ip_address") else None,
        "user_agent": values.get("user_agent", ""),
        "http_method": values.get("http_method", ""),
        "path": values.get("path", ""),
        "request_id": str(values["request_id"]),
        "created_at": values["created_at"].isoformat(),
        "previous_hash": values.get("previous_hash", ""),
    }


def compute_audit_event_hash(values):
    encoded = json.dumps(
        _canonical_payload(values),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        cls=DjangoJSONEncoder,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _values_from_event(event):
    return {
        "id": event.id,
        "tenant_id": event.tenant_id,
        "actor_username": event.actor_username,
        "action": event.action,
        "category": event.category,
        "outcome": event.outcome,
        "object_type": event.object_type,
        "object_id": event.object_id,
        "object_repr": event.object_repr,
        "metadata": event.metadata,
        "old_data": event.old_data,
        "new_data": event.new_data,
        "ip_address": event.ip_address,
        "user_agent": event.user_agent,
        "http_method": event.http_method,
        "path": event.path,
        "request_id": event.request_id,
        "created_at": event.created_at,
        "previous_hash": event.previous_hash,
    }


def verify_audit_chain(tenant=None):
    tenant_id = getattr(tenant, "id", tenant)
    qs = AuditEvent.objects.filter(tenant_id=tenant_id).order_by("created_at", "id")
    previous_hash = ""
    checked = 0
    for event in qs.iterator():
        if event.previous_hash != previous_hash:
            return {
                "valid": False,
                "checked": checked,
                "event_id": str(event.id),
                "reason": "previous_hash_mismatch",
            }
        expected = compute_audit_event_hash(_values_from_event(event))
        if event.event_hash != expected:
            return {
                "valid": False,
                "checked": checked,
                "event_id": str(event.id),
                "reason": "event_hash_mismatch",
            }
        previous_hash = event.event_hash
        checked += 1
    return {"valid": True, "checked": checked, "last_hash": previous_hash}


def record_audit_event(
    actor,
    tenant,
    action,
    object_type,
    object_id=None,
    metadata=None,
    request=None,
    *,
    old_data=None,
    new_data=None,
    object_repr="",
    outcome="success",
    category=None,
):
    username = ""
    if actor is not None:
        username = getattr(actor, "get_username", lambda: "")() or ""
    request_id = getattr(request, "correlation_id", None) if request else None
    event_id = uuid.uuid4()
    request_id = request_id or uuid.uuid4()
    created_at = timezone.now()
    tenant_id = getattr(tenant, "id", tenant)
    values = {
        "id": event_id,
        "tenant_id": tenant_id,
        "actor_username": username,
        "action": action,
        "category": category or _category_from_action(action),
        "outcome": outcome,
        "object_type": object_type,
        "object_id": object_id,
        "object_repr": object_repr,
        "metadata": metadata or {},
        "old_data": old_data or {},
        "new_data": new_data or {},
        "ip_address": _client_ip(request),
        "user_agent": request.META.get("HTTP_USER_AGENT", "") if request else "",
        "http_method": request.method if request else "",
        "path": request.path[:500] if request else "",
        "request_id": request_id,
        "created_at": created_at,
    }
    with transaction.atomic():
        _lock_audit_stream(tenant_id)
        previous_hash = (
            AuditEvent.objects.filter(tenant_id=tenant_id)
            .order_by("-created_at", "-id")
            .values_list("event_hash", flat=True)
            .first()
            or ""
        )
        values["previous_hash"] = previous_hash
        values["event_hash"] = compute_audit_event_hash(values)
        return AuditEvent.objects.create(
            actor=actor if getattr(actor, "is_authenticated", False) else None,
            **values,
        )
