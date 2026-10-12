"""Draft-only SoA control decision API. This is not an attestation or approval workflow."""
from uuid import UUID

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import record_audit_event
from apps.controls.models import Control, ControlImplementation
from apps.frameworks.models import FrameworkVersion
from apps.identity.services import (
    accessible_organization_unit_ids, has_whole_tenant_permission,
    require_tenant_permission, require_whole_tenant_permission,
)
from apps.organizations.models import OrganizationUnit
from apps.risks.models import RiskTreatment
from apps.tenancy.services import resolve_tenant_for_request

from .models import SoAControlDecision, SoARegister


def _uuid(value, field):
    try:
        return UUID(str(value))
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValidationError({field: "Valid UUID is required."}) from exc


def _model_save(row):
    try:
        row.save()
    except DjangoValidationError as exc:
        raise ValidationError(exc.message_dict if hasattr(exc, "message_dict") else {"detail": exc.messages}) from exc


def _visible_registers(request, tenant):
    require_tenant_permission(request.user, tenant, "report.view")
    qs = SoARegister.objects.filter(tenant=tenant, deleted_at__isnull=True)
    if not has_whole_tenant_permission(request.user, tenant, "report.view"):
        qs = qs.filter(organization_unit_id__in=accessible_organization_unit_ids(
            request.user, tenant, "report.view"
        ))
    return qs.select_related("framework_version__framework", "organization_unit")


def _register(request, pk, for_write=False):
    tenant = resolve_tenant_for_request(request)
    if for_write:
        require_whole_tenant_permission(request.user, tenant, "report.generate")
    row = _visible_registers(request, tenant).filter(pk=pk).first()
    if row is None:
        raise Http404
    return tenant, row


def _register_data(row):
    data = {
        "id": str(row.pk), "tenant": str(row.tenant_id),
        "organization_unit": str(row.organization_unit_id),
        "framework_version": str(row.framework_version_id),
        "title": row.title, "revision": row.revision,
        "status": row.status, "is_formal_statement_of_applicability": False,
        "approval_status": "not_available",
        "notice": "DRAFT / NOT APPROVED — control decisions only; no formal ISO SoA has been issued.",
    }
    return data


def _decision_data(row):
    return {
        "id": str(row.pk), "register": str(row.register_id),
        "control": str(row.control_id), "control_code": row.control.code,
        "reference_kind": row.reference_kind,
        "source_identifier": row.source_identifier,
        "decision": row.decision, "rationale": row.rationale,
        "control_implementation": str(row.control_implementation_id) if row.control_implementation_id else None,
        "risk_treatment": str(row.risk_treatment_id) if row.risk_treatment_id else None,
        "last_edited_by": str(row.last_edited_by_id),
        "approval_status": "draft_unapproved",
    }


# Defensively sort using actual model columns; published ordering does not
# imply ISO conformance or any published source's wording.
def _register_data_with_decisions(row):
    data = _register_data(row)
    data["decisions"] = [
        _decision_data(x) for x in row.control_decisions.filter(
            deleted_at__isnull=True
        ).select_related("control").order_by("reference_kind", "source_identifier")
    ]
    return data


class SoARegisterListCreateView(APIView):
    def get(self, request):
        tenant = resolve_tenant_for_request(request)
        qs = _visible_registers(request, tenant).order_by("-created_at")
        return Response({"results": [_register_data(x) for x in qs[:200]], "is_formal_statement_of_applicability": False})

    @transaction.atomic
    def post(self, request):
        tenant = resolve_tenant_for_request(request)
        require_whole_tenant_permission(request.user, tenant, "report.generate")
        allowed = {"title", "organization_unit", "framework_version", "revision"}
        if set(request.data) - allowed:
            raise ValidationError({"fields": "Unsupported register fields; approval/status cannot be client-assigned."})
        unit = OrganizationUnit.objects.filter(
            id=_uuid(request.data.get("organization_unit"), "organization_unit"),
            tenant=tenant, deleted_at__isnull=True
        ).first()
        if not unit:
            raise ValidationError({"organization_unit": "Unit not found in tenant."})
        version = FrameworkVersion.objects.filter(
            pk=_uuid(request.data.get("framework_version"), "framework_version"),
            framework__tenant=tenant, deleted_at__isnull=True
        ).first()
        if not version or not version.is_locked:
            raise ValidationError({"framework_version": "Tenant framework version must exist and be locked."})
        title = request.data.get("title")
        if not isinstance(title, str) or not title.strip():
            raise ValidationError({"title": "Title is required."})
        revision = request.data.get("revision", 1)
        if type(revision) is not int or revision < 1:
            raise ValidationError({"revision": "Positive integer is required."})
        register = SoARegister(
            tenant=tenant, organization_unit=unit, framework_version=version,
            title=title.strip(), revision=revision, created_by=request.user,
        )
        _model_save(register)
        record_audit_event(request.user, tenant, "soa.draft.create", "soa_register", register.pk,
                           new_data={"revision": revision, "scope": str(unit.pk)}, request=request)
        return Response(_register_data(register), status=status.HTTP_201_CREATED)


class SoARegisterDetailView(APIView):
    def get(self, request, pk):
        _, register = _register(request, pk)
        return Response(_register_data_with_decisions(register))


def _referenced_model(request_data, key, model, filters):
    value = request_data.get(key)
    if value is None or value == "":
        return None
    obj = model.objects.filter(pk=_uuid(value, key), **filters).first()
    if obj is None:
        raise ValidationError({key: "Reference is not available in this tenant and scope."})
    return obj


def _apply_decision_changes(row, data, tenant, actor, create=False):
    allowed = {"decision", "rationale", "control_implementation", "risk_treatment"}
    if create:
        allowed |= {"control", "reference_kind", "source_identifier"}
    if set(data) - allowed:
        raise ValidationError({"fields": "Unsupported/immutable decision fields."})
    if create:
        control = _referenced_model(data, "control", Control, {"deleted_at__isnull": True})
        if control is None or control.tenant_id not in {None, tenant.id}:
            raise ValidationError({"control": "Control not available to tenant."})
        row.control = control
        kind = data.get("reference_kind")
        if kind not in SoAControlDecision.ReferenceKind.values:
            raise ValidationError({"reference_kind": "Invalid reference type."})
        row.reference_kind = kind
        identifier = data.get("source_identifier")
        if not isinstance(identifier, str) or not identifier.strip() or len(identifier) > 120:
            raise ValidationError({"source_identifier": "An existing, checked identifier is required."})
        row.source_identifier = identifier.strip()
    if "decision" in data:
        if data["decision"] not in SoAControlDecision.Decision.values:
            raise ValidationError({"decision": "Unknown inclusion/exclusion decision."})
        row.decision = data["decision"]
    if "rationale" in data:
        if not isinstance(data["rationale"], str):
            raise ValidationError({"rationale": "Text is required."})
        row.rationale = data["rationale"]
    if "control_implementation" in data:
        row.control_implementation = _referenced_model(
            data, "control_implementation", ControlImplementation,
            {"tenant": tenant, "organization_unit": row.register.organization_unit,
             "control": row.control, "deleted_at__isnull": True},
        )
    if "risk_treatment" in data:
        row.risk_treatment = _referenced_model(
            data, "risk_treatment", RiskTreatment,
            {"risk__tenant": tenant, "risk__organization_unit": row.register.organization_unit,
             "risk__deleted_at__isnull": True, "deleted_at__isnull": True},
        )
    row.last_edited_by = actor
    _model_save(row)
    return row


class SoADecisionCreateView(APIView):
    @transaction.atomic
    def post(self, request, pk):
        tenant, register = _register(request, pk, for_write=True)
        row = SoAControlDecision(register=register, last_edited_by=request.user)
        _apply_decision_changes(row, request.data, tenant, request.user, create=True)
        record_audit_event(request.user, tenant, "soa.draft.decision.create", "soa_decision",
                           row.pk, new_data={"register": str(register.pk), "decision": row.decision},
                           request=request)
        return Response(_decision_data(row), status=status.HTTP_201_CREATED)


class SoADecisionDetailView(APIView):
    @transaction.atomic
    def patch(self, request, pk, decision_id):
        tenant, register = _register(request, pk, for_write=True)
        row = register.control_decisions.filter(pk=decision_id, deleted_at__isnull=True).select_related(
            "control", "control_implementation", "risk_treatment__risk"
        ).first()
        if row is None:
            raise Http404
        _apply_decision_changes(row, request.data, tenant, request.user)
        record_audit_event(request.user, tenant, "soa.draft.decision.update", "soa_decision",
                           row.pk, new_data={"register": str(register.pk), "decision": row.decision},
                           request=request)
        return Response(_decision_data(row))
