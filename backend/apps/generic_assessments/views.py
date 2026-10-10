"""Scoped APIs for generic assessments. Existing /assessments/ endpoints untouched."""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.db import transaction
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from django.utils import timezone

from apps.audit.services import record_audit_event
from apps.identity.services import (
    accessible_organization_unit_ids, has_whole_tenant_permission,
    require_tenant_permission, require_whole_tenant_permission,
)
from apps.tenancy.services import resolve_tenant_for_request
from .models import (
    ApplicabilityDecision, AssessmentTemplate, AssessmentTemplateVersion,
    ComplianceAssessmentProfile, CriterionRequirementMapping,
    GenericAssessmentItem, GenericAssessmentRun, TemplateCriterion,
)
from .serializers import (
    AnswerInputSerializer, ApplicabilitySerializer, ComplianceProfileSerializer,
    CriterionRequirementSerializer, GenericAssessmentItemSerializer,
    GenericAssessmentRunSerializer, TemplateCriterionSerializer,
    TemplateSerializer, TemplateVersionSerializer,
)
from .services import complete_run, create_run, publish_template, save_response, score_summary


def safe_model_call(fn):
    try:
        return fn()
    except DjangoValidationError as exc:
        raise ValidationError(getattr(exc, "message_dict", {"non_field_errors": exc.messages})) from exc


class TenantMixin:
    def _tenant(self):
        if not hasattr(self, "_tenant_cache"):
            self._tenant_cache = resolve_tenant_for_request(self.request)
        return self._tenant_cache

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["tenant"] = self._tenant()
        return ctx

    def scope_authorize(self, code, unit):
        if unit is None:
            require_whole_tenant_permission(self.request.user, self._tenant(), code)
        else:
            require_tenant_permission(self.request.user, self._tenant(), code, unit)

    def scope_filter(self, query, code, key):
        tenant = self._tenant()
        require_tenant_permission(self.request.user, tenant, code)
        if not has_whole_tenant_permission(self.request.user, tenant, code):
            ids = accessible_organization_unit_ids(self.request.user, tenant, code)
            query = query.filter(**{key + "__in": ids})
        return query

    def audit(self, action_code, obj, extra=None):
        record_audit_event(
            self.request.user, self._tenant(), action_code,
            obj.__class__.__name__.lower(), obj.pk,
            new_data=extra or {}, request=self.request, object_repr=str(obj),
        )


class TemplateViewSet(TenantMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                      mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = TemplateSerializer

    def get_queryset(self):
        code = "assessment.view" if self.action in {"list", "retrieve"} else "assessment.manage"
        return self.scope_filter(
            AssessmentTemplate.objects.filter(tenant=self._tenant(), deleted_at__isnull=True),
            code, "organization_unit_id",
        ).order_by("code")

    @transaction.atomic
    def perform_create(self, serializer):
        self.scope_authorize("assessment.manage", serializer.validated_data.get("organization_unit"))
        obj = safe_model_call(lambda: serializer.save(tenant=self._tenant()))
        self.audit("assessment_template.create", obj)

    @transaction.atomic
    def perform_update(self, serializer):
        self.scope_authorize("assessment.manage", serializer.instance.organization_unit)
        self.scope_authorize("assessment.manage", serializer.validated_data.get("organization_unit", serializer.instance.organization_unit))
        if serializer.instance.versions.filter(status="published").exists():
            raise ValidationError("Published template definition cannot be edited; use a new version.")
        obj = safe_model_call(serializer.save)
        self.audit("assessment_template.update", obj)


class TemplateVersionViewSet(TenantMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                             mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = TemplateVersionSerializer

    def get_queryset(self):
        code = "assessment.review" if self.action == "publish" else "assessment.view" if self.action in {"list", "retrieve"} else "assessment.manage"
        return self.scope_filter(
            AssessmentTemplateVersion.objects.filter(template__tenant=self._tenant(), deleted_at__isnull=True),
            code, "template__organization_unit_id",
        ).order_by("template__code", "-created_at")

    @transaction.atomic
    def perform_create(self, serializer):
        template = serializer.validated_data["template"]
        if template.tenant_id != self._tenant().id or template.deleted_at:
            raise ValidationError({"template": "Template outside tenant."})
        self.scope_authorize("assessment.manage", template.organization_unit)
        obj = safe_model_call(serializer.save)
        self.audit("assessment_template_version.create", obj)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def publish(self, request, pk=None):
        version = self.get_object()
        self.scope_authorize("assessment.review", version.template.organization_unit)
        version = safe_model_call(lambda: publish_template(version=version, user=request.user))
        self.audit("assessment_template_version.publish", version)
        return Response(self.get_serializer(version).data)


class TemplateCriterionViewSet(TenantMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                               mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = TemplateCriterionSerializer

    def get_queryset(self):
        code = "assessment.view" if self.action in {"list", "retrieve"} else "assessment.manage"
        return self.scope_filter(
            TemplateCriterion.objects.filter(version__template__tenant=self._tenant(), deleted_at__isnull=True),
            code, "version__template__organization_unit_id",
        ).order_by("sort_order", "code")

    @transaction.atomic
    def perform_create(self, serializer):
        version = serializer.validated_data["version"]
        if version.template.tenant_id != self._tenant().id or version.deleted_at:
            raise ValidationError({"version": "Template version outside tenant."})
        self.scope_authorize("assessment.manage", version.template.organization_unit)
        obj = safe_model_call(serializer.save)
        self.audit("assessment_criterion.create", obj)

    @transaction.atomic
    def perform_update(self, serializer):
        obj = serializer.instance
        self.scope_authorize("assessment.manage", obj.version.template.organization_unit)
        if "version" in serializer.validated_data and serializer.validated_data["version"].pk != obj.version_id:
            raise ValidationError({"version": "Cannot move a criterion between versions."})
        obj = safe_model_call(serializer.save)
        self.audit("assessment_criterion.update", obj)


class ProfileViewSet(TenantMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                     mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = ComplianceProfileSerializer

    def get_queryset(self):
        code = "assessment.view" if self.action in {"list", "retrieve"} else "assessment.manage"
        return self.scope_filter(
            ComplianceAssessmentProfile.objects.filter(tenant=self._tenant(), deleted_at__isnull=True),
            code, "template_version__template__organization_unit_id",
        ).order_by("created_at")

    @transaction.atomic
    def perform_create(self, serializer):
        version = serializer.validated_data["template_version"]
        self.scope_authorize("assessment.manage", version.template.organization_unit)
        obj = safe_model_call(lambda: serializer.save(tenant=self._tenant()))
        self.audit("assessment_profile.create", obj)


class CriterionMappingViewSet(TenantMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                              mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = CriterionRequirementSerializer

    def get_queryset(self):
        code = "assessment.view" if self.action in {"list", "retrieve"} else "assessment.manage"
        return self.scope_filter(
            CriterionRequirementMapping.objects.filter(profile__tenant=self._tenant(), deleted_at__isnull=True),
            code, "profile__template_version__template__organization_unit_id",
        ).order_by("created_at")

    @transaction.atomic
    def perform_create(self, serializer):
        profile = serializer.validated_data["profile"]
        if profile.tenant_id != self._tenant().id:
            raise ValidationError({"profile": "Profile outside tenant."})
        self.scope_authorize("assessment.manage", profile.template_version.template.organization_unit)
        if profile.assessment_runs.exists():
            raise ValidationError("Cannot change criterion crosswalk after a profile has executed.")
        obj = safe_model_call(serializer.save)
        self.audit("assessment_criterion_mapping.create", obj)


class GenericAssessmentRunViewSet(TenantMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                                  mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = GenericAssessmentRunSerializer

    def get_queryset(self):
        code = "assessment.review" if self.action == "complete" else "assessment.view" if self.action in {"list", "retrieve", "summary"} else "assessment.manage"
        return self.scope_filter(
            GenericAssessmentRun.objects.filter(tenant=self._tenant(), deleted_at__isnull=True),
            code, "organization_unit_id",
        ).order_by("-created_at")

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attrs = serializer.validated_data
        unit = attrs.get("organization_unit")
        self.scope_authorize("assessment.manage", unit)
        run = safe_model_call(lambda: create_run(
            tenant=self._tenant(), template_version=attrs["template_version"], owner=attrs["owner"],
            organization_unit=unit, title=attrs["title"], profile=attrs.get("profile"),
        ))
        self.audit("generic_assessment.create", run, {"template_version": str(run.template_version_id)})
        return Response(self.get_serializer(run).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def summary(self, request, pk=None):
        run = self.get_object()
        return Response(score_summary(run))

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def complete(self, request, pk=None):
        run = self.get_object()
        self.scope_authorize("assessment.review", run.organization_unit)
        run, summary = safe_model_call(lambda: complete_run(run=run))
        self.audit("generic_assessment.complete", run, summary)
        return Response({"assessment": self.get_serializer(run).data, "summary": summary})


class GenericAssessmentItemViewSet(TenantMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                                   viewsets.GenericViewSet):
    serializer_class = GenericAssessmentItemSerializer

    def get_queryset(self):
        code = "assessment.perform" if self.action == "answer" else "assessment.view"
        qs = self.scope_filter(
            GenericAssessmentItem.objects.filter(run__tenant=self._tenant(), deleted_at__isnull=True),
            code, "run__organization_unit_id",
        )
        if self.request.query_params.get("run"):
            qs = qs.filter(run_id=self.request.query_params["run"])
        return qs.order_by("criterion_code_snapshot")

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def answer(self, request, pk=None):
        item = self.get_object()
        self.scope_authorize("assessment.perform", item.run.organization_unit)
        incoming = AnswerInputSerializer(data=request.data)
        incoming.is_valid(raise_exception=True)
        item = safe_model_call(lambda: save_response(
            item=item, user=request.user, value=incoming.validated_data["value"],
        ))
        self.audit("generic_assessment.answer", item, {"criterion": item.criterion_code_snapshot})
        return Response(self.get_serializer(item).data)


class ApplicabilityViewSet(TenantMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                           mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = ApplicabilitySerializer

    @staticmethod
    def item_scope(decision):
        if decision.generic_item_id:
            return decision.generic_item.run.organization_unit
        return decision.legacy_item.assessment.organization_unit

    def get_queryset(self):
        # Different FK paths need separate scope filtering, never OR broad tenant membership.
        tenant = self._tenant()
        code = "assessment.review" if self.action == "review" else "assessment.view" if self.action in {"list", "retrieve"} else "assessment.perform"
        require_tenant_permission(self.request.user, tenant, code)
        qs = ApplicabilityDecision.objects.filter(tenant=tenant, deleted_at__isnull=True)
        if not has_whole_tenant_permission(self.request.user, tenant, code):
            ids = accessible_organization_unit_ids(self.request.user, tenant, code)
            qs = qs.filter(
                (Q(generic_item__run__organization_unit_id__in=ids) |
                 Q(legacy_item__assessment__organization_unit_id__in=ids))
            )
        return qs.order_by("-created_at")

    @transaction.atomic
    def perform_create(self, serializer):
        item = serializer.validated_data.get("generic_item")
        legacy = serializer.validated_data.get("legacy_item")
        tenant = self._tenant()
        if item and item.run.tenant_id != tenant.id or legacy and legacy.assessment.tenant_id != tenant.id:
            raise ValidationError("Applicability item outside tenant.")
        unit = item.run.organization_unit if item else legacy.assessment.organization_unit
        self.scope_authorize("assessment.perform", unit)
        obj = safe_model_call(lambda: serializer.save(tenant=tenant, created_by=self.request.user))
        self.audit("applicability.propose", obj)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def review(self, request, pk=None):
        obj = self.get_object()
        self.scope_authorize("assessment.review", self.item_scope(obj))
        obj = ApplicabilityDecision.objects.select_for_update().get(pk=obj.id)
        if obj.reviewed_at:
            raise ValidationError("Applicability decision already reviewed.")
        if obj.created_by_id == request.user.id:
            raise PermissionDenied("A proposer cannot review their own applicability.")
        obj.reviewed_by = request.user
        obj.reviewed_at = timezone.now()
        obj = safe_model_call(lambda: (obj.save(update_fields=["reviewed_by", "reviewed_at", "updated_at"]), obj)[1])
        self.audit("applicability.review", obj)
        return Response(self.get_serializer(obj).data)
