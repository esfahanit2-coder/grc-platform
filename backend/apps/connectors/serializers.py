from rest_framework import serializers
from .models import ConnectorConfig,ConnectorRun
class ConnectorConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model=ConnectorConfig
        fields=["id","organization_unit","name","connector_type","base_url","username_env_var","secret_env_var","secondary_secret_env_var","verify_tls","is_active","configuration","last_sync_at","last_status","last_error","created_at","updated_at"]
        read_only_fields=["id","last_sync_at","last_status","last_error","created_at","updated_at"]
class ConnectorRunSerializer(serializers.ModelSerializer):
    class Meta:
        model=ConnectorRun
        fields=["id","connector","triggered_by","status","started_at","finished_at","summary","error"]
        read_only_fields=fields
