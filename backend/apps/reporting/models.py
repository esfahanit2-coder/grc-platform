from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.common.models import UUIDTimeStampedModel
from apps.controls.models import Control, ControlImplementation
from apps.frameworks.models import FrameworkVersion
from apps.organizations.models import OrganizationUnit
from apps.risks.models import RiskTreatment
from apps.tenancy.models import Tenant


class SoARegister(UUIDTimeStampedModel):
    """Tenant-scoped *draft* decision workspace, not an approved statement."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft / not approved"

    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT, related_name="soa_registers")
    organization_unit = models.ForeignKey(OrganizationUnit, on_delete=models.PROTECT, related_name="soa_registers")
    framework_version = models.ForeignKey(FrameworkVersion, on_delete=models.PROTECT, related_name="soa_registers")
    title = models.CharField(max_length=255)
    revision = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_soa_registers")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "organization_unit", "framework_version", "revision"],
                name="uq_soa_scope_version_revision",
            ),
        ]
        indexes = [models.Index(fields=["tenant", "organization_unit", "status"], name="soa_register_scope_idx")]

    def clean(self):
        if self.organization_unit_id and self.organization_unit.tenant_id != self.tenant_id:
            raise ValidationError({"organization_unit": "Organizational scope must belong to this tenant."})
        if self.framework_version_id:
            if self.framework_version.framework.tenant_id != self.tenant_id:
                raise ValidationError({"framework_version": "Only tenant-owned authorized framework versions can be used."})
            if not self.framework_version.is_locked:
                raise ValidationError({"framework_version": "Framework version must be locked before creating SoA drafts."})
        if self.status != self.Status.DRAFT:
            raise ValidationError({"status": "Approved statements require the separate human approval workflow."})
        if self.revision < 1:
            raise ValidationError({"revision": "Revision must be positive."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class SoAControlDecision(UUIDTimeStampedModel):
    """Unapproved control selection with explicit human rationale."""

    class Decision(models.TextChoices):
        UNDECIDED = "undecided", "Undecided"
        INCLUDED = "included", "Included / necessary"
        EXCLUDED = "excluded", "Excluded / not selected"

    class ReferenceKind(models.TextChoices):
        ANNEX_A = "annex_a", "Annex A reference"
        ADDITIONAL = "additional", "Additional organizational control"

    register = models.ForeignKey(SoARegister, on_delete=models.PROTECT, related_name="control_decisions")
    control = models.ForeignKey(Control, on_delete=models.PROTECT, related_name="soa_decisions")
    reference_kind = models.CharField(max_length=20, choices=ReferenceKind.choices)
    source_identifier = models.CharField(max_length=120)
    decision = models.CharField(max_length=16, choices=Decision.choices, default=Decision.UNDECIDED)
    rationale = models.TextField(blank=True)
    control_implementation = models.ForeignKey(
        ControlImplementation, null=True, blank=True, on_delete=models.PROTECT, related_name="soa_decisions"
    )
    risk_treatment = models.ForeignKey(
        RiskTreatment, null=True, blank=True, on_delete=models.PROTECT, related_name="soa_decisions"
    )
    last_edited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="edited_soa_decisions"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["register", "control"], name="uq_soa_register_control"),
            models.UniqueConstraint(fields=["register", "reference_kind", "source_identifier"], name="uq_soa_register_reference"),
        ]
        indexes = [models.Index(fields=["register", "decision"], name="soa_decisions_state_idx")]

    def clean(self):
        if not self.register_id:
            return
        scope = self.register
        if scope.status != SoARegister.Status.DRAFT:
            raise ValidationError({"register": "Only draft registers may be edited."})
        if self.control_id:
            if self.control.deleted_at or self.control.tenant_id not in {None, scope.tenant_id}:
                raise ValidationError({"control": "Control is not visible to the register tenant."})
            if self.control.tenant_id is None and self.control.status != Control.Status.ACTIVE:
                raise ValidationError({"control": "Only active global controls can be referenced."})
        if self.decision != self.Decision.UNDECIDED and not self.rationale.strip():
            raise ValidationError({"rationale": "Include/exclude decisions require a human rationale."})
        if self.decision == self.Decision.EXCLUDED and (self.control_implementation_id or self.risk_treatment_id):
            raise ValidationError({"decision": "Excluded controls cannot be marked as implemented or risk-treated."})
        if self.control_implementation_id:
            impl = self.control_implementation
            if (impl.deleted_at or impl.tenant_id != scope.tenant_id or
                    impl.organization_unit_id != scope.organization_unit_id or
                    impl.control_id != self.control_id):
                raise ValidationError({"control_implementation": "Implementation must match tenant, scope and control."})
        if self.risk_treatment_id:
            treatment = self.risk_treatment
            if (treatment.deleted_at or treatment.risk.deleted_at or
                    treatment.risk.tenant_id != scope.tenant_id or
                    treatment.risk.organization_unit_id != scope.organization_unit_id):
                raise ValidationError({"risk_treatment": "Risk treatment must match tenant and organizational scope."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
