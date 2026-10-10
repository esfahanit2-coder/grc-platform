from rest_framework import serializers
from .models import (
    ApplicabilityDecision, AssessmentTemplate, AssessmentTemplateVersion,
    ComplianceAssessmentProfile, CriterionRequirementMapping,
    GenericAssessmentItem, GenericAssessmentRun, TemplateCriterion,
)


class TemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentTemplate
        fields = ["id", "organization_unit", "code", "title", "description", "owner", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class TemplateVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentTemplateVersion
        fields = ["id", "template", "version_code", "status", "published_at", "published_by", "notes", "created_at"]
        read_only_fields = ["id", "status", "published_at", "published_by", "created_at"]


class TemplateCriterionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemplateCriterion
        fields = ["id", "version", "code", "title", "description", "response_type", "choices", "required",
                  "weight", "applicability_mode", "sort_order", "created_at"]
        read_only_fields = ["id", "created_at"]


class ComplianceProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceAssessmentProfile
        fields = ["id", "template_version", "framework_version", "title", "created_at"]
        read_only_fields = ["id", "created_at"]


class CriterionRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = CriterionRequirementMapping
        fields = ["id", "profile", "criterion", "requirement", "created_at"]
        read_only_fields = ["id", "created_at"]


class GenericAssessmentRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = GenericAssessmentRun
        fields = ["id", "organization_unit", "template_version", "profile", "title", "owner",
                  "status", "completed_at", "created_at", "updated_at"]
        read_only_fields = ["id", "status", "completed_at", "created_at", "updated_at"]


class GenericAssessmentItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = GenericAssessmentItem
        fields = ["id", "run", "criterion", "criterion_code_snapshot", "criterion_title_snapshot",
                  "response_type_snapshot", "options_snapshot", "weight_snapshot",
                  "required_snapshot", "applicability_mode_snapshot", "answer", "score_percent", "assessed_by", "assessed_at"]
        read_only_fields = fields


class AnswerInputSerializer(serializers.Serializer):
    value = serializers.JSONField()


class ApplicabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicabilityDecision
        fields = ["id", "generic_item", "legacy_item", "decision", "rationale",
                  "created_by", "reviewed_by", "reviewed_at", "created_at"]
        read_only_fields = ["id", "created_by", "reviewed_by", "reviewed_at", "created_at"]

    def validate(self, attrs):
        if bool(attrs.get("generic_item")) == bool(attrs.get("legacy_item")):
            raise serializers.ValidationError("Select exactly one generic or legacy item.")
        if not str(attrs.get("rationale") or "").strip():
            raise serializers.ValidationError({"rationale": "A justification is required."})
        return attrs
