from apps.common.scoped_serializers import TenantValidatedSerializer
from .models import Objective, RiskObjective


class ObjectiveSerializer(TenantValidatedSerializer):
    related_link_names = ("risk_links",)

    class Meta:
        model = Objective
        fields = ["id", "organization_unit", "parent", "code", "title", "description",
                  "objective_type", "owner", "status", "target_date", "metadata",
                  "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class RiskObjectiveSerializer(TenantValidatedSerializer):
    immutable_links = ("risk", "objective")

    class Meta:
        model = RiskObjective
        fields = ["id", "risk", "objective", "relationship_type", "rationale",
                  "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
