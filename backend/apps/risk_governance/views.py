from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.audit.services import record_audit_event
from apps.identity.services import (
    accessible_organization_unit_ids, has_whole_tenant_permission,
    require_tenant_permission, require_whole_tenant_permission,
)
from apps.tenancy.services import resolve_tenant_for_request
from apps.risks.models import Risk
from .models import RiskAcceptance, RiskAppetiteStatement, RiskTolerance
from .serializers import (
    RiskAcceptanceRequestSerializer, RiskAcceptanceSerializer,
    RiskAppetiteSerializer, RiskToleranceSerializer,
)


class TenantScopeMixin:
    def _tenant(self):
        if not hasattr(self, "_resolved_tenant"):
            self._resolved_tenant = resolve_tenant_for_request(self.request)
        return self._resolved_tenant

    def get_serializer_context(self):
        result = super().get_serializer_context()
        result["tenant"] = self._tenant()
        return result

    def _require_scope(self, code, organization_unit):
        if organization_unit is None:
            require_whole_tenant_permission(self.request.user, self._tenant(), code)
        else:
            require_tenant_permission(self.request.user, self._tenant(), code, organization_unit)

    def _filter_scope(self, queryset, code, lookup):
        tenant = self._tenant()
        require_tenant_permission(self.request.user, tenant, code)
        if not has_whole_tenant_permission(self.request.user, tenant, code):
            allowed = accessible_organization_unit_ids(self.request.user, tenant, code)
            queryset = queryset.filter(**{lookup + "__in": allowed})
        return queryset

    def _audit(self, event, kind, obj, *, data=None):
        record_audit_event(
            self.request.user, self._tenant(), event, kind, obj.id,
            new_data=data or {}, object_repr=str(obj), request=self.request,
        )


class RiskAppetiteViewSet(TenantScopeMixin, viewsets.ModelViewSet):
    serializer_class = RiskAppetiteSerializer

    def get_queryset(self):
        code = ("risk.appetite.view" if self.action in {"list", "retrieve"} else
                "risk.appetite.approve" if self.action == "approve" else "risk.appetite.manage")
        qs = RiskAppetiteStatement.objects.filter(tenant=self._tenant(), deleted_at__isnull=True)
        return self._filter_scope(qs, code, "organization_unit_id").order_by("code", "-version")

    @transaction.atomic
    def perform_create(self, serializer):
        unit = serializer.validated_data.get("organization_unit")
        self._require_scope("risk.appetite.manage", unit)
        obj = serializer.save(tenant=self._tenant())
        self._audit("risk_appetite.create", "risk_appetite", obj, data={"code": obj.code, "version": obj.version})

    @transaction.atomic
    def perform_update(self, serializer):
        obj = serializer.instance
        self._require_scope("risk.appetite.manage", obj.organization_unit)
        self._require_scope("risk.appetite.manage", serializer.validated_data.get("organization_unit", obj.organization_unit))
        if obj.status != RiskAppetiteStatement.Status.DRAFT:
            raise ValidationError("Approved policy versions are immutable.")
        obj = serializer.save()
        self._audit("risk_appetite.update", "risk_appetite", obj)

    @transaction.atomic
    def perform_destroy(self, instance):
        self._require_scope("risk.appetite.manage", instance.organization_unit)
        if instance.status != RiskAppetiteStatement.Status.DRAFT or instance.tolerances.filter(deleted_at__isnull=True).exists():
            raise ValidationError("Only unused draft appetite statements may be archived.")
        instance.deleted_at = timezone.now()
        instance.save(update_fields=["deleted_at", "updated_at"])
        self._audit("risk_appetite.archive", "risk_appetite", instance)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def approve(self, request, pk=None):
        obj = self.get_object()
        self._require_scope("risk.appetite.approve", obj.organization_unit)
        obj = RiskAppetiteStatement.objects.select_for_update().get(pk=obj.id)
        if obj.status != RiskAppetiteStatement.Status.DRAFT:
            raise ValidationError("Only a draft may be approved.")
        if obj.owner_id == request.user.id:
            raise PermissionDenied("Appetite owner cannot approve their own statement.")
        if not obj.tolerances.filter(deleted_at__isnull=True).exists():
            raise ValidationError("At least one tolerance is required.")
        siblings = RiskAppetiteStatement.objects.select_for_update().filter(
            tenant=obj.tenant, code=obj.code, organization_unit=obj.organization_unit,
            status=RiskAppetiteStatement.Status.APPROVED, deleted_at__isnull=True,
        ).exclude(id=obj.id)
        for sibling in siblings:
            if (sibling.effective_until is None or sibling.effective_until >= obj.effective_from) and (
                obj.effective_until is None or obj.effective_until >= sibling.effective_from
            ):
                raise ValidationError("An approved effective version overlaps this policy period.")
        obj.status = RiskAppetiteStatement.Status.APPROVED
        obj.approved_by = request.user
        obj.approved_at = timezone.now()
        obj.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
        self._audit("risk_appetite.approve", "risk_appetite", obj)
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def retire(self, request, pk=None):
        obj = self.get_object()
        self._require_scope("risk.appetite.manage", obj.organization_unit)
        if obj.status != RiskAppetiteStatement.Status.APPROVED:
            raise ValidationError("Only approved policy versions can be retired.")
        if obj.acceptances.filter(status=RiskAcceptance.Status.PENDING, deleted_at__isnull=True).exists():
            raise ValidationError("Policy has pending acceptance requests.")
        obj.status = RiskAppetiteStatement.Status.RETIRED
        obj.save(update_fields=["status", "updated_at"])
        self._audit("risk_appetite.retire", "risk_appetite", obj)
        return Response(self.get_serializer(obj).data)


class RiskToleranceViewSet(TenantScopeMixin, viewsets.ModelViewSet):
    serializer_class = RiskToleranceSerializer

    def get_queryset(self):
        code = "risk.appetite.view" if self.action in {"list", "retrieve"} else "risk.appetite.manage"
        qs = RiskTolerance.objects.filter(
            statement__tenant=self._tenant(), deleted_at__isnull=True, statement__deleted_at__isnull=True,
        ).select_related("statement__organization_unit")
        return self._filter_scope(qs, code, "statement__organization_unit_id").order_by("created_at")

    @transaction.atomic
    def perform_create(self, serializer):
        statement = serializer.validated_data["statement"]
        self._require_scope("risk.appetite.manage", statement.organization_unit)
        obj = serializer.save()
        self._audit("risk_tolerance.create", "risk_tolerance", obj)

    @transaction.atomic
    def perform_update(self, serializer):
        obj = serializer.instance
        self._require_scope("risk.appetite.manage", obj.statement.organization_unit)
        if obj.statement.status != RiskAppetiteStatement.Status.DRAFT:
            raise ValidationError("Tolerances of approved policies are immutable.")
        obj = serializer.save()
        self._audit("risk_tolerance.update", "risk_tolerance", obj)

    @transaction.atomic
    def perform_destroy(self, instance):
        self._require_scope("risk.appetite.manage", instance.statement.organization_unit)
        if instance.statement.status != RiskAppetiteStatement.Status.DRAFT:
            raise ValidationError("Cannot remove approved tolerance.")
        instance.deleted_at = timezone.now()
        instance.save(update_fields=["deleted_at", "updated_at"])
        self._audit("risk_tolerance.archive", "risk_tolerance", instance)


class RiskAcceptanceViewSet(TenantScopeMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                            mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = RiskAcceptanceSerializer

    def get_serializer_class(self):
        return RiskAcceptanceRequestSerializer if self.action == "create" else RiskAcceptanceSerializer

    def get_queryset(self):
        qs = RiskAcceptance.objects.filter(tenant=self._tenant(), deleted_at__isnull=True).select_related(
            "risk__organization_unit", "evaluation", "appetite",
        )
        return self._filter_scope(qs, "risk.view", "risk__organization_unit_id").order_by("-created_at")

    @transaction.atomic
    def perform_create(self, serializer):
        attrs = serializer.validated_data
        risk = attrs["risk"]
        self._require_scope("risk.accept.request", risk.organization_unit)
        if attrs["appetite"].organization_unit_id is None:
            # A tenant-wide appetite can be consumed by a scoped risk manager,
            # but it cannot grant tenant-wide write authority.
            pass
        threshold = attrs.pop("_tolerance_max")
        evaluation = attrs["evaluation"]
        obj = serializer.save(
            tenant=self._tenant(), requested_by=self.request.user,
            evaluation_type_snapshot=evaluation.evaluation_type,
            score_snapshot=evaluation.score, likelihood_snapshot=evaluation.likelihood,
            impact_snapshot=evaluation.impact, evaluated_at_snapshot=evaluation.evaluated_at,
            tolerance_max_snapshot=threshold,
            exceeds_tolerance=evaluation.score > threshold,
        )
        self._audit("risk_acceptance.request", "risk_acceptance", obj, data={
            "risk": str(obj.risk_id), "evaluation": str(obj.evaluation_id),
            "score": str(obj.score_snapshot), "exceeds_tolerance": obj.exceeds_tolerance,
        })

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def approve(self, request, pk=None):
        original = self.get_object()
        # Serialize all acceptance decisions on the risk itself to prevent
        # two concurrent approvers from approving competing records.
        risk = Risk.objects.select_for_update().get(pk=original.risk_id, tenant=self._tenant())
        self._require_scope("risk.accept.approve", risk.organization_unit)
        obj = RiskAcceptance.objects.select_for_update().get(pk=original.pk, tenant=self._tenant())
        if obj.status != RiskAcceptance.Status.PENDING:
            raise ValidationError("This request has already been decided.")
        if obj.requested_by_id == request.user.id:
            raise PermissionDenied("Requester may not approve their own acceptance.")
        if obj.expires_on < timezone.localdate() or not obj.appetite.is_effective():
            raise ValidationError("Expired request or appetite policy.")
        active = list(RiskAcceptance.objects.select_for_update().filter(
            tenant=self._tenant(), risk=risk, status=RiskAcceptance.Status.APPROVED,
            expires_on__gte=timezone.localdate(), deleted_at__isnull=True,
        ).exclude(pk=obj.pk))
        if active:
            if len(active) != 1 or obj.supersedes_id != active[0].id:
                raise ValidationError("A current approved acceptance exists; explicitly supersede it.")
        elif obj.supersedes_id:
            raise ValidationError("Supersession target is no longer active.")
        decision_note = str(request.data.get("decision_note", "")).strip()
        if obj.exceeds_tolerance:
            self._require_scope("risk.accept.override", risk.organization_unit)
            if not obj.exception_justification.strip() or not decision_note:
                raise ValidationError("Exceeded tolerance requires justification and approver decision note.")
        obj.status = RiskAcceptance.Status.APPROVED
        obj.decided_by = request.user
        obj.decided_at = timezone.now()
        obj.decision_note = decision_note
        obj.save(update_fields=["status", "decided_by", "decided_at", "decision_note", "updated_at"])
        for previous in active:
            previous.status = RiskAcceptance.Status.SUPERSEDED
            previous.save(update_fields=["status", "updated_at"])
            self._audit("risk_acceptance.supersede", "risk_acceptance", previous, data={"successor": str(obj.id)})
        self._audit("risk_acceptance.approve", "risk_acceptance", obj)
        return Response(RiskAcceptanceSerializer(obj).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def reject(self, request, pk=None):
        original = self.get_object()
        self._require_scope("risk.accept.approve", original.risk.organization_unit)
        obj = RiskAcceptance.objects.select_for_update().get(pk=original.pk, tenant=self._tenant())
        if obj.status != RiskAcceptance.Status.PENDING:
            raise ValidationError("Request has already been decided.")
        if obj.requested_by_id == request.user.id:
            raise PermissionDenied("Requester may not decide own acceptance.")
        note = str(request.data.get("decision_note", "")).strip()
        if not note:
            raise ValidationError({"decision_note": "A rejection explanation is mandatory."})
        obj.status = RiskAcceptance.Status.REJECTED
        obj.decided_by = request.user
        obj.decided_at = timezone.now()
        obj.decision_note = note
        obj.save(update_fields=["status", "decided_by", "decided_at", "decision_note", "updated_at"])
        self._audit("risk_acceptance.reject", "risk_acceptance", obj)
        return Response(RiskAcceptanceSerializer(obj).data)
