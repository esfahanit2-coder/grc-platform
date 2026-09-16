from django.utils import timezone
from rest_framework import viewsets,status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from apps.audit.services import record_audit_event
from apps.identity.services import accessible_organization_unit_ids,has_whole_tenant_permission,require_tenant_permission,require_whole_tenant_permission
from apps.tenancy.services import resolve_tenant_for_request
from apps.assessments.models import Assessment
from .models import Document,DocumentVersion,DocumentApproval,DocumentLink,ReportTemplate
from .serializers import DocumentSerializer,DocumentVersionSerializer,DocumentApprovalSerializer,DocumentLinkSerializer,ReportTemplateSerializer
from .exporters import soa_docx,document_docx
class TM:
    def _tenant(self):
        if not hasattr(self,'_t'):self._t=resolve_tenant_for_request(self.request)
        return self._t
    def get_serializer_context(self):c=super().get_serializer_context();c['tenant']=self._tenant();return c
class DocumentViewSet(TM,viewsets.ModelViewSet):
    serializer_class=DocumentSerializer
    def get_queryset(self):
        t=self._tenant();require_tenant_permission(self.request.user,t,'document.view');qs=Document.objects.filter(tenant=t,deleted_at__isnull=True).select_related('organization_unit','owner','current_version')
        if not has_whole_tenant_permission(self.request.user,t,'document.view'):qs=qs.filter(organization_unit_id__in=accessible_organization_unit_ids(self.request.user,t,'document.view'))
        return qs.order_by('code')
    def perform_create(self,s):
        t=self._tenant();u=s.validated_data.get('organization_unit');require_tenant_permission(self.request.user,t,'document.manage',u) if u else require_whole_tenant_permission(self.request.user,t,'document.manage');o=s.save(tenant=t);record_audit_event(self.request.user,t,'document.create','document',o.id,request=self.request)
    def perform_update(self,s):
        t=self._tenant();o=s.instance;require_tenant_permission(self.request.user,t,'document.manage',o.organization_unit) if o.organization_unit else require_whole_tenant_permission(self.request.user,t,'document.manage');nu=s.validated_data.get('organization_unit',o.organization_unit);require_tenant_permission(self.request.user,t,'document.manage',nu) if nu else require_whole_tenant_permission(self.request.user,t,'document.manage');s.save()
    def perform_destroy(self,o):
        t=self._tenant();require_tenant_permission(self.request.user,t,'document.manage',o.organization_unit) if o.organization_unit else require_whole_tenant_permission(self.request.user,t,'document.manage');o.deleted_at=timezone.now();o.status=Document.Status.DEPRECATED;o.save(update_fields=['deleted_at','status','updated_at'])
class DocumentVersionViewSet(TM,viewsets.ModelViewSet):
    serializer_class=DocumentVersionSerializer
    def get_queryset(self):
        t=self._tenant();require_tenant_permission(self.request.user,t,'document.view');qs=DocumentVersion.objects.filter(document__tenant=t,deleted_at__isnull=True).select_related('document__organization_unit','created_by')
        if not has_whole_tenant_permission(self.request.user,t,'document.view'):qs=qs.filter(document__organization_unit_id__in=accessible_organization_unit_ids(self.request.user,t,'document.view'))
        return qs.order_by('-created_at')
    def perform_create(self,s):
        t=self._tenant();d=s.validated_data['document'];require_tenant_permission(self.request.user,t,'document.manage',d.organization_unit) if d.organization_unit else require_whole_tenant_permission(self.request.user,t,'document.manage');v=s.save(created_by=self.request.user);d.current_version=v;d.save(update_fields=['current_version','updated_at'])
    @action(detail=True,methods=['post'])
    def submit(self,request,pk=None):
        v=self.get_object();t=self._tenant();d=v.document;require_tenant_permission(request.user,t,'document.manage',d.organization_unit) if d.organization_unit else require_whole_tenant_permission(request.user,t,'document.manage');v.status=DocumentVersion.Status.REVIEW;v.save(update_fields=['status','updated_at']);d.status=Document.Status.REVIEW;d.save(update_fields=['status','updated_at']);return Response(self.get_serializer(v).data)
    @action(detail=True,methods=['get'])
    def export(self,request,pk=None):
        v=self.get_object();t=self._tenant();record_audit_event(request.user,t,'document.export','document_version',v.id,metadata={'document_id':str(v.document_id),'format':'docx'},request=request);return document_docx(v)
class DocumentApprovalViewSet(TM,viewsets.ModelViewSet):
    serializer_class=DocumentApprovalSerializer
    def get_queryset(self):
        t=self._tenant();require_tenant_permission(self.request.user,t,'document.view');qs=DocumentApproval.objects.filter(version__document__tenant=t,deleted_at__isnull=True).select_related('version__document__organization_unit','approver');return qs if has_whole_tenant_permission(self.request.user,t,'document.view') else qs.filter(version__document__organization_unit_id__in=accessible_organization_unit_ids(self.request.user,t,'document.view'))
    def perform_create(self,s):
        t=self._tenant();v=s.validated_data['version'];d=v.document;require_tenant_permission(self.request.user,t,'document.manage',d.organization_unit) if d.organization_unit else require_whole_tenant_permission(self.request.user,t,'document.manage');s.save()
    @action(detail=True,methods=['post'])
    def decide(self,request,pk=None):
        a=self.get_object();t=self._tenant();d=a.version.document;require_tenant_permission(request.user,t,'document.approve',d.organization_unit) if d.organization_unit else require_whole_tenant_permission(request.user,t,'document.approve');
        if a.approver_id!=request.user.id and not has_whole_tenant_permission(request.user,t,'document.approve'):raise ValidationError('Only assigned approver may decide.')
        decision=request.data.get('decision');
        if decision not in {x for x,_ in DocumentApproval.Decision.choices if x!='pending'}:raise ValidationError({'decision':'Invalid decision.'})
        a.decision=decision;a.comment=request.data.get('comment','');a.decided_at=timezone.now();a.save(update_fields=['decision','comment','decided_at','updated_at'])
        if decision=='approved' and not a.version.approvals.exclude(decision='approved').exists():a.version.status=DocumentVersion.Status.APPROVED;a.version.save(update_fields=['status','updated_at']);d.status=Document.Status.APPROVED;d.save(update_fields=['status','updated_at'])
        return Response(self.get_serializer(a).data)
class ReportTemplateViewSet(TM,viewsets.ModelViewSet):
    serializer_class=ReportTemplateSerializer
    def get_queryset(self):t=self._tenant();require_tenant_permission(self.request.user,t,'report.view');return ReportTemplate.objects.filter(deleted_at__isnull=True).filter(tenant__in=[t,None])
    def perform_create(self,s):require_whole_tenant_permission(self.request.user,self._tenant(),'report.generate');s.save(tenant=self._tenant())
class SoAViewSet(TM,viewsets.ViewSet):
    @action(detail=False,methods=['get'],url_path=r'(?P<assessment_id>[^/.]+)')
    def generate(self,request,assessment_id=None):
        t=self._tenant();a=Assessment.objects.select_related('organization_unit','framework_version').filter(id=assessment_id,tenant=t,deleted_at__isnull=True).first();
        if not a: raise ValidationError('Assessment not found.')
        require_tenant_permission(request.user,t,'report.generate',a.organization_unit) if a.organization_unit else require_whole_tenant_permission(request.user,t,'report.generate');record_audit_event(request.user,t,'report.export','assessment',a.id,metadata={'report':'soa','format':'docx','framework_version_id':str(a.framework_version_id)},request=request);return soa_docx(a)
