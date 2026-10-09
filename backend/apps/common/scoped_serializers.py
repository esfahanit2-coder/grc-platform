"""API validation against the same ORM constraints as direct model writes."""
from copy import copy

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers


class TenantValidatedSerializer(serializers.ModelSerializer):
    immutable_links = ()
    related_link_names = ()

    def validate(self, attrs):
        tenant = self.context["tenant"]
        if self.instance:
            for key in self.immutable_links:
                if key in attrs and attrs[key].pk != getattr(self.instance, key + "_id"):
                    raise serializers.ValidationError({key: "Relationship endpoints cannot be moved."})
            if "organization_unit" in attrs and attrs["organization_unit"] != self.instance.organization_unit:
                if self.instance.children.filter(deleted_at__isnull=True).exists():
                    raise serializers.ValidationError({"organization_unit": "Cannot change scope with active child records."})
                if any(getattr(self.instance, name).filter(deleted_at__isnull=True).exists() for name in self.related_link_names):
                    raise serializers.ValidationError({"organization_unit": "Cannot change scope with active relationships."})
            candidate = copy(self.instance)
        else:
            candidate = self.Meta.model(tenant=tenant)
        for key, value in attrs.items():
            setattr(candidate, key, value)
        candidate.tenant = tenant
        try:
            candidate.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(getattr(exc, "message_dict", {"non_field_errors": exc.messages})) from exc
        return attrs
