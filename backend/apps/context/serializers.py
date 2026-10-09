from apps.common.scoped_serializers import TenantValidatedSerializer
from .models import AuditProcess, BusinessProcess, ControlImplementationProcess, RiskProcess

class BusinessProcessSerializer(TenantValidatedSerializer):
    related_link_names = ("risk_links", "control_links", "audit_links")
    class Meta:
        model = BusinessProcess
        fields = ["id", "organization_unit", "parent", "code", "name", "description", "owner", "criticality", "status", "metadata", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

class RiskProcessSerializer(TenantValidatedSerializer):
    immutable_links = ("risk", "business_process")
    class Meta:
        model = RiskProcess
        fields = ["id", "risk", "business_process", "relationship_type", "rationale", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

class ControlImplementationProcessSerializer(TenantValidatedSerializer):
    immutable_links = ("control_implementation", "business_process")
    class Meta:
        model = ControlImplementationProcess
        fields = ["id", "control_implementation", "business_process", "relationship_type", "rationale", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

class AuditProcessSerializer(TenantValidatedSerializer):
    immutable_links = ("audit_engagement", "business_process")
    class Meta:
        model = AuditProcess
        fields = ["id", "audit_engagement", "business_process", "relationship_type", "rationale", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
