from rest_framework import status,viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from apps.identity.services import accessible_organization_unit_ids,has_whole_tenant_permission,require_tenant_permission,require_whole_tenant_permission
from apps.tenancy.services import resolve_tenant_for_request
from .models import WorkflowDefinition,WorkflowInstance,WorkflowState,WorkflowTransition
from .serializers import WorkflowDefinitionSerializer,WorkflowInstanceSerializer,WorkflowEventSerializer
from .services import start_workflow,transition_workflow

class TenantMixin:
    def _tenant(self):
        if not hasattr(self,'_resolved_tenant'):self._resolved_tenant=resolve_tenant_for_request(self.request)
        return self._resolved_tenant

class WorkflowDefinitionViewSet(TenantMixin,viewsets.ModelViewSet):
    serializer_class=WorkflowDefinitionSerializer
    def get_queryset(self):
        tenant=self._tenant();require_whole_tenant_permission(self.request.user,tenant,'workflow.manage' if self.action not in {'list','retrieve'} else 'workflow.view');return WorkflowDefinition.objects.filter(tenant=tenant,deleted_at__isnull=True).prefetch_related('states','transitions').order_by('name','-version')
    def perform_create(self,serializer):serializer.save(tenant=self._tenant())
    def perform_destroy(self,instance):
        from django.utils import timezone
        instance.deleted_at=timezone.now();instance.is_active=False;instance.save(update_fields=['deleted_at','is_active','updated_at'])
    @action(detail=True,methods=['post'],url_path='states')
    def add_state(self,request,pk=None):
        definition=self.get_object();require_whole_tenant_permission(request.user,self._tenant(),'workflow.manage')
        state=WorkflowState.objects.create(definition=definition,code=request.data.get('code',''),name=request.data.get('name',''),is_initial=bool(request.data.get('is_initial')),is_terminal=bool(request.data.get('is_terminal')),sort_order=int(request.data.get('sort_order',0)),metadata=request.data.get('metadata') or {})
        if state.is_initial: definition.states.exclude(id=state.id).update(is_initial=False)
        return Response({'id':str(state.id),'code':state.code},status=201)
    @action(detail=True,methods=['post'],url_path='transitions')
    def add_transition(self,request,pk=None):
        definition=self.get_object();require_whole_tenant_permission(request.user,self._tenant(),'workflow.manage')
        from_state=definition.states.filter(id=request.data.get('from_state')).first();to_state=definition.states.filter(id=request.data.get('to_state')).first()
        if not from_state or not to_state:raise ValidationError('States must belong to this workflow.')
        row=WorkflowTransition.objects.create(definition=definition,code=request.data.get('code',''),name=request.data.get('name',''),from_state=from_state,to_state=to_state,required_permission_code=request.data.get('required_permission_code',''),condition=request.data.get('condition') or {},actions=request.data.get('actions') or [])
        return Response({'id':str(row.id),'code':row.code},status=201)

class WorkflowInstanceViewSet(TenantMixin,viewsets.ReadOnlyModelViewSet):
    serializer_class=WorkflowInstanceSerializer
    def get_queryset(self):
        tenant=self._tenant();require_tenant_permission(self.request.user,tenant,'workflow.view')
        qs=WorkflowInstance.objects.filter(tenant=tenant,deleted_at__isnull=True).select_related('definition','current_state','organization_unit')
        if not has_whole_tenant_permission(self.request.user,tenant,'workflow.view'):
            allowed=accessible_organization_unit_ids(self.request.user,tenant,'workflow.view');qs=qs.filter(organization_unit_id__in=allowed)
        return qs.order_by('-updated_at')
    @action(detail=False,methods=['post'])
    def start(self,request):
        tenant=self._tenant();definition=WorkflowDefinition.objects.filter(tenant=tenant,id=request.data.get('definition_id'),deleted_at__isnull=True).first()
        if not definition:raise ValidationError('Workflow definition not found.')
        instance=start_workflow(tenant=tenant,user=request.user,definition=definition,object_type=request.data.get('object_type',''),object_id=request.data.get('object_id'),request=request)
        return Response(self.get_serializer(instance).data,status=status.HTTP_201_CREATED)
    @action(detail=True,methods=['post'])
    def transition(self,request,pk=None):
        instance=self.get_object();transition=WorkflowTransition.objects.filter(definition=instance.definition,id=request.data.get('transition_id')).select_related('from_state','to_state').first()
        if not transition:raise ValidationError('Transition not found.')
        instance,event=transition_workflow(tenant=self._tenant(),user=request.user,instance=instance,transition=transition,comment=request.data.get('comment',''),request=request)
        return Response({'instance':self.get_serializer(instance).data,'event':WorkflowEventSerializer(event).data})
    @action(detail=True,methods=['get'])
    def events(self,request,pk=None):return Response(WorkflowEventSerializer(self.get_object().events.order_by('created_at'),many=True).data)
