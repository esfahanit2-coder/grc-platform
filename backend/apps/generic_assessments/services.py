"""Small deterministic execution engine. No eval, dynamic Python or per-standard forks."""
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import (
    AssessmentTemplateVersion, GenericAssessmentItem,
    GenericAssessmentRun, TemplateCriterion,
)


@transaction.atomic
def publish_template(*, version, user):
    locked = AssessmentTemplateVersion.objects.select_for_update().select_related("template").get(pk=version.pk)
    if locked.status != AssessmentTemplateVersion.Status.DRAFT:
        raise ValidationError("Only a draft template may be published.")
    if locked.template.owner_id == user.id:
        raise ValidationError("The template owner cannot publish their own version.")
    if not locked.criteria.filter(deleted_at__isnull=True).exists():
        raise ValidationError("At least one valid criterion must exist.")
    locked.status = AssessmentTemplateVersion.Status.PUBLISHED
    locked.published_by = user
    locked.published_at = timezone.now()
    locked.save(update_fields=["status", "published_by", "published_at", "updated_at"])
    return locked


@transaction.atomic
def create_run(*, tenant, template_version, owner, title, organization_unit=None, profile=None):
    if template_version.status != AssessmentTemplateVersion.Status.PUBLISHED:
        raise ValidationError("Only published template versions can be executed.")
    run = GenericAssessmentRun.objects.create(
        tenant=tenant, template_version=template_version, owner=owner, title=title,
        organization_unit=organization_unit, profile=profile,
    )
    definitions = list(template_version.criteria.filter(deleted_at__isnull=True).order_by("sort_order", "code"))
    if not definitions:
        raise ValidationError("Published template has no criteria.")
    # Stable snapshots remain valid if the source framework or template later changes.
    for criterion in definitions:
        GenericAssessmentItem.objects.create(
            run=run, criterion=criterion,
            criterion_code_snapshot=criterion.code,
            criterion_title_snapshot=criterion.title,
            response_type_snapshot=criterion.response_type,
            options_snapshot=list(criterion.choices or []),
            weight_snapshot=criterion.weight,
            required_snapshot=criterion.required,
            applicability_mode_snapshot=criterion.applicability_mode,
        )
    return run


def typed_answer(item, value):
    """Return safe JSON plus an optional score on an explicit 0..100 scale.

    Text and categorical answers intentionally have no numeric score until
    a separately approved rubric is introduced; they are never assumed zero.
    """
    kind = item.response_type_snapshot
    if kind == TemplateCriterion.ResponseType.BOOLEAN:
        if not isinstance(value, bool):
            raise ValidationError({"answer": "A true/false value is required."})
        return {"value": value}, Decimal("100") if value else Decimal("0")
    if kind == TemplateCriterion.ResponseType.NUMBER:
        if isinstance(value, bool) or not isinstance(value, (int, float, str)):
            raise ValidationError({"answer": "A numeric value between 0 and 100 is required."})
        try:
            number = Decimal(str(value))
        except InvalidOperation as exc:
            raise ValidationError({"answer": "Invalid decimal value."}) from exc
        if not number.is_finite() or number < 0 or number > 100:
            raise ValidationError({"answer": "Numeric responses must be between 0 and 100."})
        return {"value": str(number)}, number
    if kind == TemplateCriterion.ResponseType.CHOICE:
        if not isinstance(value, str) or value not in item.options_snapshot:
            raise ValidationError({"answer": "Value must be an approved choice."})
        return {"value": value}, None
    if kind == TemplateCriterion.ResponseType.TEXT:
        if not isinstance(value, str) or len(value) > 10000:
            raise ValidationError({"answer": "A text value (max 10,000 characters) is required."})
        return {"value": value}, None
    raise ValidationError({"answer": "Unknown criterion response type."})


@transaction.atomic
def save_response(*, item, user, value):
    run = GenericAssessmentRun.objects.select_for_update().get(pk=item.run_id)
    if run.status in {run.Status.COMPLETED, run.Status.CANCELLED}:
        raise ValidationError("This assessment is no longer editable.")
    item = GenericAssessmentItem.objects.select_for_update().get(pk=item.pk)
    normalized, score = typed_answer(item, value)
    item.answer = normalized
    item.score_percent = score
    item.assessed_by = user
    item.assessed_at = timezone.now()
    item.save(update_fields=["answer", "score_percent", "assessed_by", "assessed_at", "updated_at"])
    if run.status == run.Status.DRAFT:
        run.status = run.Status.IN_PROGRESS
        run.save(update_fields=["status", "updated_at"])
    return item


def score_summary(run):
    """Weights apply only to explicitly scored answers; report coverage separately."""
    items = list(run.items.filter(deleted_at__isnull=True))
    answered = [i for i in items if i.answer is not None]
    scored = [i for i in applicable if i.score_percent is not None]
    weighted = sum((i.score_percent * i.weight_snapshot for i in scored), Decimal("0"))
    total_weight = sum((i.weight_snapshot for i in scored), Decimal("0"))
    from .models import ApplicabilityDecision
    decisions = {}
    for decision in ApplicabilityDecision.objects.filter(
        generic_item__run=run, reviewed_at__isnull=False, deleted_at__isnull=True,
    ).order_by("-reviewed_at", "-created_at"):
        decisions.setdefault(decision.generic_item_id, decision.decision)
    applicable = [i for i in items if decisions.get(i.id) != ApplicabilityDecision.Decision.NOT_APPLICABLE]
    review_missing = sum(
        i.applicability_mode_snapshot == "review" and i.id not in decisions
        for i in items
    )
    return {
        "applicability_reviews_missing": review_missing,
        "items_count": len(items),
        "answered_count": len(answered),
        "required_unanswered": sum(i.required_snapshot and i.answer is None for i in applicable),
        "scored_count": len(scored),
        "score_percent": str((weighted / total_weight).quantize(Decimal("0.001"))) if total_weight else None,
        "is_partial_score": len(scored) < len(applicable),
    }


@transaction.atomic
def complete_run(*, run):
    run = GenericAssessmentRun.objects.select_for_update().get(pk=run.pk)
    if run.status in {run.Status.COMPLETED, run.Status.CANCELLED}:
        raise ValidationError("Assessment is not completable.")
    summary = score_summary(run)
    if summary["applicability_reviews_missing"]:
        raise ValidationError("Manual applicability decisions require independent review.")
    if run.items.filter(
        applicability_decisions__id__isnull=False,
        applicability_decisions__reviewed_at__isnull=True,
        applicability_decisions__deleted_at__isnull=True,
    ).exists():
        raise ValidationError("Pending applicability decisions must be reviewed before completion.")
    if summary["required_unanswered"]:
        raise ValidationError("Required criteria must be answered before completion.")
    run.status = run.Status.COMPLETED
    run.completed_at = timezone.now()
    run.save(update_fields=["status", "completed_at", "updated_at"])
    return run, summary
