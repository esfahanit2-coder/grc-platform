import os
import socket
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.exceptions import ValidationError

from apps.evidence.models import Evidence
from apps.organizations.models import OrganizationUnit
from apps.tenancy.models import Tenant, TenantMembership

from .clients import ConnectorResult, validate_http_base_url
from .models import ConnectorConfig, ConnectorRun
from .serializers import ConnectorConfigSerializer
from .services import run_connector


class ConnectorEvidenceTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Pilot", code="pilot-connectors")
        self.user = get_user_model().objects.create_user(username="pilotconn", password="Password12345!")
        TenantMembership.objects.create(tenant=self.tenant, user=self.user, role_code="admin")
        self.unit = OrganizationUnit.objects.create(
            tenant=self.tenant,
            unit_type="company",
            code="HQ",
            name="HQ",
        )

    @patch("apps.connectors.services.connector_for")
    def test_all_connector_types_create_reusable_evidence_contract(self, factory):
        factory.return_value.collect.return_value = ConnectorResult("Connector snapshot", {"ok": True})
        connector_types = [
            ConnectorConfig.ConnectorType.FORTIGATE,
            ConnectorConfig.ConnectorType.TENABLE,
            ConnectorConfig.ConnectorType.VEEAM,
            ConnectorConfig.ConnectorType.ACTIVE_DIRECTORY,
        ]
        for index, connector_type in enumerate(connector_types):
            cfg = ConnectorConfig.objects.create(
                tenant=self.tenant,
                organization_unit=self.unit,
                name=f"connector-{index}",
                connector_type=connector_type,
                base_url="https://connector.example",
                username_env_var="CONNECTOR_USER",
                secret_env_var="CONNECTOR_SECRET",
                configuration={"host": "ad.example", "base_dn": "DC=example,DC=com"}
                if connector_type == ConnectorConfig.ConnectorType.ACTIVE_DIRECTORY
                else {},
            )
            run, evidence = run_connector(cfg, user=self.user)
            self.assertEqual(run.status, ConnectorRun.Status.SUCCEEDED)
            self.assertEqual(evidence.tenant, self.tenant)
            self.assertEqual(evidence.metadata["connector_run_id"], str(run.id))
            self.assertEqual(evidence.metadata["collection_mode"], "read_only")
            self.assertTrue(evidence.metadata["human_review_required"])
            self.assertFalse(evidence.metadata["asserts_compliance"])
            self.assertEqual(len(evidence.metadata["payload_sha256"]), 64)

        self.assertEqual(Evidence.objects.filter(tenant=self.tenant).count(), 4)

    @patch("apps.connectors.services.connector_for")
    def test_failed_sync_is_persisted_and_secret_is_redacted(self, factory):
        cfg = ConnectorConfig.objects.create(
            tenant=self.tenant,
            organization_unit=self.unit,
            name="FG",
            connector_type=ConnectorConfig.ConnectorType.FORTIGATE,
            base_url="https://fg.example",
            secret_env_var="FG_TOKEN",
        )
        factory.return_value.collect.side_effect = RuntimeError("upstream failed with super-secret-token")
        with patch.dict(os.environ, {"FG_TOKEN": "super-secret-token"}):
            with self.assertRaises(RuntimeError):
                run_connector(cfg, user=self.user)

        run = ConnectorRun.objects.get(connector=cfg)
        cfg.refresh_from_db()
        self.assertEqual(run.status, ConnectorRun.Status.FAILED)
        self.assertIn("[REDACTED]", run.error)
        self.assertNotIn("super-secret-token", run.error)
        self.assertEqual(cfg.last_status, "failed")
        self.assertEqual(cfg.last_error, run.error)

    def test_serializer_rejects_literal_secret_and_url_credentials(self):
        serializer = ConnectorConfigSerializer(
            data={
                "name": "unsafe",
                "connector_type": ConnectorConfig.ConnectorType.FORTIGATE,
                "base_url": "https://admin:password@fg.example",
                "secret_env_var": "literal-secret!",
                "configuration": {"read_paths": ["/api/v2/cmdb/system/global"]},
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("secret_env_var", serializer.errors)
        self.assertIn("base_url", serializer.errors)

    def test_serializer_rejects_fortigate_host_escape_path(self):
        serializer = ConnectorConfigSerializer(
            data={
                "name": "unsafe-path",
                "connector_type": ConnectorConfig.ConnectorType.FORTIGATE,
                "base_url": "https://fg.example",
                "secret_env_var": "FG_TOKEN",
                "configuration": {"read_paths": ["https://evil.example/api/v2/cmdb/system/global"]},
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("configuration", serializer.errors)

    @patch("apps.connectors.clients.socket.getaddrinfo")
    def test_http_target_blocks_loopback(self, getaddrinfo):
        getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443)),
        ]
        with self.assertRaises(ValidationError):
            validate_http_base_url("https://connector.example")

    @patch("apps.connectors.clients.socket.getaddrinfo")
    def test_http_target_allows_private_on_prem_address(self, getaddrinfo):
        getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.10.20.30", 443)),
        ]
        parsed = validate_http_base_url("https://connector.example")
        self.assertEqual(parsed.hostname, "connector.example")
