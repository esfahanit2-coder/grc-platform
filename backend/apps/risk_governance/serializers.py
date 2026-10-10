from django.utils import timezone
from rest_framework import serializers
from apps.tenancy.models import TenantMembership
from .models import RiskAppetiteStatement, RiskTolerance, RiskAcceptance


class RiskAppetiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskAppetiteStatement
        fields = [
            "id", "organization_unit", "code", "version", "title", "description", "owner",
            "status", "effective_from", "effective_until", "approved_by", "approved_at",
            "metadata", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "status", "approved_by", "approved_at", "created_at", "updated_at"]

    def validate(self, attrs):
        tenant = self.context["tenant"]
        unit = attrs.get("organization_unit", getattr(self.instance, "organization_unit", None))
        owner = attrs.get("owner", getattr(self.instance, "owner", None))
        if unit and (unit.tenant_id != tenant.id or unit.deleted_at):
            raise serializers.ValidationError({"organization_unit": "Invalid tenant unit."})
        if owner and not TenantMembership.objects.filter(tenant=tenant, user=owner, is_active=True).exists():
            raise serializers.ValidationError({"owner": "Owner must be active tenant member."})
        if self.instance and self.instance.status != RiskAppetiteStatement.Status.DRAFT:
            raise serializers.ValidationError("An approved appetite version is immutable.")
        until = attrs.get("effective_until", getattr(self.instance, "effective_until", None))
        begin = attrs.get("effective_from", getattr(self.instance, "effective_from", None))
        if until and begin and until < begin:
            raise serializers.ValidationError({"effective_until": "Must not precede effective_from."})
        return attrs


class RiskToleranceSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskTolerance
        fields = ["id", "statement", "evaluation_type", "maximum_score", "description", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        tenant = self.context["tenant"]
        statement = attrs.get("statement", getattr(self.instance, "statement", None))
        if statement is None or statement.tenant_id != tenant.id or statement.deleted_at:
            raise serializers.ValidationError({"statement": "Statement is not available in this tenant."})
        if statement.status != RiskAppetiteStatement.Status.DRAFT:
            raise serializers.ValidationError({"statement": "Tolerance definition is locked after approval."})
        if self.instance and "statement" in attrs and statement.pk != self.instance.statement_id:
            raise serializers.ValidationError({"statement": "Cannot move a tolerance to another statement."})
        return attrs


class RiskAcceptanceRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskAcceptance
        fields = ["id", "risk", "evaluation", "appetite", "rationale", "review_on",
                  "expires_on", "supersedes", "exception_justification", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        tenant = self.context["tenant"]
        risk, evaluation, appetite = (attrs.get(key) for key in ("risk", "evaluation", "appetite"))
        if risk is None or risk.tenant_id != tenant.id or risk.deleted_at:
            raise serializers.ValidationError({"risk": "Risk unavailable in the selected tenant."})
        if evaluation is None or evaluation.risk_id != risk.id or evaluation.deleted_at:
            raise serializers.ValidationError({"evaluation": "Evaluation must belong to risk."})
        if evaluation.evaluation_type not in {"current", "residual"}:
            raise serializers.ValidationError({"evaluation": "Only current or residual evaluation can support acceptance."})
        if appetite is None or appetite.tenant_id != tenant.id or appetite.deleted_at or (
            appetite.organization_unit_id not in {None, risk.organization_unit_id}
        ):
            raise serializers.ValidationError({"appetite": "Policy must match risk tenant and unit."})
        if not appetite.is_effective():
            raise serializers.ValidationError({"appetite": "Approved and currently effective appetite is required."})
        tolerance = appetite.tolerances.filter(deleted_at__isnull=True, evaluation_type=evaluation.evaluation_type).first()
        if tolerance is None:
            raise serializers.ValidationError({"appetite": "No approved tolerance for this evaluation type."})
        today = timezone.localdate()
        if attrs["expires_on"] < today or attrs["review_on"] < today or attrs["review_on"] > attrs["expires_on"]:
            raise serializers.ValidationError({"review_on": "Review and expiry must be future/current and ordered."})
        if not (attrs.get("rationale") or "").strip():
            raise serializers.ValidationError({"rationale": "A documented reason is mandatory."})
        supersedes = attrs.get("supersedes")
        if supersedes and (supersedes.tenant_id != tenant.id or supersedes.risk_id != risk.id or supersedes.status != RiskAcceptance.Status.APPROVED):
            raise serializers.ValidationError({"supersedes": "Only an approved decision on the same risk can be superseded."})
        attrs["_tolerance_max"] = tolerance.maximum_score
        return attrs


class RiskAcceptanceSerializer(serializers.ModelSerializer):
    is_current = serializers.SerializerMethodField()
    class Meta:
        model = RiskAcceptance
        fields = [
            "id", "risk", "evaluation", "appetite", "requested_by", "decided_by",
            "status", "rationale", "decision_note", "review_on", "expires_on",
            "decided_at", "supersedes", "evaluation_type_snapshot", "score_snapshot",
            "likelihood_snapshot", "impact_snapshot", "evaluated_at_snapshot",
            "tolerance_max_snapshot", "exceeds_tolerance", "exception_justification",
            "is_current", "created_at", "updated_at",
        ]
        read_only_fields = fields
    def get_is_current(self, obj):
        return obj.is_active()
