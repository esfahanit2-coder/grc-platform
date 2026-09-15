from rest_framework import serializers
from apps.actions.models import Action
from apps.identity.services import has_whole_tenant_permission
from apps.tenancy.models import TenantMembership
from .models import Risk,RiskCategory,RiskControl,RiskEvaluation,RiskMethodology,RiskTreatment
from .services import latest_evaluations,methodology_defaults

def member(user,tenant,field):
    if user and not TenantMembership.objects.filter(tenant=tenant,user=user,is_active=True).exists(): raise serializers.ValidationError({field:"User must be an active tenant member."})

class RiskCategorySerializer(serializers.ModelSerializer):
    is_global=serializers.SerializerMethodField()
    class Meta:
        model=RiskCategory;fields=["id","parent","code","name","description","is_global","created_at","updated_at"];read_only_fields=["created_at","updated_at","is_global"]
    def get_is_global(self,obj): return obj.tenant_id is None

class RiskMethodologySerializer(serializers.ModelSerializer):
    class Meta:
        model=RiskMethodology;fields=["id","name","methodology_type","likelihood_scale","impact_scale","matrix","thresholds","formula","is_default","status","created_at","updated_at"];read_only_fields=["created_at","updated_at"]
    def validate(self,attrs):
        if self.instance is None:
            defaults=methodology_defaults()
            for key in ("likelihood_scale","impact_scale","thresholds"): attrs.setdefault(key,defaults[key])
            attrs.setdefault("formula",defaults["formula"])
        return attrs

class EvaluationSummarySerializer(serializers.ModelSerializer):
    methodology_name=serializers.CharField(source="methodology.name",read_only=True)
    class Meta:
        model=RiskEvaluation;fields=["id","evaluation_type","methodology","methodology_name","likelihood","impact","score","level","evaluated_at","rationale"]

class RiskSerializer(serializers.ModelSerializer):
    owner_display=serializers.SerializerMethodField();organization_name=serializers.CharField(source="organization_unit.name",read_only=True);asset_title=serializers.CharField(source="asset.title",read_only=True);category_name=serializers.CharField(source="category.name",read_only=True);latest_evaluations=serializers.SerializerMethodField()
    class Meta:
        model=Risk;fields=["id","organization_unit","organization_name","asset","asset_title","category","category_name","code","title","scenario","cause","consequence","owner","owner_display","status","review_date","metadata","latest_evaluations","created_at","updated_at"];read_only_fields=["created_at","updated_at","owner_display","latest_evaluations"]
    def get_owner_display(self,obj): return obj.owner.get_full_name() or obj.owner.get_username()
    def get_latest_evaluations(self,obj): return {k:EvaluationSummarySerializer(v).data for k,v in latest_evaluations(obj).items()}
    def validate(self,attrs):
        tenant=self.context["tenant"];unit=attrs.get("organization_unit") if "organization_unit" in attrs else getattr(self.instance,"organization_unit",None);asset=attrs.get("asset") if "asset" in attrs else getattr(self.instance,"asset",None);category=attrs.get("category") if "category" in attrs else getattr(self.instance,"category",None);owner=attrs.get("owner") or getattr(self.instance,"owner",None)
        if unit and unit.tenant_id!=tenant.id: raise serializers.ValidationError({"organization_unit":"Unit must belong to tenant."})
        if asset and asset.tenant_id!=tenant.id: raise serializers.ValidationError({"asset":"Asset must belong to tenant."})
        if asset and unit is None:
            attrs["organization_unit"] = asset.organization_unit
            unit = asset.organization_unit
        if asset and unit and asset.organization_unit_id!=unit.id: raise serializers.ValidationError({"asset":"Asset must belong to selected organization unit."})
        if category and category.tenant_id not in {None,tenant.id}: raise serializers.ValidationError({"category":"Risk category is not visible to tenant."})
        member(owner,tenant,"owner")
        return attrs

class RiskEvaluationCreateSerializer(serializers.Serializer):
    methodology=serializers.PrimaryKeyRelatedField(queryset=RiskMethodology.objects.all())
    evaluation_type=serializers.ChoiceField(choices=RiskEvaluation.EvaluationType.choices)
    likelihood=serializers.DecimalField(max_digits=10,decimal_places=2)
    impact=serializers.DecimalField(max_digits=10,decimal_places=2)
    rationale=serializers.CharField(required=False,allow_blank=True)

class RiskControlSerializer(serializers.ModelSerializer):
    control_code=serializers.CharField(source="control_implementation.control.code",read_only=True);control_title=serializers.CharField(source="control_implementation.control.title",read_only=True)
    class Meta:
        model=RiskControl;fields=["id","risk","control_implementation","control_code","control_title","relationship_type","created_at"];read_only_fields=["created_at"]
    def validate(self,attrs):
        tenant=self.context["tenant"];risk=attrs.get("risk") or (self.instance.risk if self.instance else None);ci=attrs.get("control_implementation") or (self.instance.control_implementation if self.instance else None)
        if risk is None or ci is None: return attrs
        if risk.tenant_id!=tenant.id or ci.tenant_id!=tenant.id: raise serializers.ValidationError("Risk and control implementation must belong to tenant.")
        if self.instance is not None:
            if "risk" in attrs and attrs["risk"].id != self.instance.risk_id: raise serializers.ValidationError({"risk":"Risk link is immutable."})
            if "control_implementation" in attrs and attrs["control_implementation"].id != self.instance.control_implementation_id: raise serializers.ValidationError({"control_implementation":"Control implementation link is immutable."})
        if risk.organization_unit_id and ci.organization_unit_id!=risk.organization_unit_id: raise serializers.ValidationError("Control implementation must be in the risk organization scope.")
        return attrs

class RiskTreatmentSerializer(serializers.ModelSerializer):
    owner_display=serializers.SerializerMethodField();actions=serializers.SerializerMethodField()
    class Meta:
        model=RiskTreatment;fields=["id","risk","strategy","description","owner","owner_display","target_date","target_score","approval_status","status","accepted_by","accepted_at","actions","created_at","updated_at"];read_only_fields=["accepted_by","accepted_at","owner_display","actions","created_at","updated_at"]
    def get_owner_display(self,obj): return obj.owner.get_full_name() or obj.owner.get_username()
    def get_actions(self,obj):
        return [{"id":str(a.id),"title":a.title,"owner":a.owner.get_full_name() or a.owner.get_username(),"due_date":a.due_date,"progress":a.progress,"status":a.status} for a in Action.objects.filter(tenant=obj.risk.tenant,source_type="risk_treatment",source_id=obj.id,deleted_at__isnull=True).select_related("owner")]
    def validate(self, attrs):
        tenant = self.context["tenant"]
        risk = attrs.get("risk") or (self.instance.risk if self.instance else None)
        owner = attrs.get("owner") or (self.instance.owner if self.instance else None)
        if risk is None:
            raise serializers.ValidationError({"risk": "Risk is required."})
        if risk.tenant_id != tenant.id:
            raise serializers.ValidationError({"risk": "Risk must belong to tenant."})
        if self.instance is not None and "risk" in attrs and attrs["risk"].id != self.instance.risk_id:
            raise serializers.ValidationError({"risk":"Risk treatment cannot be moved to another risk."})
        member(owner, tenant, "owner")
        return attrs
