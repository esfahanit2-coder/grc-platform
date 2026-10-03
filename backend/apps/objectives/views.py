from django.utils import timezone
from rest_framework import viewsets

from apps.audit.services import record_audit_event
from apps.identity.services import (
    accessible_organization_unit_ids,
    has_whole_tenant_permission,
    require_tenant_permission,
    require_whole_tenant_permission,
)
from apps.tenancy.services import resolve_tenant_for_request
from .models import Objective, RiskObjective
from .serializers import ObjectiveSerializer, RiskObjectiveSerializer


class TenantMixin:
    def _tenant(self):
        if not hasattr(self, "_resolved_tenant"):
            self._resolved_tenant = resolve_tenant_for_request(self.request)
        return self._resolved_tenant


class ObjectiveViewSet(TenantMixin, viewsets.ModelViewSet):
    serializer_class = ObjectiveSerializer

    def _permission_code(self):
        return "objective.view" if self.action in {"list", "retrieve"} else "objective.manage"

    def get_queryset(self):
        tenant = self._tenant()
        code = self._permission_code()
        require_tenant_permission(self.request.user, tenant, code)
        allowed = accessible_organization_unit_ids(self.request.user, tenant, code)
        whole = has_whole_tenant_permission(self.request.user, tenant, code)
        qs = (
            Objective.objects.filter(tenant=tenant, deleted_at__isnull=True)
            .select_related("organization_unit", "parent", "owner")
            .order_by("code")
        )
        return qs if whole else qs.filter(organization_unit_id__in=allowed)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["tenant"] = self._tenant()
        return context

    def perform_create(self, serializer):
        tenant = self._tenant()
        unit = serializer.validated_data.get("organization_unit")
        if unit:
            require_tenant_permission(
                self.request.user, tenant, "objective.manage", unit
            )
        else:
            require_whole_tenant_permission(
                self.request.user, tenant, "objective.manage"
            )
        obj = serializer.save(tenant=tenant)
        record_audit_event(
            self.request.user,
            tenant,
            "objective.create",
            "objective",
            obj.id,
            new_data={"code": obj.code, "title": obj.title},
            object_repr=str(obj),
            request=self.request,
        )

    def perform_update(self, serializer):
        tenant = self._tenant()
        instance = serializer.instance
        if instance.organization_unit:
            require_tenant_permission(
                self.request.user,
                tenant,
                "objective.manage",
                instance.organization_unit,
            )
        else:
            require_whole_tenant_permission(
                self.request.user, tenant, "objective.manage"
            )
        new_unit = serializer.validated_data.get(
            "organization_unit", instance.organization_unit
        )
        if new_unit:
            require_tenant_permission(
                self.request.user, tenant, "objective.manage", new_unit
            )
        else:
            require_whole_tenant_permission(
                self.request.user, tenant, "objective.manage"
            )
        old = {
            "code": instance.code,
            "title": instance.title,
            "status": instance.status,
            "organization_unit": str(instance.organization_unit_id or ""),
        }
        obj = serializer.save()
        record_audit_event(
            self.request.user,
            tenant,
            "objective.update",
            "objective",
            obj.id,
            old_data=old,
            new_data={
                "code": obj.code,
                "title": obj.title,
                "status": obj.status,
                "organization_unit": str(obj.organization_unit_id or ""),
            },
            object_repr=str(obj),
            request=self.request,
        )

    def perform_destroy(self, instance):
        tenant = self._tenant()
        if instance.organization_unit:
            require_tenant_permission(
                self.request.user,
                tenant,
                "objective.manage",
                instance.organization_unit,
            )
        else:
            require_whole_tenant_permission(
                self.request.user, tenant, "objective.manage"
            )
        instance.deleted_at = timezone.now()
        instance.status = Objective.Status.RETIRED
        instance.save(update_fields=["deleted_at", "status", "updated_at"])
        record_audit_event(
            self.request.user,
            tenant,
            "objective.archive",
            "objective",
            instance.id,
            object_repr=str(instance),
            request=self.request,
        )


class RiskObjectiveViewSet(TenantMixin, viewsets.ModelViewSet):
    serializer_class = RiskObjectiveSerializer

    def get_queryset(self):
        tenant = self._tenant()
        require_tenant_permission(self.request.user, tenant, "objective.view")
        allowed = accessible_organization_unit_ids(
            self.request.user, tenant, "objective.view"
        )
        whole = has_whole_tenant_permission(
            self.request.user, tenant, "objective.view"
        )
        qs = (
            RiskObjective.objects.filter(tenant=tenant, deleted_at__isnull=True)
            .select_related("risk", "objective", "objective__organization_unit")
            .order_by("-created_at")
        )
        if self.request.query_params.get("risk"):
            qs = qs.filter(risk_id=self.request.query_params["risk"])
        if self.request.query_params.get("objective"):
            qs = qs.filter(objective_id=self.request.query_params["objective"])
        return qs if whole else qs.filter(objective__organization_unit_id__in=allowed)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["tenant"] = self._tenant()
        return context

    def _require_manage(self, obj):
        tenant = self._tenant()
        objective = obj.objective
        risk = obj.risk
        if objective.organization_unit:
            require_tenant_permission(
                self.request.user,
                tenant,
                "objective.manage",
                objective.organization_unit,
            )
        else:
            require_whole_tenant_permission(
                self.request.user, tenant, "objective.manage"
            )
        if risk.organization_unit:
            require_tenant_permission(
                self.request.user, tenant, "risk.view", risk.organization_unit
            )
        else:
            require_whole_tenant_permission(self.request.user, tenant, "risk.view")

    def perform_create(self, serializer):
        tenant = self._tenant()
        pending = RiskObjective(
            tenant=tenant,
            risk=serializer.validated_data["risk"],
            objective=serializer.validated_data["objective"],
            relationship_type=serializer.validated_data.get(
                "relationship_type", RiskObjective.RelationshipType.THREATENS
            ),
        )
        self._require_manage(pending)
        obj = serializer.save(tenant=tenant)
        record_audit_event(
            self.request.user,
            tenant,
            "objective.risk_link.create",
            "risk_objective",
            obj.id,
            metadata={"risk_id": str(obj.risk_id), "objective_id": str(obj.objective_id)},
            request=self.request,
        )

    def perform_update(self, serializer):
        self._require_manage(serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        tenant = self._tenant()
        self._require_manage(instance)
        instance.deleted_at = timezone.now()
        instance.save(update_fields=["deleted_at", "updated_at"])
        record_audit_event(
            self.request.user,
            tenant,
            "objective.risk_link.delete",
            "risk_objective",
            instance.id,
            request=self.request,
        )
