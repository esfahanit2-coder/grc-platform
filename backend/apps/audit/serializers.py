from rest_framework import serializers
from .models import AuditEvent


class AuditEventSerializer(serializers.ModelSerializer):
    actor = serializers.SerializerMethodField()

    class Meta:
        model = AuditEvent
        fields = [
            "id", "created_at", "request_id", "actor", "action", "category", "outcome",
            "object_type", "object_id", "object_repr", "old_data", "new_data", "metadata",
            "ip_address", "http_method", "path", "previous_hash", "event_hash",
        ]

    def get_actor(self, event):
        return {"id": event.actor_id, "username": event.actor_username} if event.actor_username or event.actor_id else None
