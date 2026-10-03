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
from .models import AuditProcess, BusinessProcess, ControlImplementationProcess, RiskProcess
from .serializers import (
    AuditProcessSerializer,
    BusinessProcessSerializer,
    ControlImplementationProcessSerializer,
    RiskProcessSerializer,
)


class TenantMixin:
    def _tenant(self):
        if not hasattr(self, "_resolved_tenant"):
            self._resolved_tenant = resolve_tenant_for_request(self.request)
        return self._resolved_tenant


def _require_scoped(user, tenant, code, unit):
    if unit:
        return require_tenant_permission(user, tenant, code, unit)
    return require_whole_tenant_permission(user, tenant, code)


class BusinessProcessViewSet(TenantMixin, viewsets.ModelViewSet):
    serializer_class = BusinessProcessSerializer

    def _permission_code(self):
        return "process.view" if self.action in {"list", "retrieve"} else "process.manage"

    def get_queryset(self):
        tenant = self._tenant()
        code = self._permission_code()
        require_tenant_permission(self.request.user, tenant, code)
        allowed = accessible_organization_unit_ids(self.request.user, tenant, code)
        whole = has_whole_tenant_permission(self.request.user, tenant, code)
        qs = (
            BusinessProcess.objects.filter(tenant=tenant, deleted_at__isnull=True)
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
        _require_scoped(self.request.user, tenant, "process.manage", unit)
        obj = serializer.save(tenant=tenant)
        record_audit_event(
            self.request.user, tenant, "process.create", "business_process", obj.id,
            new_data={"code": obj.code, "name": obj.name},
            object_repr=str(obj), request=self.request,
        )

    def perform_update(self, serializer):
        tenant = self._tenant()
        instance = serializer.instance
        _require_scoped(
            self.request.user, tenant, "process.manage", instance.organization_unit
        )
        new_unit = serializer.validated_data.get(
            "organization_unit", instance.organization_unit
        )
        _require_scoped(self.request.user, tenant, "process.manage", new_unit)
        old = {
            "code": instance.code,
            "name": instance.name,
            "status": instance.status,
            "organization_unit": str(instance.organization_unit_id or ""),
        }
        obj = serializer.save()
        record_audit_event(
            self.request.user, tenant, "process.update", "business_process", obj.id,
            old_data=old,
            new_data={
                "code": obj.code,
                "name": obj.name,
                "status": obj.status,
                "organization_unit": str(obj.organization_unit_id or ""),
            },
            object_repr=str(obj), request=self.request,
        )

    def perform_destroy(self, instance):
        tenant = self._tenant()
        _require_scoped(
            self.request.user, tenant, "process.manage", instance.organization_unit
        )
        instance.deleted_at = timezone.now()
        instance.status = BusinessProcess.Status.RETIRED
        instance.save(update_fields=["deleted_at", "status", "updated_at"])
        record_audit_event(
            self.request.user, tenant, "process.archive", "business_process",
            instance.id, object_repr=str(instance), request=self.request,
        )


class ProcessLinkMixin(TenantMixin):
    process_field = "process"

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["tenant"] = self._tenant()
        return context

    def _process_scope(self, obj):
        return obj.process.organization_unit

    def _require_process_manage(self, process):
        _require_scoped(
            self.request.user, self._tenant(), "process.manage", process.organization_unit
        )

    def _base_queryset(self, model):
        tenant = self._tenant()
        require_tenant_permission(self.request.user, tenant, "process.view")
        allowed = accessible_organization_unit_ids(
            self.request.user, tenant, "process.view"
        )
        whole = has_whole_tenant_permission(self.request.user, tenant, "process.view")
        qs = model.objects.filter(tenant=tenant, deleted_at__isnull=True)
        return qs if whole else qs.filter(process__organization_unit_id__in=allowed)

    def perform_destroy(self, instance):
        tenant = self._tenant()
        self._require_process_manage(instance.process)
        self._require_other_side(instance)
        instance.deleted_at = timezone.now()
        instance.save(update_fields=["deleted_at", "updated_at"])
        record_audit_event(
            self.request.user, tenant, f"process.{self.audit_kind}.delete",
            self.audit_kind, instance.id, request=self.request,
        )


class RiskProcessViewSet(ProcessLinkMixin, viewsets.ModelViewSet):
    serializer_class = RiskProcessSerializer
    audit_kind = "risk_process"

    def get_queryset(self):
        qs = self._base_queryset(RiskProcess).select_related(
            "risk", "process", "process__organization_unit"
        ).order_by("-created_at")
        if self.request.query_params.get("risk"):
            qs = qs.filter(risk_id=self.request.query_params["risk"])
        if self.request.query_params.get("process"):
            qs = qs.filter(process_id=self.request.query_params["process"])
        return qs

    def _require_other_side(self, obj):
        _require_scoped(
            self.request.user, self._tenant(), "risk.view", obj.risk.organization_unit
        )

    def perform_create(self, serializer):
        tenant = self._tenant()
        process = serializer.validated_data["process"]
        risk = serializer.validated_data["risk"]
        self._require_process_manage(process)
        _require_scoped(self.request.user, tenant, "risk.view", risk.organization_unit)
        obj = serializer.save(tenant=tenant)
        record_audit_event(
            self.request.user, tenant, "process.risk_link.create", "risk_process",
            obj.id, metadata={"risk_id": str(obj.risk_id), "process_id": str(obj.process_id)},
            request=self.request,
        )

    def perform_update(self, serializer):
        self._require_process_manage(serializer.instance.process)
        self._require_other_side(serializer.instance)
        serializer.save()


class ControlImplementationProcessViewSet(ProcessLinkMixin, viewsets.ModelViewSet):
    serializer_class = ControlImplementationProcessSerializer
    audit_kind = "control_process"

    def get_queryset(self):
        qs = self._base_queryset(ControlImplementationProcess).select_related(
            "control_implementation__control",
            "control_implementation__organization_unit",
            "process",
            "process__organization_unit",
        ).order_by("-created_at")
        if self.request.query_params.get("control_implementation"):
            qs = qs.filter(
                control_implementation_id=self.request.query_params["control_implementation"]
            )
        if self.request.query_params.get("process"):
            qs = qs.filter(process_id=self.request.query_params["process"])
        return qs

    def _require_other_side(self, obj):
        _require_scoped(
            self.request.user,
            self._tenant(),
            "control.implementation.view",
            obj.control_implementation.organization_unit,
        )

    def perform_create(self, serializer):
        tenant = self._tenant()
        process = serializer.validated_data["process"]
        control = serializer.validated_data["control_implementation"]
        self._require_process_manage(process)
        _require_scoped(
            self.request.user,
            tenant,
            "control.implementation.view",
            control.organization_unit,
        )
        obj = serializer.save(tenant=tenant)
        record_audit_event(
            self.request.user, tenant, "process.control_link.create",
            "control_process", obj.id,
            metadata={
                "control_implementation_id": str(obj.control_implementation_id),
                "process_id": str(obj.process_id),
            },
            request=self.request,
        )

    def perform_update(self, serializer):
        self._require_process_manage(serializer.instance.process)
        self._require_other_side(serializer.instance)
        serializer.save()


class AuditProcessViewSet(ProcessLinkMixin, viewsets.ModelViewSet):
    serializer_class = AuditProcessSerializer
    audit_kind = "audit_process"

    def get_queryset(self):
        qs = self._base_queryset(AuditProcess).select_related(
            "audit_engagement__organization_unit",
            "process",
            "process__organization_unit",
        ).order_by("-created_at")
        if self.request.query_params.get("audit_engagement"):
            qs = qs.filter(
                audit_engagement_id=self.request.query_params["audit_engagement"]
            )
        if self.request.query_params.get("process"):
            qs = qs.filter(process_id=self.request.query_params["process"])
        return qs

    def _require_other_side(self, obj):
        _require_scoped(
            self.request.user,
            self._tenant(),
            "internal_audit.view",
            obj.audit_engagement.organization_unit,
        )

    def perform_create(self, serializer):
        tenant = self._tenant()
        process = serializer.validated_data["process"]
        audit = serializer.validated_data["audit_engagement"]
        self._require_process_manage(process)
        _require_scoped(
            self.request.user, tenant, "internal_audit.view", audit.organization_unit
        )
        obj = serializer.save(tenant=tenant)
        record_audit_event(
            self.request.user, tenant, "process.audit_link.create",
            "audit_process", obj.id,
            metadata={
                "audit_engagement_id": str(obj.audit_engagement_id),
                "process_id": str(obj.process_id),
            },
            request=self.request,
        )

    def perform_update(self, serializer):
        self._require_process_manage(serializer.instance.process)
        self._require_other_side(serializer.instance)
        serializer.save()
