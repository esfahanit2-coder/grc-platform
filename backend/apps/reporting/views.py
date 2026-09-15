from django.db.models import Count,Q
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.identity.services import accessible_organization_unit_ids,has_whole_tenant_permission,require_tenant_permission
from apps.tenancy.services import resolve_tenant_for_request
from apps.risks.models import Risk,RiskEvaluation
from apps.findings.models import Finding
from apps.actions.models import Action
from apps.assessments.models import Assessment
from apps.controls.models import ControlImplementation
class ManagementDashboardView(APIView):
    def get(self,request):
        t=resolve_tenant_for_request(request);require_tenant_permission(request.user,t,'report.view');whole=has_whole_tenant_permission(request.user,t,'report.view');allowed=accessible_organization_unit_ids(request.user,t,'report.view')
        rf=Q(tenant=t,deleted_at__isnull=True);ff=Q(tenant=t,deleted_at__isnull=True);af=Q(tenant=t,deleted_at__isnull=True);sf=Q(tenant=t,deleted_at__isnull=True);cf=Q(tenant=t,deleted_at__isnull=True)
        if not whole:
            rf&=Q(organization_unit_id__in=allowed);ff&=Q(organization_unit_id__in=allowed);af&=Q(organization_unit_id__in=allowed);sf&=Q(organization_unit_id__in=allowed);cf&=Q(organization_unit_id__in=allowed)
        risks=Risk.objects.filter(rf);findings=Finding.objects.filter(ff);actions=Action.objects.filter(af);assess=Assessment.objects.filter(sf);controls=ControlImplementation.objects.filter(cf)
        latest_high=RiskEvaluation.objects.filter(risk__in=risks,evaluation_type='residual',deleted_at__isnull=True,level__in=['high','critical']).values('risk_id').distinct().count()
        overdue=actions.exclude(status__in=['done','cancelled']).filter(due_date__lt=timezone.now().date()).count()
        avg=None
        vals=list(assess.exclude(overall_score__isnull=True).values_list('overall_score',flat=True)); avg=round(sum(float(v) for v in vals)/len(vals),2) if vals else None
        return Response({'compliance_score':avg,'high_critical_residual_risks':latest_high,'open_findings':findings.exclude(status__in=['closed','accepted']).count(),'overdue_actions':overdue,'control_effectiveness':dict(controls.values_list('effectiveness').annotate(c=Count('id'))),'assessments_due':assess.exclude(status__in=['completed','cancelled']).filter(due_date__isnull=False).count(),'top_findings':list(findings.exclude(status__in=['closed','accepted']).values('id','title','severity','due_date')[:10])})

from django.http import HttpResponse
from rest_framework.exceptions import ValidationError
from apps.documents.models import ReportTemplate
from apps.identity.services import require_whole_tenant_permission
from .template_engine import render_html,render_pdf

class TemplateRenderView(APIView):
    def post(self,request):
        t=resolve_tenant_for_request(request);require_whole_tenant_permission(request.user,t,'report.generate')
        template=ReportTemplate.objects.filter(id=request.data.get('template_id'),deleted_at__isnull=True).filter(Q(tenant=t)|Q(tenant__isnull=True)).first()
        if not template: raise ValidationError('Report template not found.')
        html_template=(template.configuration or {}).get('html_template')
        if not html_template: raise ValidationError('Template configuration has no html_template.')
        context=request.data.get('context') or {};fmt=str(request.data.get('format','html')).lower()
        try:
            if fmt=='pdf':
                payload,_=render_pdf(html_template,context,(template.configuration or {}).get('css',''))
                response=HttpResponse(payload,content_type='application/pdf');response['Content-Disposition']=f'attachment; filename="report-{template.id}.pdf"';return response
            return HttpResponse(render_html(html_template,context),content_type='text/html; charset=utf-8')
        except Exception as exc:
            raise ValidationError({'template':f'Render failed: {exc}'}) from exc
