"""Bounded, tenant-scoped, read-only compatibility index of legacy and generic assessments.

The index deliberately returns common *metadata only*. Legacy and generic scores
are not conflated or recalculated, and no historical record is migrated or edited.
"""
from uuid import UUID

from django.db.models import CharField, DecimalField, F, Value
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.assessments.models import Assessment
from apps.generic_assessments.models import GenericAssessmentRun
from apps.identity.services import (
    accessible_organization_unit_ids, has_whole_tenant_permission, require_tenant_permission,
)
from apps.tenancy.services import resolve_tenant_for_request


def _positive(value, name, *, default, maximum):
    if value is None:
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError({name: "A positive integer is required."}) from exc
    if parsed < 1 or parsed > maximum:
        raise ValidationError({name: f"Allowed range: 1 to {maximum}."})
    return parsed


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def assessment_history(request):
    tenant = resolve_tenant_for_request(request)
    code = "assessment.view"
    require_tenant_permission(request.user, tenant, code)

    source = request.query_params.get("source", "all")
    if source not in {"all", "legacy", "generic"}:
        raise ValidationError({"source": "Choose all, legacy or generic."})
    page = _positive(request.query_params.get("page"), "page", default=1, maximum=1000)
    page_size = _positive(request.query_params.get("page_size"), "page_size", default=25, maximum=100)
    offset = (page - 1) * page_size
    needle = request.query_params.get("search", "").strip()
    if len(needle) > 120:
        raise ValidationError({"search": "Search is too long."})
    requested_unit = request.query_params.get("organization_unit")
    if requested_unit:
        try:
            requested_unit = UUID(requested_unit)
        except (ValueError, AttributeError) as exc:
            raise ValidationError({"organization_unit": "A valid UUID is required."}) from exc

    legacy = Assessment.objects.filter(tenant=tenant, deleted_at__isnull=True)
    generic = GenericAssessmentRun.objects.filter(tenant=tenant, deleted_at__isnull=True)
    if not has_whole_tenant_permission(request.user, tenant, code):
        allowed = accessible_organization_unit_ids(request.user, tenant, code)
        legacy = legacy.filter(organization_unit_id__in=allowed)
        generic = generic.filter(organization_unit_id__in=allowed)
    if requested_unit:
        legacy = legacy.filter(organization_unit_id=requested_unit)
        generic = generic.filter(organization_unit_id=requested_unit)
    if needle:
        legacy = legacy.filter(title__icontains=needle)
        generic = generic.filter(title__icontains=needle)

    common = (
        "id", "title", "status", "organization_unit_id", "created_at",
        "source", "reference_version_id", "overall_score", "progress_percent",
    )
    # Union is performed by PostgreSQL, ensuring global chronological paging,
    # unlike Python-side concatenation of capped independent result sets.
    legacy_rows = legacy.order_by().annotate(
        source=Value("legacy", output_field=CharField(max_length=12)),
        reference_version_id=F("framework_version_id"),
    ).values(*common)
    generic_rows = generic.order_by().annotate(
        source=Value("generic", output_field=CharField(max_length=12)),
        reference_version_id=F("template_version_id"),
        overall_score=Value(None, output_field=DecimalField(max_digits=7, decimal_places=3)),
        progress_percent=Value(None, output_field=DecimalField(max_digits=7, decimal_places=3)),
    ).values(*common)

    if source == "legacy":
        selected = legacy_rows
    elif source == "generic":
        selected = generic_rows
    else:
        selected = legacy_rows.union(generic_rows, all=True)
    selected = selected.order_by("-created_at", "-id")
    rows = list(selected[offset: offset + page_size + 1])
    has_more = len(rows) > page_size
    rows = rows[:page_size]
    return Response({
        "page": page,
        "page_size": page_size,
        "has_more": has_more,
        "results": [{
            "source": row["source"],
            "id": str(row["id"]),
            "title": row["title"],
            "status": row["status"],
            "organization_unit": str(row["organization_unit_id"]) if row["organization_unit_id"] else None,
            "reference_version_id": str(row["reference_version_id"]),
            "overall_score": str(row["overall_score"]) if row["overall_score"] is not None else None,
            "progress_percent": str(row["progress_percent"]) if row["progress_percent"] is not None else None,
            "created_at": row["created_at"].isoformat(),
        } for row in rows],
    })
