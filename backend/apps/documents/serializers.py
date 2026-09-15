from rest_framework import serializers
from django.utils import timezone
from apps.tenancy.models import TenantMembership
from .models import Document,DocumentVersion,DocumentApproval,DocumentLink,ReportTemplate
class DocumentSerializer(serializers.ModelSerializer):
    owner_display=serializers.SerializerMethodField();current_version_code=serializers.CharField(source='current_version.version',read_only=True)
    class Meta: model=Document;fields=["id","organization_unit","document_type","code","title","owner","owner_display","status","review_date","current_version","current_version_code","metadata","created_at","updated_at"]
    def get_owner_display(self,o): return o.owner.get_full_name() or o.owner.get_username()
    def validate(self,a):
        t=self.context['tenant'];u=a.get('organization_unit',getattr(self.instance,'organization_unit',None));owner=a.get('owner',getattr(self.instance,'owner',None))
        if u and u.tenant_id!=t.id: raise serializers.ValidationError({'organization_unit':'Unit must belong to tenant.'})
        if owner and not TenantMembership.objects.filter(tenant=t,user=owner,is_active=True).exists(): raise serializers.ValidationError({'owner':'Owner must be tenant member.'})
        return a
class DocumentVersionSerializer(serializers.ModelSerializer):
    class Meta: model=DocumentVersion;fields=["id","document","version","content","storage_key","change_summary","created_by","status","created_at","updated_at"];read_only_fields=['created_by','created_at','updated_at']
    def validate_document(self,d):
        if d.tenant_id!=self.context['tenant'].id: raise serializers.ValidationError('Document must belong to tenant.')
        if self.instance is not None and d.id!=self.instance.document_id: raise serializers.ValidationError('Document version cannot be moved to another document.')
        return d
class DocumentApprovalSerializer(serializers.ModelSerializer):
    approver_display=serializers.SerializerMethodField()
    class Meta: model=DocumentApproval;fields=["id","version","approver","approver_display","approval_order","decision","comment","decided_at","created_at"];read_only_fields=['decision','comment','decided_at','created_at']
    def get_approver_display(self,o): return o.approver.get_full_name() or o.approver.get_username()
class DocumentLinkSerializer(serializers.ModelSerializer):
    class Meta: model=DocumentLink;fields='__all__';read_only_fields=['tenant','created_at','updated_at','deleted_at']
class ReportTemplateSerializer(serializers.ModelSerializer):
    class Meta: model=ReportTemplate;fields='__all__';read_only_fields=['tenant','created_at','updated_at','deleted_at']
