from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.common.models import UUIDTimeStampedModel
from apps.controls.models import ControlImplementation
from apps.internal_audits.models import AuditEngagement
from apps.organizations.models import OrganizationUnit
from apps.risks.models import Risk
from apps.tenancy.models import Tenant, TenantMembership

class BusinessProcess(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        ARCHIVED = "archived", "Archived"

    class Criticality(models.IntegerChoices):
        VERY_LOW = 1, "Very low"
        LOW = 2, "Low"
        MODERATE = 3, "Moderate"
        HIGH = 4, "High"
        CRITICAL = 5, "Critical"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="business_processes")
    organization_unit = models.ForeignKey(OrganizationUnit, null=True, blank=True, on_delete=models.PROTECT, related_name="business_processes")
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="children")
    code = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="owned_business_processes")
    criticality = models.PositiveSmallIntegerField(choices=Criticality.choices, default=Criticality.MODERATE)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["tenant", "code"], name="uq_businessprocess_tenant_code")]

    def clean(self):
        if self.organization_unit_id and self.organization_unit.tenant_id != self.tenant_id:
            raise ValidationError({"organization_unit": "Unit must belong to the selected tenant."})
        if self.owner_id and not TenantMembership.objects.filter(tenant_id=self.tenant_id, user_id=self.owner_id, is_active=True).exists():
            raise ValidationError({"owner": "Owner must be an active tenant member."})
        if self.parent_id:
            if self.parent_id == self.id:
                raise ValidationError({"parent": "A process cannot parent itself."})
            if self.parent.tenant_id != self.tenant_id or self.parent.deleted_at:
                raise ValidationError({"parent": "Parent must be active and within this tenant."})
            if self.parent.organization_unit_id != self.organization_unit_id:
                raise ValidationError({"parent": "Parent and child must share an organization scope."})
            visited = set()
            node = self.parent
            while node is not None and node.id not in visited:
                if node.id == self.id:
                    raise ValidationError({"parent": "Hierarchy cycle is not allowed."})
                visited.add(node.id)
                node = node.parent

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} — {self.name}"

def _check_link(link, endpoint_one, endpoint_two):
    if not endpoint_one or not endpoint_two:
        return
    if endpoint_one.deleted_at or endpoint_two.deleted_at or endpoint_one.tenant_id != link.tenant_id or endpoint_two.tenant_id != link.tenant_id:
        raise ValidationError("Both link endpoints must be active and belong to the same tenant.")
    if endpoint_one.organization_unit_id != endpoint_two.organization_unit_id:
        raise ValidationError("Link endpoints must share an organization scope.")

class RiskProcess(UUIDTimeStampedModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="risk_process_links")
    risk = models.ForeignKey(Risk, on_delete=models.PROTECT, related_name="process_links")
    business_process = models.ForeignKey(BusinessProcess, on_delete=models.PROTECT, related_name="risk_links")
    relationship_type = models.CharField(max_length=30, default="impacts")
    rationale = models.TextField(blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["risk", "business_process", "relationship_type"], condition=Q(deleted_at__isnull=True), name="uq_active_risk_process")]
    def clean(self):
        if self.risk_id and self.business_process_id:
            _check_link(self, self.risk, self.business_process)
    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

class ControlImplementationProcess(UUIDTimeStampedModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="control_process_links")
    control_implementation = models.ForeignKey(ControlImplementation, on_delete=models.PROTECT, related_name="process_links")
    business_process = models.ForeignKey(BusinessProcess, on_delete=models.PROTECT, related_name="control_links")
    relationship_type = models.CharField(max_length=30, default="applies_to")
    rationale = models.TextField(blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["control_implementation", "business_process", "relationship_type"], condition=Q(deleted_at__isnull=True), name="uq_active_control_process")]
    def clean(self):
        if self.control_implementation_id and self.business_process_id:
            _check_link(self, self.control_implementation, self.business_process)
    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

class AuditProcess(UUIDTimeStampedModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="audit_process_links")
    audit_engagement = models.ForeignKey(AuditEngagement, on_delete=models.PROTECT, related_name="process_links")
    business_process = models.ForeignKey(BusinessProcess, on_delete=models.PROTECT, related_name="audit_links")
    relationship_type = models.CharField(max_length=30, default="in_scope")
    rationale = models.TextField(blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["audit_engagement", "business_process", "relationship_type"], condition=Q(deleted_at__isnull=True), name="uq_active_audit_process")]
    def clean(self):
        if self.audit_engagement_id and self.business_process_id:
            _check_link(self, self.audit_engagement, self.business_process)
    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
