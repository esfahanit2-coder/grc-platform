from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.common.models import UUIDTimeStampedModel
from apps.controls.models import ControlImplementation
from apps.internal_audits.models import AuditEngagement
from apps.organizations.models import OrganizationUnit
from apps.risks.models import Risk
from apps.tenancy.models import Tenant


class BusinessProcess(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        RETIRED = "retired", "Retired"

    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="business_processes"
    )
    organization_unit = models.ForeignKey(
        OrganizationUnit,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="business_processes",
    )
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )
    code = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_business_processes",
    )
    criticality = models.DecimalField(max_digits=6, decimal_places=2, default=3)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"], name="uq_business_process_tenant_code"
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant", "parent"], name="process_tenant_parent_idx"
            ),
            models.Index(
                fields=["tenant", "organization_unit", "status"],
                name="process_tenant_org_status_idx",
            ),
            models.Index(fields=["tenant", "owner"], name="process_tenant_owner_idx"),
        ]

    def clean(self):
        if self.organization_unit_id and self.organization_unit.tenant_id != self.tenant_id:
            raise ValidationError({"organization_unit": "Organization unit must belong to tenant."})
        if self.parent_id:
            if self.parent_id == self.id:
                raise ValidationError({"parent": "A process cannot be its own parent."})
            if self.parent.tenant_id != self.tenant_id:
                raise ValidationError({"parent": "Parent process must belong to tenant."})
            node = self.parent
            visited = set()
            while node is not None and node.id not in visited:
                if self.id and node.id == self.id:
                    raise ValidationError({"parent": "Process hierarchy cannot contain cycles."})
                visited.add(node.id)
                node = node.parent

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} — {self.name}"


class RiskProcess(UUIDTimeStampedModel):
    class RelationshipType(models.TextChoices):
        PRIMARY = "primary", "Primary"
        SUPPORTING = "supporting", "Supporting"
        DEPENDENCY = "dependency", "Dependency"

    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="risk_process_links"
    )
    risk = models.ForeignKey(Risk, on_delete=models.CASCADE, related_name="process_links")
    process = models.ForeignKey(
        BusinessProcess, on_delete=models.CASCADE, related_name="risk_links"
    )
    relationship_type = models.CharField(
        max_length=20, choices=RelationshipType.choices, default=RelationshipType.PRIMARY
    )
    rationale = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "risk", "process", "relationship_type"],
                name="uq_risk_process_relationship",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "risk"], name="process_link_risk_idx"),
            models.Index(fields=["tenant", "process"], name="process_link_proc_idx"),
        ]

    def clean(self):
        if self.risk_id and self.risk.tenant_id != self.tenant_id:
            raise ValidationError({"risk": "Risk must belong to tenant."})
        if self.process_id and self.process.tenant_id != self.tenant_id:
            raise ValidationError({"process": "Process must belong to tenant."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class ControlImplementationProcess(UUIDTimeStampedModel):
    class RelationshipType(models.TextChoices):
        OPERATES = "operates", "Operates in process"
        SUPPORTS = "supports", "Supports process"
        COMPENSATING = "compensating", "Compensating"

    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="control_process_links"
    )
    control_implementation = models.ForeignKey(
        ControlImplementation,
        on_delete=models.CASCADE,
        related_name="process_links",
    )
    process = models.ForeignKey(
        BusinessProcess, on_delete=models.CASCADE, related_name="control_links"
    )
    relationship_type = models.CharField(
        max_length=20, choices=RelationshipType.choices, default=RelationshipType.OPERATES
    )
    rationale = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "control_implementation", "process", "relationship_type"],
                name="uq_control_process_relationship",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant", "control_implementation"],
                name="process_link_control_idx",
            ),
            models.Index(fields=["tenant", "process"], name="process_ctrl_proc_idx"),
        ]

    def clean(self):
        if (
            self.control_implementation_id
            and self.control_implementation.tenant_id != self.tenant_id
        ):
            raise ValidationError(
                {"control_implementation": "Control implementation must belong to tenant."}
            )
        if self.process_id and self.process.tenant_id != self.tenant_id:
            raise ValidationError({"process": "Process must belong to tenant."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class AuditProcess(UUIDTimeStampedModel):
    class RelationshipType(models.TextChoices):
        SCOPE = "scope", "In scope"
        PRIMARY = "primary", "Primary process"
        SUPPORTING = "supporting", "Supporting process"

    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="audit_process_links"
    )
    audit_engagement = models.ForeignKey(
        AuditEngagement, on_delete=models.CASCADE, related_name="process_links"
    )
    process = models.ForeignKey(
        BusinessProcess, on_delete=models.CASCADE, related_name="audit_links"
    )
    relationship_type = models.CharField(
        max_length=20, choices=RelationshipType.choices, default=RelationshipType.SCOPE
    )
    rationale = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "audit_engagement", "process", "relationship_type"],
                name="uq_audit_process_relationship",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant", "audit_engagement"], name="process_link_audit_idx"
            ),
            models.Index(fields=["tenant", "process"], name="process_audit_proc_idx"),
        ]

    def clean(self):
        if self.audit_engagement_id and self.audit_engagement.tenant_id != self.tenant_id:
            raise ValidationError(
                {"audit_engagement": "Audit engagement must belong to tenant."}
            )
        if self.process_id and self.process.tenant_id != self.tenant_id:
            raise ValidationError({"process": "Process must belong to tenant."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
