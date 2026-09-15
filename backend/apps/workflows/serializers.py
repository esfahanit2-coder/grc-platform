from rest_framework import serializers
from .models import WorkflowDefinition,WorkflowState,WorkflowTransition,WorkflowInstance,WorkflowEvent
class WorkflowStateSerializer(serializers.ModelSerializer):
    class Meta: model=WorkflowState;fields=['id','code','name','is_initial','is_terminal','sort_order','metadata']
class WorkflowTransitionSerializer(serializers.ModelSerializer):
    class Meta: model=WorkflowTransition;fields=['id','code','name','from_state','to_state','required_permission_code','condition','actions']
class WorkflowDefinitionSerializer(serializers.ModelSerializer):
    states=WorkflowStateSerializer(many=True,read_only=True);transitions=WorkflowTransitionSerializer(many=True,read_only=True)
    class Meta: model=WorkflowDefinition;fields=['id','name','object_type','version','is_active','configuration','states','transitions','created_at','updated_at'];read_only_fields=['id','created_at','updated_at']
class WorkflowInstanceSerializer(serializers.ModelSerializer):
    current_state_detail=WorkflowStateSerializer(source='current_state',read_only=True)
    class Meta: model=WorkflowInstance;fields=['id','definition','object_type','object_id','organization_unit','current_state','current_state_detail','started_by','status','metadata','created_at','updated_at'];read_only_fields=['id','organization_unit','current_state','started_by','status','created_at','updated_at']
class WorkflowEventSerializer(serializers.ModelSerializer):
    class Meta: model=WorkflowEvent;fields=['id','transition','from_state','to_state','actor','comment','metadata','created_at'];read_only_fields=fields
