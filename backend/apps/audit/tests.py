from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.identity.services import bootstrap_tenant_rbac
from apps.tenancy.models import Tenant, TenantMembership

from .models import AuditEvent, AuditIntegrityMutationError
from .services import record_audit_event


class AuditTrailTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="auditor-admin", password="StrongPassword123!")
        self.tenant = Tenant.objects.create(name="Audit Tenant", code="audit-tenant")
        TenantMembership.objects.create(tenant=self.tenant, user=self.user, role_code="admin")
        bootstrap_tenant_rbac(self.tenant, admin_user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(self.user).access_token}", HTTP_X_TENANT_ID=str(self.tenant.id))

    def test_audit_event_api_returns_before_after_data(self):
        record_audit_event(self.user, self.tenant, "tenant.update", "tenant", self.tenant.id, old_data={"name": "A"}, new_data={"name": "B"})
        response = self.client.get("/api/v1/audit-events/")
        self.assertEqual(response.status_code, 200)
        event = response.data["results"][0]
        self.assertEqual(event["old_data"]["name"], "A")
        self.assertEqual(event["new_data"]["name"], "B")

    def test_audit_event_contains_integrity_fields(self):
        event = record_audit_event(self.user, self.tenant, "tenant.update", "tenant", self.tenant.id)
        self.assertTrue(event.event_hash)
        self.assertTrue(event.integrity_key_id)
        self.assertEqual(event.chain_sequence, 1)

    def test_audit_chain_links_events(self):
        first = record_audit_event(self.user, self.tenant, "tenant.update", "tenant", self.tenant.id)
        second = record_audit_event(self.user, self.tenant, "tenant.update", "tenant", self.tenant.id)
        self.assertEqual(second.chain_sequence, 2)
        self.assertEqual(second.previous_hash, first.event_hash)

    def test_audit_event_update_is_forbidden(self):
        event = record_audit_event(self.user, self.tenant, "tenant.update", "tenant", self.tenant.id)
        event.object_repr = "tampered"
        with self.assertRaises(AuditIntegrityMutationError):
            event.save()

    def test_audit_event_delete_is_forbidden(self):
        event = record_audit_event(self.user, self.tenant, "tenant.update", "tenant", self.tenant.id)
        with self.assertRaises(AuditIntegrityMutationError):
            event.delete()
