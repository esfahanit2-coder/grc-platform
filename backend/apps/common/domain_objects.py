from dataclasses import dataclass
from typing import Optional

from django.apps import apps
from django.db.models import Q


@dataclass(frozen=True)
class DomainObjectSpec:
    type_code: str
    app_label: str
    model_name: str
    tenant_lookup: Optional[str]
    scope_lookup: Optional[str] = None
    select_related: tuple[str, ...] = ()
    allow_global: bool = False
    capabilities: frozenset[str] = frozenset()


_SPECS = (
    DomainObjectSpec(
        "risk", "risks", "Risk", "tenant", "organization_unit",
        ("organization_unit",), capabilities=frozenset({"evidence", "workflow"}),
    ),
    DomainObjectSpec(
        "assessment", "assessments", "Assessment", "tenant", "organization_unit",
        ("organization_unit",), capabilities=frozenset({"evidence", "workflow"}),
    ),
    DomainObjectSpec(
        "assessment_item", "assessments", "AssessmentItem", "assessment__tenant",
        "assessment__organization_unit", ("assessment__organization_unit",),
        capabilities=frozenset({"evidence"}),
    ),
    DomainObjectSpec(
        "control_implementation", "controls", "ControlImplementation", "tenant",
        "organization_unit", ("organization_unit",), capabilities=frozenset({"evidence"}),
    ),
    DomainObjectSpec(
        "finding", "findings", "Finding", "tenant", "organization_unit",
        ("organization_unit",), capabilities=frozenset({"evidence", "workflow"}),
    ),
    DomainObjectSpec(
        "action", "actions", "Action", "tenant", "organization_unit",
        ("organization_unit",), capabilities=frozenset({"evidence", "workflow"}),
    ),
    DomainObjectSpec(
        "requirement", "frameworks", "Requirement",
        "framework_version__framework__tenant", None,
        ("framework_version__framework",), allow_global=True,
        capabilities=frozenset({"evidence"}),
    ),
    DomainObjectSpec(
        "audit_workpaper", "internal_audits", "Workpaper", "engagement__tenant",
        "engagement__organization_unit", ("engagement__organization_unit",),
        capabilities=frozenset({"evidence"}),
    ),
    DomainObjectSpec(
        "control_test_run", "controls", "ControlTestRun",
        "control_test__control_implementation__tenant",
        "control_test__control_implementation__organization_unit",
        ("control_test__control_implementation__organization_unit",),
        capabilities=frozenset({"evidence"}),
    ),
    DomainObjectSpec(
        "document", "documents", "Document", "tenant", "organization_unit",
        ("organization_unit",), capabilities=frozenset({"evidence", "workflow"}),
    ),
    # Keep the legacy workflow type code stable. Future APIs may expose the
    # more explicit audit_engagement code without breaking existing records.
    DomainObjectSpec(
        "audit", "internal_audits", "AuditEngagement", "tenant", "organization_unit",
        ("organization_unit",), capabilities=frozenset({"workflow"}),
    ),
)

DOMAIN_OBJECT_REGISTRY = {spec.type_code: spec for spec in _SPECS}


def get_domain_object_spec(type_code):
    return DOMAIN_OBJECT_REGISTRY.get(str(type_code or "").strip())


def supports_domain_object_type(type_code, *, capability=None):
    spec = get_domain_object_spec(type_code)
    if spec is None:
        return False
    return capability is None or capability in spec.capabilities


def _model_has_field(model, name):
    return any(field.name == name for field in model._meta.fields)


def resolve_domain_object(tenant, type_code, object_id):
    """Resolve a registered object while cloaking foreign-tenant records.

    Unsupported type codes return None here; callers that need to distinguish
    unsupported types should call supports_domain_object_type first.
    """
    spec = get_domain_object_spec(type_code)
    if spec is None:
        return None

    model = apps.get_model(spec.app_label, spec.model_name)
    queryset = model.objects.filter(id=object_id)

    if _model_has_field(model, "deleted_at"):
        queryset = queryset.filter(deleted_at__isnull=True)

    if spec.tenant_lookup:
        if spec.allow_global:
            queryset = queryset.filter(
                Q(**{spec.tenant_lookup: tenant})
                | Q(**{f"{spec.tenant_lookup}__isnull": True})
            )
        else:
            queryset = queryset.filter(**{spec.tenant_lookup: tenant})

    if spec.select_related:
        queryset = queryset.select_related(*spec.select_related)

    return queryset.first()


def _resolve_attr_path(obj, path):
    current = obj
    for part in str(path or "").split("__"):
        if not part:
            continue
        current = getattr(current, part, None)
        if current is None:
            return None
    return current


def domain_object_scope(type_code, obj):
    spec = get_domain_object_spec(type_code)
    if spec is None or obj is None or not spec.scope_lookup:
        return None
    return _resolve_attr_path(obj, spec.scope_lookup)


def domain_object_display(type_code, obj, object_id=None):
    if obj is None:
        return f"{type_code} / {str(object_id or '')[:8]}"

    code = str(getattr(obj, "code", "") or "").strip()
    title = str(
        getattr(obj, "title", "")
        or getattr(obj, "name", "")
        or getattr(obj, "subject", "")
        or ""
    ).strip()

    if code and title:
        return f"{code} · {title}"
    if title:
        return title
    if code:
        return code
    return f"{type_code} / {str(object_id or getattr(obj, 'id', ''))[:8]}"
