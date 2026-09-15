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
    kwargs = {}
    if request_id:
        kwargs["request_id"] = request_id
    return AuditEvent.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        actor_username=username,
        tenant=tenant,
        action=action,
        category=category or _category_from_action(action),
        outcome=outcome,
        object_type=object_type,
        object_id=object_id,
        object_repr=object_repr,
        metadata=metadata or {},
        old_data=old_data or {},
        new_data=new_data or {},
        ip_address=_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", "") if request else "",
        http_method=request.method if request else "",
        path=request.path[:500] if request else "",
        **kwargs,
    )
