"""Read-only diagnostic for draft SoA; intentionally not an approval gate.

The diagnostic checks internal links and incomplete work only. It never
certifies coverage of copyrighted ISO controls or the sufficiency of evidence.
"""
from collections import Counter

from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.evidence.models import EvidenceLink
from apps.risks.models import RiskControl, RiskTreatment

from .models import SoAControlDecision
from .soa_views import _register


def build_draft_readiness(register):
    decisions = list(
        register.control_decisions.filter(deleted_at__isnull=True)
        .select_related("control", "control_implementation",
                        "risk_treatment__risk")
        .order_by("reference_kind", "source_identifier", "id")
    )
    decision_ids = [item.pk for item in decisions]
    now = timezone.now()
    valid_evidence = (
        EvidenceLink.objects.filter(
            tenant_id=register.tenant_id,
            object_type="soa_decision",
            object_id__in=decision_ids,
            deleted_at__isnull=True,
            evidence__tenant_id=register.tenant_id,
            evidence__organization_unit_id=register.organization_unit_id,
            evidence__deleted_at__isnull=True,
        )
        .filter(
            # Expiry is a freshness screen, not a claim of evidentiary adequacy.
            # Undated evidence remains unverified and needs human review.
            # "valid_until" is a date or datetime depending on model config.
            # The Evidence model currently defines a DateTimeField.
            # Conditions are expressed explicitly rather than interpreted as approval.
            _evidence_expiry_q(now)
        )
        .values_list("object_id", flat=True)
    )
    linked_count = Counter(valid_evidence)
    risk_links = {
        (risk_id, impl_id)
        for risk_id, impl_id in RiskControl.objects.filter(
            risk_id__in=[d.risk_treatment.risk_id for d in decisions if d.risk_treatment_id],
            control_implementation_id__in=[d.control_implementation_id for d in decisions if d.control_implementation_id],
            deleted_at__isnull=True,
        ).values_list("risk_id", "control_implementation_id")
    }

    findings = []
    totals = Counter({"included": 0, "excluded": 0, "undecided": 0})
    for decision in decisions:
        totals[decision.decision] += 1
        problems = []
        if decision.decision == SoAControlDecision.Decision.UNDECIDED:
            problems.append("decision_undecided")
        if decision.decision != SoAControlDecision.Decision.UNDECIDED and not decision.rationale.strip():
            problems.append("decision_rationale_missing")
        if (decision.control.deleted_at is not None or
            decision.control.tenant_id not in (None, register.tenant_id)):
            problems.append("control_reference_invalid")
        impl = decision.control_implementation
        if decision.decision == SoAControlDecision.Decision.INCLUDED:
            if impl is None:
                problems.append("implementation_not_linked")
            else:
                if (impl.deleted_at is not None or
                    impl.tenant_id != register.tenant_id or
                    impl.organization_unit_id != register.organization_unit_id or
                    impl.control_id != decision.control_id):
                    problems.append("implementation_scope_invalid")
                if impl.implementation_status != "implemented":
                    problems.append("implementation_not_completed")
                if impl.effectiveness == "not_assessed":
                    problems.append("implementation_effectiveness_not_assessed")
            if linked_count[decision.pk] == 0:
                problems.append("no_current_scoped_evidence_link")
        if decision.decision == SoAControlDecision.Decision.EXCLUDED:
            if impl is not None or decision.risk_treatment_id:
                problems.append("excluded_control_has_conflicting_links")

        treatment = decision.risk_treatment
        if treatment:
            if (
                treatment.deleted_at is not None or treatment.risk.deleted_at is not None or
                treatment.risk.tenant_id != register.tenant_id or
                treatment.risk.organization_unit_id != register.organization_unit_id
            ):
                problems.append("risk_treatment_scope_invalid")
            if not impl or (treatment.risk_id, decision.control_implementation_id) not in risk_links:
                problems.append("missing_risk_control_link")
            if treatment.approval_status != RiskTreatment.ApprovalStatus.APPROVED:
                problems.append("risk_treatment_not_approved")

        if problems:
            findings.append({
                "decision_id": str(decision.pk),
                "reference_kind": decision.reference_kind,
                "source_identifier": decision.source_identifier,
                "codes": problems,
            })

    return {
        "register_id": str(register.pk),
        "status": "draft_review_only",
        "is_formal_statement_of_applicability": False,
        "formal_attestation_allowed": False,
        "source_version_locked": bool(register.framework_version.is_locked),
        "source_rights_review": "not_verified_by_this_endpoint",
        "source_control_inventory_coverage": "not_verified",
        "approval_workflow": "not_available",
        "evidence_sufficiency": "requires_human_review",
        "counts": {
            "decisions": len(decisions),
            "included": totals["included"],
            "excluded": totals["excluded"],
            "undecided": totals["undecided"],
            "decisions_with_findings": len(findings),
        },
        "findings": findings,
        "register_findings": (
            (["empty_control_decision_register"] if not decisions else []) + [
                "source_control_inventory_not_verified",
                "rights_and_content_review_not_verified",
                "human_approval_snapshot_not_available",
            ]
        ),
        "blocking_external_prerequisites": [
            "Verify approved and licensed source inventory (including any organization-specific necessary controls)",
            "Review inclusion/exclusion rationale and current implementation evidence",
            "Reconcile risk treatment decisions, independent approver and immutable approved version",
            "Complete customer UAT and formal approval workflow before issuing any SoA",
        ],
    }


def _evidence_expiry_q(now):
    from django.db.models import Q
    return Q(evidence__valid_until__isnull=True) | Q(evidence__valid_until__gte=now)


class SoADraftReadinessView(APIView):
    def get(self, request, pk):
        _, register = _register(request, pk)
        return Response(build_draft_readiness(register))
