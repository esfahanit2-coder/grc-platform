from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.identity.services import bootstrap_tenant_rbac
from apps.tenancy.models import Tenant, TenantMembership
from .models import AuditEvent
from .services import record_audit_event, verify_audit_chain


class AuditTrailTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="auditor-admin", password="StrongPassword123!")
        self.tenant = Tenant.objects.create(name="Audit Tenant", code="audit-tenant")
        TenantMembership.objects.create(tenant=self.tenant, user=self.user, role_code="admin")
        bootstrap_tenant_rbac(self.tenant, admin_user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(self.user).access_token}", HTTP_X_TENANT_ID=str(self.tenant.id))

    def test_audit_event_api_returns_before_after_data_and_integrity_hashes(self):
        record_audit_event(self.user, self.tenant, "tenant.update", "tenant", self.tenant.id, old_data={"name": "A"}, new_data={"name": "B"})
        response = self.client.get("/api/v1/audit-events/")
        self.assertEqual(response.status_code, 200)
        event = response.data["results"][0]
        self.assertEqual(event["old_data"]["name"], "A")
        self.assertEqual(event["new_data"]["name"], "B")
        self.assertEqual(len(event["event_hash"]), 64)
        self.assertEqual(event["previous_hash"], "")

    def test_audit_chain_links_events_and_verifies_clean_history(self):
        first = record_audit_event(self.user, self.tenant, "tenant.update", "tenant", self.tenant.id, new_data={"step": 1})
        second = record_audit_event(self.user, self.tenant, "tenant.update", "tenant", self.tenant.id, new_data={"step": 2})
        self.assertEqual(second.previous_hash, first.event_hash)
        result = verify_audit_chain(self.tenant)
        self.assertTrue(result["valid"])
        self.assertEqual(result["checked"], 2)
        self.assertEqual(result["last_hash"], second.event_hash)

    def test_historical_audit_rows_are_append_only_through_orm(self):
        event = record_audit_event(self.user, self.tenant, "tenant.update", "tenant", self.tenant.id)
        event.object_repr = "tampered"
        with self.assertRaises(ValidationError):
            event.save()
        with self.assertRaises(ValidationError):
            AuditEvent.objects.filter(pk=event.pk).update(object_repr="tampered")
        with self.assertRaises(ValidationError):
            AuditEvent.objects.filter(pk=event.pk).delete()

    def test_raw_database_tampering_breaks_chain_verification(self):
        event = record_audit_event(self.user, self.tenant, "tenant.update", "tenant", self.tenant.id, object_repr="original")
        record_audit_event(self.user, self.tenant, "tenant.read", "tenant", self.tenant.id)
        self.assertTrue(verify_audit_chain(self.tenant)["valid"])
        table = connection.ops.quote_name(AuditEvent._meta.db_table)
        with connection.cursor() as cursor:
            cursor.execute(f"UPDATE {table} SET object_repr = %s WHERE id = %s", ["tampered", event.id])
        result = verify_audit_chain(self.tenant)
        self.assertFalse(result["valid"])
        self.assertEqual(result["event_id"], str(event.id))
        self.assertEqual(result["reason"], "event_hash_mismatch")
