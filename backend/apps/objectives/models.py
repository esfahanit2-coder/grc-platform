from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.common.models import UUIDTimeStampedModel
from apps.organizations.models import OrganizationUnit
from apps.risks.models import Risk
from apps.tenancy.models import Tenant


class Objective(UUIDTimeStampedModel):
    class ObjectiveType(models.TextChoices):
        STRATEGIC = "strategic", "Strategic"
        OPERATIONAL = "operational", "Operational"
        FINANCIAL = "financial", "Financial"
        COMPLIANCE = "compliance", "Compliance"
        SECURITY = "security", "Security"
        RESILIENCE = "resilience", "Resilience"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        ACHIEVED = "achieved", "Achieved"
        RETIRED = "retired", "Retired"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="objectives")
    organization_unit = models.ForeignKey(
        OrganizationUnit,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="objectives",
    )
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )
    code = models.CharField(max_length=100)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    objective_type = models.CharField(
        max_length=20, choices=ObjectiveType.choices, default=ObjectiveType.OPERATIONAL
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="owned_objectives"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    target_date = models.DateField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "code"], name="uq_objective_tenant_code"),
        ]
        indexes = [
            models.Index(fields=["tenant", "status"], name="objective_tenant_status_idx"),
            models.Index(
                fields=["tenant", "organization_unit", "status"],
                name="objective_tenant_org_status_idx",
            ),
            models.Index(fields=["tenant", "owner"], name="objective_tenant_owner_idx"),
        ]

    def clean(self):
        if self.organization_unit_id and self.organization_unit.tenant_id != self.tenant_id:
            raise ValidationError({"organization_unit": "Organization unit must belong to tenant."})
        if self.parent_id:
            if self.parent_id == self.id:
                raise ValidationError({"parent": "An objective cannot be its own parent."})
            if self.parent.tenant_id != self.tenant_id:
                raise ValidationError({"parent": "Parent objective must belong to tenant."})
            node = self.parent
            visited = set()
            while node is not None and node.id not in visited:
                if self.id and node.id == self.id:
                    raise ValidationError({"parent": "Objective hierarchy cannot contain cycles."})
                visited.add(node.id)
                node = node.parent

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} — {self.title}"


class RiskObjective(UUIDTimeStampedModel):
    class RelationshipType(models.TextChoices):
        THREATENS = "threatens", "Threatens"
        SUPPORTS = "supports", "Supports"
        DEPENDENCY = "dependency", "Dependency"

    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="risk_objective_links"
    )
    risk = models.ForeignKey(
        Risk, on_delete=models.CASCADE, related_name="objective_links"
    )
    objective = models.ForeignKey(
        Objective, on_delete=models.CASCADE, related_name="risk_links"
    )
    relationship_type = models.CharField(
        max_length=20, choices=RelationshipType.choices, default=RelationshipType.THREATENS
    )
    rationale = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "risk", "objective", "relationship_type"],
                name="uq_risk_objective_relationship",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "risk"], name="objective_link_risk_idx"),
            models.Index(fields=["tenant", "objective"], name="objective_link_obj_idx"),
        ]

    def clean(self):
        if self.risk_id and self.risk.tenant_id != self.tenant_id:
            raise ValidationError({"risk": "Risk must belong to tenant."})
        if self.objective_id and self.objective.tenant_id != self.tenant_id:
            raise ValidationError({"objective": "Objective must belong to tenant."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
