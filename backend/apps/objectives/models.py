from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.common.models import UUIDTimeStampedModel
from apps.organizations.models import OrganizationUnit
from apps.risks.models import Risk
from apps.tenancy.models import Tenant, TenantMembership


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
        ARCHIVED = "archived", "Archived"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="objectives")
    organization_unit = models.ForeignKey(OrganizationUnit, null=True, blank=True, on_delete=models.PROTECT, related_name="objectives")
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="children")
    code = models.CharField(max_length=100)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    objective_type = models.CharField(max_length=24, choices=ObjectiveType.choices, default=ObjectiveType.STRATEGIC)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="owned_objectives")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    target_date = models.DateField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["tenant", "code"], name="uq_objective_tenant_code")]

    def clean(self):
        if self.organization_unit_id and self.organization_unit.tenant_id != self.tenant_id:
            raise ValidationError({"organization_unit": "Unit must belong to the selected tenant."})
        if self.owner_id and not TenantMembership.objects.filter(tenant_id=self.tenant_id, user_id=self.owner_id, is_active=True).exists():
            raise ValidationError({"owner": "Owner must be an active tenant member."})
        if self.parent_id:
            if self.parent_id == self.id:
                raise ValidationError({"parent": "An objective cannot parent itself."})
            if self.parent.tenant_id != self.tenant_id or self.parent.deleted_at:
                raise ValidationError({"parent": "Parent must be an active objective in the same tenant."})
            if self.parent.organization_unit_id != self.organization_unit_id:
                raise ValidationError({"parent": "Parent and child must share an organization scope."})
            seen = set()
            node = self.parent
            while node is not None and node.id not in seen:
                if node.id == self.id:
                    raise ValidationError({"parent": "Hierarchy cycle is not allowed."})
                seen.add(node.id)
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

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="risk_objective_links")
    risk = models.ForeignKey(Risk, on_delete=models.PROTECT, related_name="objective_links")
    objective = models.ForeignKey(Objective, on_delete=models.PROTECT, related_name="risk_links")
    relationship_type = models.CharField(max_length=20, choices=RelationshipType.choices, default=RelationshipType.THREATENS)
    rationale = models.TextField(blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["risk", "objective", "relationship_type"], condition=Q(deleted_at__isnull=True), name="uq_active_risk_objective")]

    def clean(self):
        if self.risk_id and self.objective_id:
            if self.risk.deleted_at or self.objective.deleted_at or self.risk.tenant_id != self.tenant_id or self.objective.tenant_id != self.tenant_id:
                raise ValidationError("Both endpoints must be active and belong to the same tenant.")
            if self.risk.organization_unit_id != self.objective.organization_unit_id:
                raise ValidationError("Both endpoints must share an organization scope.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.risk_id} → {self.objective_id}"
