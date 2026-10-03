from rest_framework import serializers

from apps.tenancy.models import TenantMembership
from .models import (
    AuditProcess,
    BusinessProcess,
    ControlImplementationProcess,
    RiskProcess,
)


def _active_member(user, tenant):
    return bool(
        user
        and TenantMembership.objects.filter(
            tenant=tenant, user=user, is_active=True
        ).exists()
    )


class BusinessProcessSerializer(serializers.ModelSerializer):
    owner_display = serializers.SerializerMethodField()
    organization_name = serializers.CharField(
        source="organization_unit.name", read_only=True
    )
    children_count = serializers.SerializerMethodField()

    class Meta:
        model = BusinessProcess
        fields = [
            "id",
            "organization_unit",
            "organization_name",
            "parent",
            "code",
            "name",
            "description",
            "owner",
            "owner_display",
            "criticality",
            "status",
            "metadata",
            "children_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "organization_name",
            "owner_display",
            "children_count",
            "created_at",
            "updated_at",
        ]

    def get_owner_display(self, obj):
        return obj.owner.get_full_name() or obj.owner.get_username()

    def get_children_count(self, obj):
        return obj.children.filter(deleted_at__isnull=True).count()

    def validate(self, attrs):
        tenant = self.context["tenant"]
        unit = attrs.get(
            "organization_unit",
            getattr(self.instance, "organization_unit", None),
        )
        parent = attrs.get("parent", getattr(self.instance, "parent", None))
        owner = attrs.get("owner", getattr(self.instance, "owner", None))
        if unit and unit.tenant_id != tenant.id:
            raise serializers.ValidationError(
                {"organization_unit": "Organization unit must belong to tenant."}
            )
        if parent and parent.tenant_id != tenant.id:
            raise serializers.ValidationError(
                {"parent": "Parent process must belong to tenant."}
            )
        if self.instance and parent and parent.id == self.instance.id:
            raise serializers.ValidationError(
                {"parent": "A process cannot be its own parent."}
            )
        if self.instance and parent:
            node = parent
            visited = set()
            while node is not None and node.id not in visited:
                if node.id == self.instance.id:
                    raise serializers.ValidationError(
                        {"parent": "Moving this process would create a hierarchy cycle."}
                    )
                visited.add(node.id)
                node = node.parent
        if owner and not _active_member(owner, tenant):
            raise serializers.ValidationError(
                {"owner": "Owner must be an active tenant member."}
            )
        return attrs


class RiskProcessSerializer(serializers.ModelSerializer):
    risk_code = serializers.CharField(source="risk.code", read_only=True)
    process_code = serializers.CharField(source="process.code", read_only=True)
    process_name = serializers.CharField(source="process.name", read_only=True)

    class Meta:
        model = RiskProcess
        fields = [
            "id", "risk", "risk_code", "process", "process_code", "process_name",
            "relationship_type", "rationale", "created_at",
        ]
        read_only_fields = ["risk_code", "process_code", "process_name", "created_at"]

    def validate(self, attrs):
        tenant = self.context["tenant"]
        risk = attrs.get("risk", getattr(self.instance, "risk", None))
        process = attrs.get("process", getattr(self.instance, "process", None))
        if risk is None or risk.tenant_id != tenant.id:
            raise serializers.ValidationError({"risk": "Risk must belong to tenant."})
        if process is None or process.tenant_id != tenant.id:
            raise serializers.ValidationError({"process": "Process must belong to tenant."})
        if self.instance:
            if "risk" in attrs and attrs["risk"].id != self.instance.risk_id:
                raise serializers.ValidationError({"risk": "Risk link is immutable."})
            if "process" in attrs and attrs["process"].id != self.instance.process_id:
                raise serializers.ValidationError({"process": "Process link is immutable."})
        return attrs


class ControlImplementationProcessSerializer(serializers.ModelSerializer):
    control_code = serializers.CharField(
        source="control_implementation.control.code", read_only=True
    )
    process_code = serializers.CharField(source="process.code", read_only=True)
    process_name = serializers.CharField(source="process.name", read_only=True)

    class Meta:
        model = ControlImplementationProcess
        fields = [
            "id", "control_implementation", "control_code", "process",
            "process_code", "process_name", "relationship_type", "rationale", "created_at",
        ]
        read_only_fields = ["control_code", "process_code", "process_name", "created_at"]

    def validate(self, attrs):
        tenant = self.context["tenant"]
        control = attrs.get(
            "control_implementation",
            getattr(self.instance, "control_implementation", None),
        )
        process = attrs.get("process", getattr(self.instance, "process", None))
        if control is None or control.tenant_id != tenant.id:
            raise serializers.ValidationError(
                {"control_implementation": "Control implementation must belong to tenant."}
            )
        if process is None or process.tenant_id != tenant.id:
            raise serializers.ValidationError({"process": "Process must belong to tenant."})
        if self.instance:
            if (
                "control_implementation" in attrs
                and attrs["control_implementation"].id
                != self.instance.control_implementation_id
            ):
                raise serializers.ValidationError(
                    {"control_implementation": "Control implementation link is immutable."}
                )
            if "process" in attrs and attrs["process"].id != self.instance.process_id:
                raise serializers.ValidationError({"process": "Process link is immutable."})
        return attrs


class AuditProcessSerializer(serializers.ModelSerializer):
    audit_title = serializers.CharField(
        source="audit_engagement.title", read_only=True
    )
    process_code = serializers.CharField(source="process.code", read_only=True)
    process_name = serializers.CharField(source="process.name", read_only=True)

    class Meta:
        model = AuditProcess
        fields = [
            "id", "audit_engagement", "audit_title", "process", "process_code",
            "process_name", "relationship_type", "rationale", "created_at",
        ]
        read_only_fields = ["audit_title", "process_code", "process_name", "created_at"]

    def validate(self, attrs):
        tenant = self.context["tenant"]
        audit = attrs.get(
            "audit_engagement", getattr(self.instance, "audit_engagement", None)
        )
        process = attrs.get("process", getattr(self.instance, "process", None))
        if audit is None or audit.tenant_id != tenant.id:
            raise serializers.ValidationError(
                {"audit_engagement": "Audit engagement must belong to tenant."}
            )
        if process is None or process.tenant_id != tenant.id:
            raise serializers.ValidationError({"process": "Process must belong to tenant."})
        if self.instance:
            if (
                "audit_engagement" in attrs
                and attrs["audit_engagement"].id != self.instance.audit_engagement_id
            ):
                raise serializers.ValidationError(
                    {"audit_engagement": "Audit link is immutable."}
                )
            if "process" in attrs and attrs["process"].id != self.instance.process_id:
                raise serializers.ValidationError({"process": "Process link is immutable."})
        return attrs
