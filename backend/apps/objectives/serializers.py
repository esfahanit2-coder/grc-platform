from rest_framework import serializers

from apps.tenancy.models import TenantMembership
from .models import Objective, RiskObjective


def _active_member(user, tenant):
    return bool(
        user
        and TenantMembership.objects.filter(
            tenant=tenant, user=user, is_active=True
        ).exists()
    )


class ObjectiveSerializer(serializers.ModelSerializer):
    owner_display = serializers.SerializerMethodField()
    organization_name = serializers.CharField(
        source="organization_unit.name", read_only=True
    )
    children_count = serializers.SerializerMethodField()

    class Meta:
        model = Objective
        fields = [
            "id",
            "organization_unit",
            "organization_name",
            "parent",
            "code",
            "title",
            "description",
            "objective_type",
            "owner",
            "owner_display",
            "status",
            "target_date",
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
                {"parent": "Parent objective must belong to tenant."}
            )
        if self.instance and parent and parent.id == self.instance.id:
            raise serializers.ValidationError(
                {"parent": "An objective cannot be its own parent."}
            )
        if self.instance and parent:
            node = parent
            visited = set()
            while node is not None and node.id not in visited:
                if node.id == self.instance.id:
                    raise serializers.ValidationError(
                        {"parent": "Moving this objective would create a hierarchy cycle."}
                    )
                visited.add(node.id)
                node = node.parent
        if owner and not _active_member(owner, tenant):
            raise serializers.ValidationError(
                {"owner": "Owner must be an active tenant member."}
            )
        return attrs


class RiskObjectiveSerializer(serializers.ModelSerializer):
    risk_code = serializers.CharField(source="risk.code", read_only=True)
    objective_code = serializers.CharField(source="objective.code", read_only=True)
    objective_title = serializers.CharField(source="objective.title", read_only=True)

    class Meta:
        model = RiskObjective
        fields = [
            "id",
            "risk",
            "risk_code",
            "objective",
            "objective_code",
            "objective_title",
            "relationship_type",
            "rationale",
            "created_at",
        ]
        read_only_fields = [
            "risk_code",
            "objective_code",
            "objective_title",
            "created_at",
        ]

    def validate(self, attrs):
        tenant = self.context["tenant"]
        risk = attrs.get("risk", getattr(self.instance, "risk", None))
        objective = attrs.get("objective", getattr(self.instance, "objective", None))
        if risk is None or risk.tenant_id != tenant.id:
            raise serializers.ValidationError({"risk": "Risk must belong to tenant."})
        if objective is None or objective.tenant_id != tenant.id:
            raise serializers.ValidationError(
                {"objective": "Objective must belong to tenant."}
            )
        if self.instance:
            if "risk" in attrs and attrs["risk"].id != self.instance.risk_id:
                raise serializers.ValidationError({"risk": "Risk link is immutable."})
            if (
                "objective" in attrs
                and attrs["objective"].id != self.instance.objective_id
            ):
                raise serializers.ValidationError(
                    {"objective": "Objective link is immutable."}
                )
        return attrs
