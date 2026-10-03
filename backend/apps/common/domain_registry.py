from dataclasses import dataclass, field
from typing import Iterable

from django.apps import apps
from django.db.models import Q


@dataclass(frozen=True)
class DomainObjectSpec:
    type_code: str
    app_label: str
    model_name: str
    tenant_lookup: str | None
    scope_lookup: str | None = None
    allow_global_tenant: bool = False
    capabilities: frozenset[str] = field(default_factory=frozenset)
    label_fields: tuple[str, ...] = ("code", "title", "name", "subject")


_REGISTRY: dict[str, DomainObjectSpec] = {}


def register_domain_object(spec: DomainObjectSpec) -> None:
    existing = _REGISTRY.get(spec.type_code)
    if existing and existing != spec:
        raise RuntimeError(f"Domain object type already registered: {spec.type_code}")
    _REGISTRY[spec.type_code] = spec


def register_domain_objects(specs: Iterable[DomainObjectSpec]) -> None:
    for spec in specs:
        register_domain_object(spec)


def get_domain_object_spec(type_code: str) -> DomainObjectSpec | None:
    return _REGISTRY.get(str(type_code or "").strip())


def registered_type_codes(*, capability: str | None = None) -> frozenset[str]:
    if not capability:
        return frozenset(_REGISTRY)
    return frozenset(
        code for code, spec in _REGISTRY.items() if capability in spec.capabilities
    )


def supports_domain_object(type_code: str, *, capability: str | None = None) -> bool:
    spec = get_domain_object_spec(type_code)
    if not spec:
        return False
    return capability is None or capability in spec.capabilities


def _resolve_attr(obj, dotted_path: str | None):
    current = obj
    for part in str(dotted_path or "").split("."):
        if not part:
            continue
        current = getattr(current, part, None)
        if current is None:
            return None
    return current


def resolve_domain_object(
    *,
    tenant,
    type_code: str,
    object_id,
    capability: str | None = None,
    include_deleted: bool = False,
):
    spec = get_domain_object_spec(type_code)
    if not spec:
        return None
    if capability and capability not in spec.capabilities:
        return None

    model = apps.get_model(spec.app_label, spec.model_name)
    queryset = model._default_manager.filter(id=object_id)

    if not include_deleted and any(field.name == "deleted_at" for field in model._meta.fields):
        queryset = queryset.filter(deleted_at__isnull=True)

    if spec.tenant_lookup:
        tenant_filter = {spec.tenant_lookup: tenant}
        if spec.allow_global_tenant:
            queryset = queryset.filter(
                Q(**tenant_filter) | Q(**{f"{spec.tenant_lookup}__isnull": True})
            )
        else:
            queryset = queryset.filter(**tenant_filter)

    return queryset.first()


def domain_object_scope(obj, spec_or_type_code):
    if obj is None:
        return None
    spec = (
        spec_or_type_code
        if isinstance(spec_or_type_code, DomainObjectSpec)
        else get_domain_object_spec(spec_or_type_code)
    )
    if not spec:
        return None
    return _resolve_attr(obj, spec.scope_lookup)


def domain_object_display(obj, type_code: str, object_id=None) -> str:
    spec = get_domain_object_spec(type_code)
    if obj is not None and spec:
        code = str(getattr(obj, "code", "") or "").strip()
        title = ""
        for field_name in spec.label_fields:
            value = str(getattr(obj, field_name, "") or "").strip()
            if value:
                if field_name == "code":
                    code = value
                else:
                    title = value
                    break
        if code and title:
            return f"{code} · {title}"
        if title:
            return title
        if code:
            return code
    suffix = str(object_id or "")[:8]
    return f"{type_code} / {suffix}" if suffix else str(type_code or "")


COMMON_EVIDENCE = frozenset({"evidence_link"})
COMMON_DOCUMENT = frozenset({"document_link"})
COMMON_AI = frozenset({"ai_target"})
COMMON_REFERENCE = COMMON_EVIDENCE | COMMON_DOCUMENT | COMMON_AI


register_domain_objects(
    [
        DomainObjectSpec(
            "risk",
            "risks",
            "Risk",
            "tenant",
            "organization_unit",
            capabilities=COMMON_REFERENCE | frozenset({"workflow"}),
        ),
        DomainObjectSpec(
            "risk_treatment",
            "risks",
            "RiskTreatment",
            "risk__tenant",
            "risk.organization_unit",
            capabilities=frozenset({"action_source"}),
        ),
        DomainObjectSpec(
            "assessment",
            "assessments",
            "Assessment",
            "tenant",
            "organization_unit",
            capabilities=COMMON_REFERENCE | frozenset({"workflow"}),
        ),
        DomainObjectSpec(
            "assessment_item",
            "assessments",
            "AssessmentItem",
            "assessment__tenant",
            "assessment.organization_unit",
            capabilities=COMMON_REFERENCE | frozenset({"action_source"}),
        ),
        DomainObjectSpec(
            "finding",
            "findings",
            "Finding",
            "tenant",
            "organization_unit",
            capabilities=COMMON_REFERENCE | frozenset({"workflow", "action_source"}),
        ),
        DomainObjectSpec(
            "action",
            "actions",
            "Action",
            "tenant",
            "organization_unit",
            capabilities=COMMON_REFERENCE | frozenset({"workflow"}),
        ),
        DomainObjectSpec(
            "document",
            "documents",
            "Document",
            "tenant",
            "organization_unit",
            capabilities=COMMON_REFERENCE | frozenset({"workflow"}),
        ),
        DomainObjectSpec(
            "audit",
            "internal_audits",
            "AuditEngagement",
            "tenant",
            "organization_unit",
            capabilities=frozenset({"workflow"}),
        ),
        DomainObjectSpec(
            "audit_engagement",
            "internal_audits",
            "AuditEngagement",
            "tenant",
            "organization_unit",
            capabilities=COMMON_REFERENCE,
        ),
        DomainObjectSpec(
            "audit_workpaper",
            "internal_audits",
            "Workpaper",
            "engagement__tenant",
            "engagement.organization_unit",
            capabilities=COMMON_REFERENCE,
        ),
        DomainObjectSpec(
            "control_implementation",
            "controls",
            "ControlImplementation",
            "tenant",
            "organization_unit",
            capabilities=COMMON_REFERENCE,
        ),
        DomainObjectSpec(
            "control_test_run",
            "controls",
            "ControlTestRun",
            "control_test__control_implementation__tenant",
            "control_test.control_implementation.organization_unit",
            capabilities=COMMON_REFERENCE,
        ),
        DomainObjectSpec(
            "requirement",
            "frameworks",
            "Requirement",
            "framework_version__framework__tenant",
            None,
            allow_global_tenant=True,
            capabilities=COMMON_REFERENCE,
        ),
        DomainObjectSpec(
            "evidence",
            "evidence",
            "Evidence",
            "tenant",
            "organization_unit",
            capabilities=COMMON_DOCUMENT | COMMON_AI,
        ),
    ]
)
