import base64
import os
import socket
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.exceptions import ValidationError

from apps.organizations.models import OrganizationUnit
from apps.tenancy.models import Tenant, TenantMembership

from .clients import validate_http_base_url
from .models import ConnectorConfig, ConnectorRun
from .services import run_connector


class ConnectorSecurityBoundaryTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Security Tenant", code="connector-security")
        self.user = get_user_model().objects.create_user(username="connector-sec", password="StrongPassword123!")
        TenantMembership.objects.create(tenant=self.tenant, user=self.user, role_code="admin")
        self.unit = OrganizationUnit.objects.create(
            tenant=self.tenant,
            unit_type="company",
            code="HQ",
            name="HQ",
        )

    @patch("apps.connectors.services.connector_for")
    def test_connector_exception_redacts_raw_and_basic_auth_credentials(self, factory):
        cfg = ConnectorConfig.objects.create(
            tenant=self.tenant,
            organization_unit=self.unit,
            name="Veeam security",
            connector_type=ConnectorConfig.ConnectorType.VEEAM,
            base_url="https://veeam.example",
            username_env_var="VEEAM_TEST_USER",
            secret_env_var="VEEAM_TEST_PASSWORD",
        )
        username = "svc-backup"
        password = "Sup3r-Secret!"
        encoded = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
        factory.return_value.collect.side_effect = RuntimeError(
            f"upstream Authorization: Basic {encoded}; user={username}; password={password}"
        )
        with patch.dict(
            os.environ,
            {"VEEAM_TEST_USER": username, "VEEAM_TEST_PASSWORD": password},
        ):
            with self.assertRaises(RuntimeError) as raised:
                run_connector(cfg, user=self.user)

        message = str(raised.exception)
        self.assertIn("[REDACTED]", message)
        self.assertNotIn(username, message)
        self.assertNotIn(password, message)
        self.assertNotIn(encoded, message)
        run = ConnectorRun.objects.get(connector=cfg)
        self.assertEqual(run.error, message)

    @patch("apps.connectors.clients.socket.getaddrinfo")
    def test_runtime_target_rejects_cloud_metadata_link_local_address(self, getaddrinfo):
        getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("169.254.169.254", 443)),
        ]
        with self.assertRaises(ValidationError):
            validate_http_base_url("https://metadata-alias.example")

    @patch("apps.connectors.clients.socket.getaddrinfo")
    def test_runtime_target_rejects_ipv6_loopback(self, getaddrinfo):
        getaddrinfo.return_value = [
            (socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("::1", 443, 0, 0)),
        ]
        with self.assertRaises(ValidationError):
            validate_http_base_url("https://connector.example")
