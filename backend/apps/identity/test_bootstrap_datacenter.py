import json
import os
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.identity.models import UserRoleScope
from apps.tenancy.models import Tenant, TenantMembership


class DatacenterBootstrapCommandTests(TestCase):
    password = "Datacenter-Admin-Password-123!"

    def run_bootstrap(self, **overrides):
        args = {
            "tenant_code": "customer-a",
            "tenant_name": "Customer A",
            "admin_username": "customer-admin",
            "admin_email": "admin@example.invalid",
            "json": True,
        }
        args.update(overrides)
        output = StringIO()
        with patch.dict(os.environ, {"GRC_BOOTSTRAP_ADMIN_PASSWORD": self.password}, clear=False):
            call_command("bootstrap_datacenter", stdout=output, **args)
        return json.loads(output.getvalue())

    def test_creates_non_superuser_tenant_admin_with_whole_tenant_rbac(self):
        payload = self.run_bootstrap()
        User = get_user_model()
        user = User.objects.get(username="customer-admin")
        tenant = Tenant.objects.get(code="customer-a")
        self.assertFalse(user.is_superuser)
        self.assertTrue(TenantMembership.objects.filter(tenant=tenant, user=user, is_active=True, role_code="admin").exists())
        self.assertTrue(
            UserRoleScope.objects.filter(
                tenant=tenant,
                user=user,
                role__code="tenant_admin",
                organization_unit__isnull=True,
                is_active=True,
            ).exists()
        )
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["password_source"], "environment")
        self.assertFalse(payload["is_django_superuser"])

    def test_same_identity_is_idempotent(self):
        first = self.run_bootstrap()
        second = self.run_bootstrap()
        self.assertTrue(first["tenant_created"])
        self.assertTrue(first["user_created"])
        self.assertFalse(second["tenant_created"])
        self.assertFalse(second["user_created"])
        self.assertEqual(Tenant.objects.count(), 1)
        self.assertEqual(get_user_model().objects.filter(username="customer-admin").count(), 1)

    def test_existing_user_from_another_context_is_not_claimed(self):
        get_user_model().objects.create_user(
            username="customer-admin",
            email="admin@example.invalid",
            password=self.password,
        )
        with self.assertRaisesMessage(CommandError, "not already a member"):
            self.run_bootstrap()

    def test_password_must_come_from_environment(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesMessage(CommandError, "GRC_BOOTSTRAP_ADMIN_PASSWORD"):
                call_command(
                    "bootstrap_datacenter",
                    tenant_code="customer-a",
                    tenant_name="Customer A",
                    admin_username="customer-admin",
                    admin_email="admin@example.invalid",
                )
