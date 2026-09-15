from rest_framework import serializers
from .models import AIProviderConfig, AIInteraction, AISuggestion, KnowledgeChunk

class AIProviderConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIProviderConfig
        fields = ["id","name","provider_type","base_url","model_name","secret_env_var","is_active","is_default","allow_confidential","configuration","created_at","updated_at"]
        read_only_fields = ["id","created_at","updated_at"]

class AIInteractionSerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source="provider.name", read_only=True)
    class Meta:
        model = AIInteraction
        fields = ["id","capability","classification","provider","provider_name","input_summary","context_manifest","output","confidence","status","error","created_at"]
        read_only_fields = fields

class AISuggestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AISuggestion
        fields = ["id","interaction","object_type","object_id","suggestion_type","proposed_value","confidence","status","reviewed_by","reviewed_at","review_comment","created_at"]
        read_only_fields = fields

class KnowledgeChunkSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeChunk
        fields = ["id","organization_unit","source_type","source_id","title","content","content_hash","token_count","classification","metadata","embedding_model","embedding_dimensions","embedded_at","created_at","updated_at"]
        read_only_fields = ["id","content_hash","token_count","embedding_model","embedding_dimensions","embedded_at","created_at","updated_at"]
