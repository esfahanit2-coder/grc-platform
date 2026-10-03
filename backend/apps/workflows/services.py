from django.apps import apps
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.audit.services import record_audit_event
from apps.common.domain_registry import (
    domain_object_display,
    domain_object_scope,
    resolve_domain_object,
)
from apps.identity.services import (
    has_tenant_permission,
    has_whole_tenant_permission,
    require_tenant_permission,
    require_whole_tenant_permission,
)
from apps.tenancy.models import TenantMembership

from .models import WorkflowEvent, WorkflowInstance, WorkflowTransition


rom django.apps import apps
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.audit.services import record_audit_event
from apps.common.domain_registry import (
    domain_object_display,
    domain_object_scope,
    resolve_domain_object,
)
from apps.identity.services import (
    has_tenant_permission,
    has_whole_tenant_permission,
    require_tenant_permission,
    require_whole_tenant_permission,
)
from apps.tenancy.models import TenantMembership

from .models import WorkflowEvent, WorkflowInstance, WorkflowTransition


OBJECT_MODEL_MAP = {
    "risk": ("risks", "Risk"),
    "assessment": ("assessments", "Assessment"),
    "finding": ("findings", "Finding"),
    "document": ("documents", "Document"),
    "action": ("actions", "Action"),
    "audit": ("internal_audits", "AuditEngagement"),
}


def _has_scoped_permission(user, tenant, permission_code, unit):
    if unit is None:
        return has_whole_tenant_permission(user, tenant, permission_code)
    return has_tenant_permission(user, tenant, permission_code, unit)


def _require_scoped_permission(user, tenant, permission_code, unit):
    if unit is None:
        return require_whole_tenant_permission(user, tenant, permission_code)
    return require_tenant_permission(user, tenant, permission_code, unit)


def resolve_workflow_object(tenant, object_type, object_id):
    obj = resolve_domain_object(
        tenant=tenant,
        type_code=object_type,
        object_id=object_id,
        capability="workflow",
    )
    if not obj:
        raise ValidationError("Workflow target object was not found.")
    return obj


def workflow_object_label(obj, object_type, object_id):
    return domain_object_display(obj, object_type, object_id)


def workflow_target_display(instance):
    cached = str((instance.metadata or {}).get("target_display", "")).strip()
    if cached:
        return cached
    try:
        obj = resolve_workflow_object(
            instance.tenant, instance.object_type, instance.object_id
        )
    except ValidationError:
        return domain_object_display(None, instance.object_type, instance.object_id)
    return domain_object_display(obj, instance.object_type, instance.object_id)


def object_scope(tenant, object_type, object_id):
    obj = resolve_workflow_object(tenant, object_type, object_id)
    return domain_object_scope(obj, object_type)

