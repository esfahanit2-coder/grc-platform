from apps.common.scoped_registers import ScopedEntityViewSet, ScopedLinkViewSet
from .models import Objective, RiskObjective
from .serializers import ObjectiveSerializer, RiskObjectiveSerializer


class ObjectiveViewSet(ScopedEntityViewSet):
    model = Objective
    serializer_class = ObjectiveSerializer
    related_link_names = ("risk_links",)
    read_permissions = (("objective.view", "organization_unit_id"),)
    write_permissions = (("objective.manage", "organization_unit_id"),)


class RiskObjectiveViewSet(ScopedLinkViewSet):
    model = RiskObjective
    serializer_class = RiskObjectiveSerializer
    endpoints = ("objective", "risk")
    read_permissions = (
        ("objective.view", "objective__organization_unit_id"),
        ("risk.view", "risk__organization_unit_id"),
    )
    write_permissions = (
        ("objective.manage", "objective__organization_unit_id"),
        ("risk.manage", "risk__organization_unit_id"),
    )
