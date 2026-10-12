"""Read-only comparison with numeric-only Annex A identifiers; no ISO content import.

This intentionally does not validate framework edition ownership, licensed use,
necessity of any individual control, controls outside Annex A, or approved SoA.
"""
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SoAControlDecision
from .soa_views import _register


REFERENCE = "iso-iec-27001-2022-annex-a-structure-only"
# Identifiers only; verified against the structure-only reference index in
# content-packs/references/iso-iec-27001-2022-structure-only.json.
NUMERIC_GROUP_SIZES = {5: 37, 6: 8, 7: 14, 8: 34}
EXPECTED_IDS = tuple(
    f"A.{group}.{number}"
    for group, size in NUMERIC_GROUP_SIZES.items()
    for number in range(1, size + 1)
)


def build_numeric_reference_diff(register):
    # This source-free comparison is intentionally available for any scoped
    # *draft*, but must never be interpreted as the tenant's licensed,
    # organization-specific ISO 27001 SoA assessment.
    rows = list(
        register.control_decisions.filter(
            deleted_at__isnull=True,
            reference_kind=SoAControlDecision.ReferenceKind.ANNEX_A,
        ).values("source_identifier", "decision")
    )
    expected = set(EXPECTED_IDS)
    seen = {row["source_identifier"] for row in rows}
    matched = sorted(seen & expected, key=lambda value: EXPECTED_IDS.index(value))
    missing = [ref for ref in EXPECTED_IDS if ref not in seen]
    unknown = sorted(seen - expected)
    undecided = sorted(
        {row["source_identifier"] for row in rows
         if row["source_identifier"] in expected
         and row["decision"] == SoAControlDecision.Decision.UNDECIDED},
        key=lambda value: EXPECTED_IDS.index(value),
    )
    additional_count = register.control_decisions.filter(
        deleted_at__isnull=True,
        reference_kind=SoAControlDecision.ReferenceKind.ADDITIONAL,
    ).count()
    return {
        "register_id": str(register.pk),
        "comparison_type": "numeric_structure_only_non_attesting",
        "reference": REFERENCE,
        "source_rights_review": "not_verified",
        "framework_source_identity": "not_verified",
        "control_title_and_content_review": "not_performed",
        "human_control_selection_review": "not_performed",
        "is_formal_statement_of_applicability": False,
        "formal_attestation_allowed": False,
        "comparison_summary": {
            "reference_numeric_ids": len(EXPECTED_IDS),
            "matched_numeric_identifiers": len(matched),
            "missing_numeric_identifiers": len(missing),
            "unrecognized_annex_a_identifiers": len(unknown),
            "undecided_numeric_identifiers": len(undecided),
            "additional_organizational_control_decisions": additional_count,
        },
        "missing_numeric_ids": missing,
        "unrecognized_annex_a_ids": unknown,
        "undecided_numeric_ids": undecided,
        "notice": (
            "Numeric identifier comparison ONLY; 93 IDs are NOT 93 mandatory "
            "organization-specific control selections. Source licensing, content "
            "rights, non-Annex-A necessary controls, evidence, treatment and "
            "independent approval are NOT VERIFIED."
        ),
    }


class SoANumericReferenceDiffView(APIView):
    def get(self, request, pk):
        reference = request.query_params.get("reference")
        if reference != REFERENCE:
            raise ValidationError({
                "reference": (
                    "Explicit reference=iso-iec-27001-2022-annex-a-structure-only "
                    "is required; source identity is not inferred from arbitrary frameworks."
                )
            })
        _, register = _register(request, pk)
        return Response(build_numeric_reference_diff(register))
