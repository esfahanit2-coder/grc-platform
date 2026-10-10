"""Shared tenant/org-scope enforcement for additive domain registers (#104).

Views still require domain-specific permission sets; this base never treats a
tenant membership as a grant to an unrelated module.
"""
from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError

from apps.audit.services import record_audit_event
from apps.identity.services import (
    accessible_organization_unit_ids, has_whole_tenant_permission,
    require_tenant_permission, require_whole_tenant_permission,
)
from apps.tenancy.services import resolve_tenant_for_request


class ScopedRegisterMixin:
    model = None
    serializer_class = None
    read_permissions = ()
    write_permissions = ()
    # (permission code, FK chain ending at OrganizationUnit ID)
    scope_lookups = ()

    def _tenant(self):
        if not hasattr(self, "_resolved_tenant"):
            self._resolved_tenant = resolve_tenant_for_request(self.request)
        return self._resolved_tenant

    def get_serializer_context(self):
        result = super().get_serializer_context()
        result["tenant"] = self._tenant()
        return result

    def _permissions(self):
        return self.read_permissions if self.action in {"list", "retrieve"} else self.write_permissions

    def get_queryset(self):
        tenant = self._tenant()
        qs = self.model.objects.filter(tenant=tenant, deleted_at__isnull=True)
        for code, scope_lookup in self._permissions():
            require_tenant_permission(self.request.user, tenant, code)
            if not has_whole_tenant_permission(self.request.user, tenant, code):
                ids = accessible_organization_unit_ids(self.request.user, tenant, code)
                qs = qs.filter(**{scope_lookup + "__in": ids})
        return qs.order_by("created_at")

    def _require_scope(self, permission, unit):
        tenant = self._tenant()
        if unit is None:
            require_whole_tenant_permission(self.request.user, tenant, permission)
        else:
            require_tenant_permission(self.request.user, tenant, permission, unit)

    def _check_endpoints(self, attrs, *, write=True):
        for (permission, _), endpoint_name in zip(self.write_permissions if write else self.read_permissions, self.endpoints):
            endpoint = attrs[endpoint_name]
            self._require_scope(permission, endpoint.organization_unit)

    def _audit(self, suffix, instance, *, old=None, new=None):
        record_audit_event(
            self.request.user, self._tenant(), self.model.__name__.lower() + "." + suffix,
            self.model.__name__.lower(), instance.pk,
            old_data=old, new_data=new,
            object_repr=str(instance), request=self.request,
        )


class ScopedEntityViewSet(ScopedRegisterMixin, viewsets.ModelViewSet):
    scope_field = "organization_unit"
    related_link_names = ()

    @transaction.atomic
    def perform_create(self, serializer):
        unit = serializer.validated_data.get(self.scope_field)
        for permission, _ in self.write_permissions:
            self._require_scope(permission, unit)
        instance = serializer.save(tenant=self._tenant())
        self._audit("create", instance, new={"code": instance.code, "scope": str(instance.organization_unit_id or "")})

    @transaction.atomic
    def perform_update(self, serializer):
        instance = serializer.instance
        before = {"code": instance.code, "scope": str(instance.organization_unit_id or ""), "status": instance.status}
        for permission, _ in self.write_permissions:
            self._require_scope(permission, instance.organization_unit)
            new_unit = serializer.validated_data.get(self.scope_field, instance.organization_unit)
            self._require_scope(permission, new_unit)
        changed = serializer.save()
        self._audit("update", changed, old=before, new={"code": changed.code, "scope": str(changed.organization_unit_id or ""), "status": changed.status})

    @transaction.atomic
    def perform_destroy(self, instance):
        for permission, _ in self.write_permissions:
            self._require_scope(permission, instance.organization_unit)
        if instance.children.filter(deleted_at__isnull=True).exists():
            raise ValidationError("Cannot archive a parent with active children.")
        if any(getattr(instance, name).filter(deleted_at__isnull=True).exists() for name in self.related_link_names):
            raise ValidationError("Cannot archive a register record with active relationships.")
        before = {"status": instance.status}
        instance.deleted_at = timezone.now()
        instance.status = "archived"
        instance.save(update_fields=["deleted_at", "status", "updated_at"])
        self._audit("archive", instance, old=before, new={"status": "archived"})


class ScopedLinkViewSet(ScopedRegisterMixin, viewsets.ModelViewSet):
    endpoints = ()  # matches permission tuples for this viewset

    @transaction.atomic
    def perform_create(self, serializer):
        attrs = serializer.validated_data
        self._check_endpoints(attrs)
        instance = serializer.save(tenant=self._tenant())
        self._audit("create", instance, new={key: str(getattr(instance, key + "_id")) for key in self.endpoints})

    @transaction.atomic
    def perform_update(self, serializer):
        instance = serializer.instance
        attrs = {name: getattr(instance, name) for name in self.endpoints}
        self._check_endpoints(attrs)
        changed = serializer.save()
        self._audit("update", changed)

    @transaction.atomic
    def perform_destroy(self, instance):
        attrs = {name: getattr(instance, name) for name in self.endpoints}
        self._check_endpoints(attrs)
        instance.deleted_at = timezone.now()
        instance.save(update_fields=["deleted_at", "updated_at"])
        self._audit("archive", instance)
