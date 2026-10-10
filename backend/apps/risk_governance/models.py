from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone
from apps.common.models import UUIDTimeStampedModel
from apps.organizations.models import OrganizationUnit
from apps.risks.models import Risk, RiskEvaluation
from apps.tenancy.models import Tenant, TenantMembership


def member(tenant_id, user_id):
    return TenantMembership.objects.filter(tenant_id=tenant_id, user_id=user_id, is_active=True).exists()


class RiskAppetiteStatement(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        APPROVED = "approved", "Approved"
        RETIRED = "retired", "Retired"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="risk_appetites")
    organization_unit = models.ForeignKey(OrganizationUnit, null=True, blank=True, on_delete=models.PROTECT, related_name="risk_appetites")
    code = models.CharField(max_length=100)
    version = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="owned_risk_appetites")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    effective_from = models.DateField()
    effective_until = models.DateField(null=True, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="approved_risk_appetites")
    approved_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["tenant", "code", "version"], name="uq_appetite_tenant_code_version")]

    def clean(self):
        if self.organization_unit_id and self.organization_unit.tenant_id != self.tenant_id:
            raise ValidationError({"organization_unit": "Unit outside tenant."})
        if self.owner_id and not member(self.tenant_id, self.owner_id):
            raise ValidationError({"owner": "Owner must be active tenant member."})
        if self.approved_by_id and not member(self.tenant_id, self.approved_by_id):
            raise ValidationError({"approved_by": "Approver must be active tenant member."})
        if self.effective_until and self.effective_until < self.effective_from:
            raise ValidationError({"effective_until": "End precedes start."})

    def save(self, *args, **kwargs):
        self.full_clean()
        previous = type(self).objects.filter(pk=self.pk).first()
        if previous and previous.status != self.Status.DRAFT:
            changed = [
                field.attname for field in self._meta.concrete_fields
                if field.name not in {"status", "updated_at"} and getattr(previous, field.attname) != getattr(self, field.attname)
            ]
            if changed or self.status not in {previous.status, self.Status.RETIRED}:
                raise ValidationError("Approved appetite is immutable. Create a new version.")
        if previous and previous.status == self.Status.DRAFT and self.status == self.Status.APPROVED and not self.approved_by_id:
            raise ValidationError("Approval must name an approver.")
        return super().save(*args, **kwargs)

    def is_effective(self, on_date=None):
        day = on_date or timezone.localdate()
        return (self.status == self.Status.APPROVED and self.effective_from <= day
                and (self.effective_until is None or day <= self.effective_until))

    def __str__(self):
        return f"{self.code}/v{self.version} — {self.title}"


class RiskTolerance(UUIDTimeStampedModel):
    statement = models.ForeignKey(RiskAppetiteStatement, on_delete=models.PROTECT, related_name="tolerances")
    evaluation_type = models.CharField(max_length=16, choices=[("current", "Current"), ("residual", "Residual")], default="residual")
    maximum_score = models.DecimalField(max_digits=14, decimal_places=4, validators=[MinValueValidator(0)])
    description = models.TextField(blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["statement", "evaluation_type"], condition=Q(deleted_at__isnull=True), name="uq_tolerance_statement_eval")]

    def clean(self):
        if self.statement_id and (self.statement.deleted_at or self.statement.status != RiskAppetiteStatement.Status.DRAFT):
            raise ValidationError({"statement": "Tolerance can be edited only for draft appetite."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class RiskAcceptance(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        SUPERSEDED = "superseded", "Superseded"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="risk_acceptances")
    risk = models.ForeignKey(Risk, on_delete=models.PROTECT, related_name="acceptances")
    evaluation = models.ForeignKey(RiskEvaluation, on_delete=models.PROTECT, related_name="acceptances")
    appetite = models.ForeignKey(RiskAppetiteStatement, on_delete=models.PROTECT, related_name="acceptances")
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="risk_acceptance_requests")
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="risk_acceptance_decisions")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    rationale = models.TextField()
    decision_note = models.TextField(blank=True)
    review_on = models.DateField()
    expires_on = models.DateField()
    decided_at = models.DateTimeField(null=True, blank=True)
    supersedes = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="successors")
    evaluation_type_snapshot = models.CharField(max_length=16)
    score_snapshot = models.DecimalField(max_digits=14, decimal_places=4)
    likelihood_snapshot = models.DecimalField(max_digits=10, decimal_places=2)
    impact_snapshot = models.DecimalField(max_digits=10, decimal_places=2)
    evaluated_at_snapshot = models.DateTimeField()
    tolerance_max_snapshot = models.DecimalField(max_digits=14, decimal_places=4)
    exceeds_tolerance = models.BooleanField(default=False)
    exception_justification = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "risk", "status"], name="accept_tenant_risk_status_idx"),
            models.Index(fields=["status", "review_on"], name="accept_status_review_idx"),
            models.Index(fields=["status", "expires_on"], name="accept_status_expiry_idx"),
        ]

    def clean(self):
        if self.risk_id and (self.risk.tenant_id != self.tenant_id or self.risk.deleted_at):
            raise ValidationError({"risk": "Risk outside tenant or archived."})
        if self.evaluation_id and self.risk_id and (self.evaluation.risk_id != self.risk_id or self.evaluation.deleted_at):
            raise ValidationError({"evaluation": "Evaluation must belong to this risk."})
        if self.appetite_id and self.risk_id and (
            self.appetite.tenant_id != self.tenant_id or self.appetite.deleted_at or
            self.appetite.organization_unit_id not in {None, self.risk.organization_unit_id}
        ):
            raise ValidationError({"appetite": "Appetite must match tenant and organizational scope."})
        if self.requested_by_id and not member(self.tenant_id, self.requested_by_id):
            raise ValidationError({"requested_by": "Requester must be an active tenant member."})
        if self.decided_by_id and not member(self.tenant_id, self.decided_by_id):
            raise ValidationError({"decided_by": "Approver must be an active tenant member."})
        if self.decided_by_id and self.decided_by_id == self.requested_by_id:
            raise ValidationError({"decided_by": "Requester cannot decide their own acceptance."})
        if self.review_on and self.expires_on and self.review_on > self.expires_on:
            raise ValidationError({"review_on": "Review must precede expiry."})
        if self.supersedes_id and (
            self.supersedes_id == self.id or self.supersedes.tenant_id != self.tenant_id or self.supersedes.risk_id != self.risk_id
        ):
            raise ValidationError({"supersedes": "Supersession must target the same risk and tenant."})

    def save(self, *args, **kwargs):
        self.full_clean()
        previous = type(self).objects.filter(pk=self.pk).first()
        if previous:
            immutable = (
                "tenant_id", "risk_id", "evaluation_id", "appetite_id", "requested_by_id",
                "rationale", "review_on", "expires_on", "supersedes_id",
                "evaluation_type_snapshot", "score_snapshot", "likelihood_snapshot",
                "impact_snapshot", "evaluated_at_snapshot", "tolerance_max_snapshot",
                "exceeds_tolerance", "exception_justification",
            )
            if any(getattr(self, key) != getattr(previous, key) for key in immutable):
                raise ValidationError("Acceptance request and evaluation snapshot are immutable.")
            transitions = {
                self.Status.PENDING: {self.Status.PENDING, self.Status.APPROVED, self.Status.REJECTED},
                self.Status.APPROVED: {self.Status.APPROVED, self.Status.SUPERSEDED},
                self.Status.REJECTED: {self.Status.REJECTED},
                self.Status.SUPERSEDED: {self.Status.SUPERSEDED},
            }
            if self.status not in transitions[previous.status]:
                raise ValidationError("Invalid decision state transition.")
        return super().save(*args, **kwargs)

    def is_active(self, on_date=None):
        return self.status == self.Status.APPROVED and self.expires_on >= (on_date or timezone.localdate())
