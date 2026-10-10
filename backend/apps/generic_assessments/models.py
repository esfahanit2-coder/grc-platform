"""Versioned, framework-agnostic assessment definitions; legacy Assessment is unchanged."""
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.assessments.models import AssessmentItem
from apps.common.models import UUIDTimeStampedModel
from apps.frameworks.models import FrameworkVersion, Requirement
from apps.organizations.models import OrganizationUnit
from apps.tenancy.models import Tenant, TenantMembership


def active_member(tenant_id, user_id):
    return TenantMembership.objects.filter(
        tenant_id=tenant_id, user_id=user_id, is_active=True, deleted_at__isnull=True,
    ).exists()


class AssessmentTemplate(UUIDTimeStampedModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="assessment_templates")
    organization_unit = models.ForeignKey(
        OrganizationUnit, on_delete=models.PROTECT, null=True, blank=True, related_name="assessment_templates",
    )
    code = models.CharField(max_length=100)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="owned_assessment_templates")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["tenant", "code"], name="uq_assess_template_tenant_code")]

    def clean(self):
        if self.organization_unit_id and (
            self.organization_unit.tenant_id != self.tenant_id or self.organization_unit.deleted_at
        ):
            raise ValidationError({"organization_unit": "Template scope is outside tenant."})
        if self.owner_id and not active_member(self.tenant_id, self.owner_id):
            raise ValidationError({"owner": "Owner must be an active tenant member."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code}: {self.title}"


class AssessmentTemplateVersion(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        RETIRED = "retired", "Retired"

    template = models.ForeignKey(AssessmentTemplate, on_delete=models.PROTECT, related_name="versions")
    version_code = models.CharField(max_length=80)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="published_assessment_templates",
    )
    notes = models.TextField(blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["template", "version_code"], name="uq_assess_template_version_code")]

    def clean(self):
        if self.template_id and self.template.deleted_at:
            raise ValidationError({"template": "Cannot version an archived template."})
        if self.published_by_id and not active_member(self.template.tenant_id, self.published_by_id):
            raise ValidationError({"published_by": "Publisher must be an active tenant member."})

    def save(self, *args, **kwargs):
        self.full_clean()
        previous = type(self).objects.filter(pk=self.pk).first()
        if previous:
            if previous.status != self.Status.DRAFT:
                immutable = ("template_id", "version_code", "published_at", "published_by_id", "notes")
                if any(getattr(previous, key) != getattr(self, key) for key in immutable):
                    raise ValidationError("Published template version is immutable.")
                if self.status not in {previous.status, self.Status.RETIRED}:
                    raise ValidationError("Invalid published template lifecycle transition.")
            elif self.status == self.Status.PUBLISHED and (not self.published_by_id or not self.published_at):
                raise ValidationError("Publishing requires an accountable publisher and timestamp.")
        return super().save(*args, **kwargs)


class TemplateCriterion(UUIDTimeStampedModel):
    class ResponseType(models.TextChoices):
        BOOLEAN = "boolean", "Yes/No"
        NUMBER = "number", "Number"
        CHOICE = "choice", "Single choice"
        TEXT = "text", "Text"

    version = models.ForeignKey(AssessmentTemplateVersion, on_delete=models.PROTECT, related_name="criteria")
    code = models.CharField(max_length=120)
    title = models.TextField()
    description = models.TextField(blank=True)
    response_type = models.CharField(max_length=16, choices=ResponseType.choices)
    choices = models.JSONField(default=list, blank=True)
    required = models.BooleanField(default=True)
    weight = models.DecimalField(max_digits=8, decimal_places=3, default=1, validators=[MinValueValidator(0)])
    applicability_mode = models.CharField(max_length=12, choices=[("always", "Always"), ("review", "Manual review")], default="always")
    sort_order = models.IntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["version", "code"], name="uq_assess_criterion_version_code")]
        ordering = ["sort_order", "code"]

    def clean(self):
        if self.version_id and (self.version.deleted_at or self.version.status != AssessmentTemplateVersion.Status.DRAFT):
            raise ValidationError({"version": "Criteria can only change in draft versions."})
        if self.response_type == self.ResponseType.CHOICE:
            if not isinstance(self.choices, list) or len(self.choices) < 2 or len(self.choices) > 40:
                raise ValidationError({"choices": "Choice criterion requires 2–40 items."})
            if any(not isinstance(x, str) or not x.strip() or len(x) > 120 for x in self.choices):
                raise ValidationError({"choices": "Choices must be short, non-empty strings."})
            if len(set(self.choices)) != len(self.choices):
                raise ValidationError({"choices": "Choices must be unique."})
        elif self.choices:
            raise ValidationError({"choices": "Only choice criteria may have options."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class ComplianceAssessmentProfile(UUIDTimeStampedModel):
    """Links published generic templates to a legally sourced FrameworkVersion."""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="compliance_assessment_profiles")
    template_version = models.ForeignKey(AssessmentTemplateVersion, on_delete=models.PROTECT, related_name="compliance_profiles")
    framework_version = models.ForeignKey(FrameworkVersion, on_delete=models.PROTECT, related_name="generic_assessment_profiles")
    title = models.CharField(max_length=255)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=["tenant", "template_version", "framework_version"], name="uq_compliance_assessment_profile",
        )]

    def clean(self):
        if self.template_version_id and (
            self.template_version.template.tenant_id != self.tenant_id or self.template_version.deleted_at
        ):
            raise ValidationError({"template_version": "Template version outside tenant."})
        if self.framework_version_id and (
            self.framework_version.framework.tenant_id not in (None, self.tenant_id) or self.framework_version.deleted_at
        ):
            raise ValidationError({"framework_version": "Framework version not authorized for tenant."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class CriterionRequirementMapping(UUIDTimeStampedModel):
    profile = models.ForeignKey(ComplianceAssessmentProfile, on_delete=models.PROTECT, related_name="criterion_mappings")
    criterion = models.ForeignKey(TemplateCriterion, on_delete=models.PROTECT, related_name="requirement_mappings")
    requirement = models.ForeignKey(Requirement, on_delete=models.PROTECT, related_name="template_criterion_mappings")

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=["profile", "criterion", "requirement"], name="uq_generic_criterion_requirement",
        )]

    def clean(self):
        if self.profile_id and self.criterion_id and self.criterion.version_id != self.profile.template_version_id:
            raise ValidationError({"criterion": "Criterion must be from profile template version."})
        if self.profile_id and self.requirement_id and self.requirement.framework_version_id != self.profile.framework_version_id:
            raise ValidationError({"requirement": "Requirement must be from profile framework version."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class GenericAssessmentRun(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="generic_assessment_runs")
    template_version = models.ForeignKey(AssessmentTemplateVersion, on_delete=models.PROTECT, related_name="assessment_runs")
    profile = models.ForeignKey(ComplianceAssessmentProfile, on_delete=models.PROTECT, null=True, blank=True, related_name="assessment_runs")
    organization_unit = models.ForeignKey(OrganizationUnit, on_delete=models.PROTECT, null=True, blank=True, related_name="generic_assessment_runs")
    title = models.CharField(max_length=255)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="owned_generic_assessments")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    completed_at = models.DateTimeField(null=True, blank=True)

    def clean(self):
        if self.template_version_id:
            existing = type(self).objects.filter(pk=self.pk).first()
            usable = {AssessmentTemplateVersion.Status.PUBLISHED} if not existing else {
                AssessmentTemplateVersion.Status.PUBLISHED, AssessmentTemplateVersion.Status.RETIRED,
            }
            if (self.template_version.template.tenant_id != self.tenant_id or
                self.template_version.deleted_at or self.template_version.status not in usable):
                raise ValidationError({"template_version": "A published template for this tenant is required."})
        if self.organization_unit_id and (
            self.organization_unit.tenant_id != self.tenant_id or self.organization_unit.deleted_at
        ):
            raise ValidationError({"organization_unit": "Organization unit outside tenant."})
        if self.template_version_id and self.template_version.template.organization_unit_id not in {None, self.organization_unit_id}:
            raise ValidationError({"organization_unit": "Run must match scoped template."})
        if self.profile_id and (
            self.profile.tenant_id != self.tenant_id or self.profile.template_version_id != self.template_version_id
        ):
            raise ValidationError({"profile": "Compliance profile does not match template or tenant."})
        if self.owner_id and not active_member(self.tenant_id, self.owner_id):
            raise ValidationError({"owner": "Owner must be an active tenant member."})

    def save(self, *args, **kwargs):
        self.full_clean()
        previous = type(self).objects.filter(pk=self.pk).first()
        if previous:
            if any(getattr(previous, key) != getattr(self, key) for key in (
                "tenant_id", "template_version_id", "profile_id", "organization_unit_id",
            )):
                raise ValidationError("Assessment run scope and published template are immutable.")
            if previous.status == self.Status.COMPLETED and self.status != self.Status.COMPLETED:
                raise ValidationError("Completed assessments cannot be reopened.")
        return super().save(*args, **kwargs)


class GenericAssessmentItem(UUIDTimeStampedModel):
    run = models.ForeignKey(GenericAssessmentRun, on_delete=models.PROTECT, related_name="items")
    criterion = models.ForeignKey(TemplateCriterion, on_delete=models.PROTECT, related_name="assessment_items")
    criterion_code_snapshot = models.CharField(max_length=120)
    criterion_title_snapshot = models.TextField()
    response_type_snapshot = models.CharField(max_length=16)
    options_snapshot = models.JSONField(default=list, blank=True)
    weight_snapshot = models.DecimalField(max_digits=8, decimal_places=3)
    required_snapshot = models.BooleanField(default=True)
    applicability_mode_snapshot = models.CharField(max_length=12, default="always")
    answer = models.JSONField(null=True, blank=True)
    score_percent = models.DecimalField(max_digits=7, decimal_places=3, null=True, blank=True)
    assessed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="generic_assessment_answers")
    assessed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["run", "criterion"], name="uq_generic_run_criterion")]

    def clean(self):
        if self.criterion_id and self.run_id and self.criterion.version_id != self.run.template_version_id:
            raise ValidationError({"criterion": "Item criterion not from assessment template version."})
        if self.run_id and self.run.status == GenericAssessmentRun.Status.COMPLETED:
            raise ValidationError("Completed assessment items cannot be changed.")

    def save(self, *args, **kwargs):
        self.full_clean()
        previous = type(self).objects.filter(pk=self.pk).first()
        if previous and any(getattr(previous, key) != getattr(self, key) for key in (
            "run_id", "criterion_id", "criterion_code_snapshot", "criterion_title_snapshot",
            "response_type_snapshot", "options_snapshot", "weight_snapshot", "required_snapshot",
            "applicability_mode_snapshot",
        )):
            raise ValidationError("Criterion snapshot cannot be mutated.")
        return super().save(*args, **kwargs)


class ApplicabilityDecision(UUIDTimeStampedModel):
    class Decision(models.TextChoices):
        APPLICABLE = "applicable", "Applicable"
        NOT_APPLICABLE = "not_applicable", "Not applicable"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="generic_applicability_decisions")
    generic_item = models.ForeignKey(GenericAssessmentItem, on_delete=models.PROTECT, null=True, blank=True, related_name="applicability_decisions")
    legacy_item = models.ForeignKey(AssessmentItem, on_delete=models.PROTECT, null=True, blank=True, related_name="governed_applicability_decisions")
    decision = models.CharField(max_length=20, choices=Decision.choices)
    rationale = models.TextField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="proposed_applicability_decisions")
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="reviewed_applicability_decisions")
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.CheckConstraint(
            condition=(Q(generic_item__isnull=False, legacy_item__isnull=True) |
                       Q(generic_item__isnull=True, legacy_item__isnull=False)),
            name="ck_applicability_exactly_one_item",
        )]

    def clean(self):
        if self.generic_item_id and self.generic_item.run.tenant_id != self.tenant_id:
            raise ValidationError({"generic_item": "Generic item outside tenant."})
        if self.generic_item_id and self.generic_item.run.status == GenericAssessmentRun.Status.COMPLETED:
            raise ValidationError({"generic_item": "Completed assessments cannot receive new applicability decisions."})
        if self.legacy_item_id and self.legacy_item.assessment.tenant_id != self.tenant_id:
            raise ValidationError({"legacy_item": "Historical assessment item outside tenant."})
        if bool(self.generic_item_id) == bool(self.legacy_item_id):
            raise ValidationError("An applicability decision must target exactly one item.")
        if not self.rationale.strip():
            raise ValidationError({"rationale": "Rationale is mandatory."})
        if self.created_by_id and not active_member(self.tenant_id, self.created_by_id):
            raise ValidationError({"created_by": "Actor is not an active member."})
        if self.reviewed_by_id and (
            self.reviewed_by_id == self.created_by_id or not active_member(self.tenant_id, self.reviewed_by_id)
        ):
            raise ValidationError({"reviewed_by": "Independent, active reviewer required."})
        if bool(self.reviewed_by_id) != bool(self.reviewed_at):
            raise ValidationError("Reviewer and review time must be set together.")

    def save(self, *args, **kwargs):
        self.full_clean()
        previous = type(self).objects.filter(pk=self.pk).first()
        if previous:
            if any(getattr(previous, key) != getattr(self, key) for key in (
                "tenant_id", "generic_item_id", "legacy_item_id", "decision", "rationale", "created_by_id",
            )):
                raise ValidationError("Applicability decision history is immutable.")
            if previous.reviewed_at and (
                self.reviewed_at != previous.reviewed_at or self.reviewed_by_id != previous.reviewed_by_id
            ):
                raise ValidationError("Reviewed applicability is immutable.")
        return super().save(*args, **kwargs)
