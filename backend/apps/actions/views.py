from django.utils import timezone
from rest_framework import viewsets
from apps.audit.services import record_audit_event
from apps.identity.services import accessible_organization_unit_ids,has_whole_tenant_permission,require_tenant_permission,require_whole_tenant_permission
from apps.tenancy.services import resolve_tenant_for_request
from .models import Action
from .serializers import ActionSerializer
class ActionViewSet(viewsets.ModelViewSet):
    serializer_class=ActionSerializer
    def _tenant(self):
        if not hasattr(self,"_resolved_tenant"): self._resolved_tenant=resolve_tenant_for_request(self.request)
        return self._resolved_tenant
    def get_serializer_context(self): ctx=super().get_serializer_context();ctx["tenant"]=self._tenant();return ctx
    def _perm(self): return "action.view" if self.action in {"list","retrieve"} else "action.manage"
    def get_queryset(self):
        tenant=self._tenant();code=self._perm();require_tenant_permission(self.request.user,tenant,code);allowed=accessible_organization_unit_ids(self.request.user,tenant,code);whole=has_whole_tenant_permission(self.request.user,tenant,code)
        qs=Action.objects.filter(tenant=tenant,deleted_at__isnull=True)
        if whole: return qs.select_related("organization_unit","owner","reviewer").order_by("due_date","created_at")
        return qs.filter(organization_unit_id__in=allowed).select_related("organization_unit","owner","reviewer").order_by("due_date","created_at")
    def perform_create(self,serializer):
        tenant=self._tenant();unit=serializer.validated_data.get("organization_unit");require_tenant_permission(self.request.user,tenant,"action.manage",unit) if unit else require_whole_tenant_permission(self.request.user,tenant,"action.manage");obj=serializer.save(tenant=tenant);record_audit_event(self.request.user,tenant,"action.create","action",obj.id,request=self.request)
    def perform_update(self, serializer):
        tenant = self._tenant()
        instance = serializer.instance
        if instance.organization_unit:
            require_tenant_permission(self.request.user, tenant, "action.manage", instance.organization_unit)
        else:
            require_whole_tenant_permission(self.request.user, tenant, "action.manage")
        new_unit = serializer.validated_data.get("organization_unit", instance.organization_unit)
        if new_unit:
            require_tenant_permission(self.request.user, tenant, "action.manage", new_unit)
        elif instance.organization_unit_id:
            require_whole_tenant_permission(self.request.user, tenant, "action.manage")
        obj = serializer.save()
        if obj.status == Action.Status.DONE and obj.completed_at is None:
            obj.completed_at = timezone.now()
            obj.progress = 100
            obj.save(update_fields=["completed_at", "progress", "updated_at"])
        record_audit_event(self.request.user, tenant, "action.update", "action", obj.id, request=self.request)

    def perform_destroy(self, instance):
        tenant=self._tenant()
        if instance.organization_unit:
            require_tenant_permission(self.request.user,tenant,"action.manage",instance.organization_unit)
        else:
            require_whole_tenant_permission(self.request.user,tenant,"action.manage")
        instance.deleted_at=timezone.now(); instance.status=Action.Status.CANCELLED; instance.save(update_fields=["deleted_at","status","updated_at"])
