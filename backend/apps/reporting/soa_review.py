"""Human draft review feedback. A review is never an approved ISO SoA."""
import hashlib
import json

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import record_audit_event
from apps.evidence.models import EvidenceLink
from apps.frameworks.services import calculate_version_checksum
from apps.identity.services import (
    has_tenant_permission, require_tenant_permission, require_whole_tenant_permission,
)
from apps.tenancy.models import TenantMembership

from .models import SoADraftReviewEvent, SoARegister
from .soa_views import _register


def draft_review_digest(register):
    """Canonical local draft fingerprint, not a rights, signature or approval proof."""
    framework = register.framework_version
    decisions = []
    for d in register.control_decisions.filter(deleted_at__isnull=True).order_by("id"):
        decisions.append({
            "id": str(d.pk), "control_id": str(d.control_id),
            "reference_kind": d.reference_kind, "identifier": d.source_identifier,
            "decision": d.decision, "rationale": d.rationale,
            "implementation": str(d.control_implementation_id or ""),
            "treatment": str(d.risk_treatment_id or ""),
            "last_editor": str(d.last_edited_by_id),
        })
    evidence_links = [
        {
            "id": str(link.pk), "object_id": str(link.object_id),
            "evidence_id": str(link.evidence_id),
            "relation": link.relation_type, "evidence_modified": str(link.evidence.updated_at),
            "valid_until": str(link.evidence.valid_until),
        }
        for link in EvidenceLink.objects.filter(
            tenant_id=register.tenant_id,
            object_type="soa_decision",
            object_id__in=[d["id"] for d in decisions],
            deleted_at__isnull=True,
            evidence__deleted_at__isnull=True,
        ).select_related("evidence").order_by("id")
    ]
    payload = {
        "register": str(register.pk), "tenant": str(register.tenant_id),
        "org": str(register.organization_unit_id), "revision": register.revision,
        "version": str(register.framework_version_id),
        "framework_locked": bool(framework.is_locked),
        "framework_stored_checksum": framework.checksum,
        "framework_current_checksum": calculate_version_checksum(framework),
        "decisions": decisions, "evidence_links": evidence_links,
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _validate_reviewer(register, candidate):
    if candidate.id == register.created_by_id:
        raise ValidationError({"reviewer": "Preparer cannot review own draft."})
    if register.control_decisions.filter(
        deleted_at__isnull=True, last_edited_by_id=candidate.pk
    ).exists():
        raise ValidationError({"reviewer": "A decision editor cannot independently review this draft."})
    if not TenantMembership.objects.filter(
        tenant_id=register.tenant_id, user=candidate, is_active=True
    ).exists():
        raise ValidationError({"reviewer": "Reviewer must be an active tenant member."})
    if not (
        has_tenant_permission(candidate, register.tenant, "assessment.review", register.organization_unit)
        and has_tenant_permission(candidate, register.tenant, "report.view", register.organization_unit)
    ):
        raise ValidationError({"reviewer": "Reviewer lacks independent scoped review/view permission."})


def _serialize(event, digest=None):
    return {
        "id": str(event.pk),
        "register": str(event.register_id),
        "round": event.review_round,
        "kind": event.kind,
        "actor_id": str(event.actor_id),
        "assigned_reviewer_id": str(event.assigned_reviewer_id),
        "note": event.note,
        "created_at": event.created_at.isoformat(),
        "snapshot_stale": digest is not None and digest != event.draft_digest,
        "is_formal_statement_of_applicability": False,
        "formal_attestation_allowed": False,
        "notice": "Human draft review feedback only — NOT approval, attestation or signature.",
    }


def _parse_reviewer(value):
    identifier = str(value or "")
    if not identifier.isdecimal() or len(identifier) > 18 or int(identifier) < 1:
        raise ValidationError({"reviewer": "A valid reviewer user ID is required."})
    return int(identifier)


class SoAReviewCandidatesView(APIView):
    def get(self, request, pk):
        _, register = _register(request, pk, for_write=True)
        excluded_editor_ids = set(register.control_decisions.filter(
            deleted_at__isnull=True
        ).values_list("last_edited_by_id", flat=True))
        results = []
        members = list(TenantMembership.objects.filter(
            tenant_id=register.tenant_id, is_active=True, user__is_active=True,
        ).select_related("user").order_by("user__username")[:501])
        for membership in members[:500]:
            candidate = membership.user
            if candidate.pk == register.created_by_id or candidate.pk == request.user.pk:
                continue
            if candidate.pk in excluded_editor_ids:
                continue
            if has_tenant_permission(
                candidate, register.tenant, "assessment.review", register.organization_unit
            ) and has_tenant_permission(
                candidate, register.tenant, "report.view", register.organization_unit
            ):
                results.append({
                    "id": str(candidate.pk),
                    "display": candidate.get_full_name() or candidate.get_username(),
                })
        return Response({
            "results": results,
            "truncated": len(members) > 500,
            "status": "draft_review_only_not_approved",
            "formal_attestation_allowed": False,
        })


class SoAReviewEventsView(APIView):
    def get(self, request, pk):
        _, register = _register(request, pk)
        events = list(register.review_events.filter(deleted_at__isnull=True).order_by(
            "review_round", "created_at", "id"
        )[:300])
        digest = draft_review_digest(register)
        closed_rounds = {e.review_round for e in events if e.is_response}
        results = []
        for event in events:
            row = _serialize(event, digest)
            row["can_respond"] = bool(
                event.kind == SoADraftReviewEvent.Kind.REQUESTED
                and event.review_round not in closed_rounds
                and event.assigned_reviewer_id == request.user.pk
                and event.actor_id != request.user.pk
                and register.created_by_id != request.user.pk
                and digest == event.draft_digest
                and not register.control_decisions.filter(
                    deleted_at__isnull=True, last_edited_by=request.user
                ).exists()
                and has_tenant_permission(
                    request.user, register.tenant, "assessment.review", register.organization_unit
                )
            )
            results.append(row)
        return Response({
            "results": results,
            "truncated": len(events) == 300,
            "status": "draft_review_only_not_approved",
            "formal_attestation_allowed": False,
        })

    @transaction.atomic
    def post(self, request, pk):
        tenant, register = _register(request, pk, for_write=True)
        require_whole_tenant_permission(request.user, tenant, "report.generate")
        if set(request.data) - {"reviewer", "note"}:
            raise ValidationError({"fields": "Only reviewer and note are supported."})
        note = request.data.get("note", "")
        if not isinstance(note, str) or len(note) > 2000:
            raise ValidationError({"note": "Review request note must be text up to 2000 characters."})
        reviewer_id = _parse_reviewer(request.data.get("reviewer"))
        reviewer = get_user_model().objects.filter(pk=reviewer_id, is_active=True).first()
        if not reviewer:
            raise ValidationError({"reviewer": "Active reviewer not found."})

        register = SoARegister.objects.select_for_update().select_related(
            "framework_version", "framework_version__framework", "organization_unit", "tenant"
        ).get(pk=register.pk, tenant=tenant, deleted_at__isnull=True)
        _validate_reviewer(register, reviewer)
        if reviewer.pk == request.user.pk:
            raise ValidationError({"reviewer": "Requester must be different from reviewer."})
        digest = draft_review_digest(register)
        last = register.review_events.filter(
            deleted_at__isnull=True, is_response=False
        ).order_by("-review_round").first()
        round_number = 1 if last is None else last.review_round + 1
        if last is not None:
            responded = register.review_events.filter(
                review_round=last.review_round, is_response=True, deleted_at__isnull=True
            ).exists()
            if not responded:
                if last.draft_digest == digest:
                    return Response({
                        "detail": "There is already a pending review of this exact draft.",
                        "formal_attestation_allowed": False,
                    }, status=status.HTTP_409_CONFLICT)
                stale = SoADraftReviewEvent.objects.create(
                    register=register, review_round=last.review_round,
                    kind=SoADraftReviewEvent.Kind.SUPERSEDED,
                    is_response=True, actor=request.user, assigned_reviewer=last.assigned_reviewer,
                    draft_digest=last.draft_digest,
                    note="Source draft changed; previous request superseded without review.",
                )
                record_audit_event(
                    request.user, tenant, "soa.review.supersede", "soa_review_event",
                    stale.pk, metadata={"register": str(register.pk), "round": last.review_round},
                    request=request,
                )
        created = SoADraftReviewEvent.objects.create(
            register=register, review_round=round_number,
            kind=SoADraftReviewEvent.Kind.REQUESTED,
            is_response=False, actor=request.user, assigned_reviewer=reviewer,
            note=note.strip(), draft_digest=digest,
        )
        record_audit_event(
            request.user, tenant, "soa.review.request", "soa_review_event",
            created.pk, metadata={"register": str(register.pk), "round": round_number},
            request=request,
        )
        return Response(_serialize(created, digest), status=status.HTTP_201_CREATED)


class SoAReviewRespondView(APIView):
    @transaction.atomic
    def post(self, request, pk, event_id):
        tenant, register = _register(request, pk)
        if set(request.data) - {"kind", "note"}:
            raise ValidationError({"fields": "Only kind and note are supported."})
        kind = request.data.get("kind")
        if kind not in {
            SoADraftReviewEvent.Kind.FEEDBACK_RECORDED,
            SoADraftReviewEvent.Kind.CHANGES_REQUESTED,
        }:
            raise ValidationError({"kind": "Draft review can record feedback or request changes, NEVER approve."})
        note = request.data.get("note")
        if not isinstance(note, str) or not note.strip() or len(note) > 4000:
            raise ValidationError({"note": "Written human feedback is mandatory (max 4000 characters)."})
        register = SoARegister.objects.select_for_update().select_related(
            "framework_version", "framework_version__framework", "organization_unit", "tenant"
        ).get(pk=register.pk, tenant=tenant, deleted_at__isnull=True)
        source = register.review_events.filter(
            pk=event_id, is_response=False,
            kind=SoADraftReviewEvent.Kind.REQUESTED, deleted_at__isnull=True
        ).first()
        if source is None:
            from django.http import Http404
            raise Http404
        require_tenant_permission(request.user, tenant, "assessment.review", register.organization_unit)
        require_tenant_permission(request.user, tenant, "report.view", register.organization_unit)
        if request.user.pk != source.assigned_reviewer_id:
            raise ValidationError({"reviewer": "Only the selected independent reviewer can respond."})
        if (
            request.user.pk in {register.created_by_id, source.actor_id}
            or register.control_decisions.filter(
                deleted_at__isnull=True, last_edited_by=request.user
            ).exists()
        ):
            raise ValidationError({"reviewer": "The preparer or a control decision editor cannot review own draft."})
        _validate_reviewer(register, request.user)
        if register.review_events.filter(
            review_round=source.review_round, is_response=True, deleted_at__isnull=True
        ).exists():
            return Response({"detail": "Review round is already closed."}, status=status.HTTP_409_CONFLICT)
        digest = draft_review_digest(register)
        if source.draft_digest != digest:
            return Response({
                "detail": "Draft changed since review request; request a new independent review.",
                "formal_attestation_allowed": False,
            }, status=status.HTTP_409_CONFLICT)
        response = SoADraftReviewEvent.objects.create(
            register=register, review_round=source.review_round,
            kind=kind, is_response=True,
            actor=request.user, assigned_reviewer=request.user,
            note=note.strip(), draft_digest=source.draft_digest,
        )
        record_audit_event(
            request.user, tenant, "soa.review.feedback", "soa_review_event",
            response.pk, metadata={
                "register": str(register.pk), "round": source.review_round,
                "kind": kind,
            }, request=request,
        )
        return Response(_serialize(response, digest), status=status.HTTP_201_CREATED)
