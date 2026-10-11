from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.common.domain_objects import (
    domain_object_display,
    domain_object_scope,
    resolve_domain_object,
    supports_domain_object_type,
)
from apps.frameworks.models import Framework, FrameworkVersion, Requirement
from apps.organizations.models import OrganizationUnit
from apps.risks.models import Risk, RiskCategory
from apps.tenancy.models import Tenant


User = get_user_model()


class DomainObjectRegistryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="domain-registry-user", password="StrongPassword123!"
        )
        self.tenant = Tenant.objects.create(
            name="Registry Tenant", code="registry-tenant"
        )
        self.other_tenant = Tenant.objects.create(
            name="Other Registry Tenant", code="registry-other"
        )
        self.unit = OrganizationUnit.objects.create(
            tenant=self.tenant,
            unit_type="department",
            code="SEC",
            name="Security",
        )
        self.other_unit = OrganizationUnit.objects.create(
            tenant=self.other_tenant,
            unit_type="department",
            code="OPS",
            name="Operations",
        )
        category = RiskCategory.objects.create(
            tenant=self.tenant, code="cyber", name="Cyber"
        )
        other_category = RiskCategory.objects.create(
            tenant=self.other_tenant, code="ops", name="Operational"
        )
        self.risk = Risk.objects.create(
            tenant=self.tenant,
            organization_unit=self.unit,
            category=category,
            code="R-001",
            title="Registry risk",
            owner=self.user,
        )
        self.foreign_risk = Risk.objects.create(
            tenant=self.other_tenant,
            organization_unit=self.other_unit,
            category=other_category,
            code="R-OTHER",
            title="Foreign risk",
            owner=self.user,
        )

        global_framework = Framework.objects.create(
            code="global-demo",
            name="Global Demo",
            status=Framework.Status.ACTIVE,
            license_type=Framework.LicenseType.PUBLIC,
        )
        global_version = FrameworkVersion.objects.create(
            framework=global_framework,
            version_code="1",
            status=FrameworkVersion.Status.ACTIVE,
            is_locked=True,
        )
        self.global_requirement = Requirement.objects.create(
            framework_version=global_version,
            code="G-1",
            title="Global requirement",
        )

        tenant_framework = Framework.objects.create(
            tenant=self.other_tenant,
            code="other-private",
            name="Other Private",
            status=Framework.Status.ACTIVE,
        )
        tenant_version = FrameworkVersion.objects.create(
            framework=tenant_framework,
            version_code="1",
            status=FrameworkVersion.Status.ACTIVE,
        )
        self.foreign_requirement = Requirement.objects.create(
            framework_version=tenant_version,
            code="P-1",
            title="Private requirement",
        )

    def test_capabilities_are_explicit(self):
        self.assertTrue(
            supports_domain_object_type("risk", capability="evidence")
        )
        self.assertTrue(
            supports_domain_object_type("risk", capability="workflow")
        )
        self.assertFalse(
            supports_domain_object_type("requirement", capability="workflow")
        )
        self.assertFalse(
            supports_domain_object_type("does-not-exist", capability="evidence")
        )

    def test_resolves_same_tenant_and_scope(self):
        obj = resolve_domain_object(self.tenant, "risk", self.risk.id)
        self.assertEqual(obj, self.risk)
        self.assertEqual(domain_object_scope("risk", obj), self.unit)

    def test_foreign_tenant_record_is_cloaked(self):
        self.assertIsNone(
            resolve_domain_object(self.tenant, "risk", self.foreign_risk.id)
        )

    def test_global_requirement_is_visible_without_scope(self):
        obj = resolve_domain_object(
            self.tenant, "requirement", self.global_requirement.id
        )
        self.assertEqual(obj, self.global_requirement)
        self.assertIsNone(domain_object_scope("requirement", obj))

    def test_foreign_tenant_requirement_is_cloaked(self):
        self.assertIsNone(
            resolve_domain_object(
                self.tenant, "requirement", self.foreign_requirement.id
            )
        )

    def test_display_is_stable_and_human_readable(self):
        self.assertEqual(
            domain_object_display("risk", self.risk, self.risk.id),
            "R-001 · Registry risk",
        )


    def test_reference_inspector_distinguishes_missing_deleted_foreign_and_scope(self):
        from django.utils import timezone
        from uuid import uuid4
        from apps.common.domain_objects import inspect_domain_reference
        from apps.risks.models import Risk

        inspect = lambda kind, target: inspect_domain_reference(
            tenant=self.tenant, type_code=kind, object_id=target, capability="evidence"
        )
        self.assertEqual(inspect("unknown-object", self.risk.id), "unknown_type")
        self.assertEqual(
            inspect_domain_reference(
                tenant=self.tenant, type_code="risk", object_id=self.risk.id,
                capability="not-a-capability",
            ), "unsupported_capability"
        )
        self.assertEqual(inspect("risk", uuid4()), "missing")
        self.assertEqual(inspect("risk", self.foreign_risk.id), "cross_tenant")
        self.assertEqual(inspect("risk", self.risk.id), "ok")
        self.assertEqual(inspect("requirement", self.global_requirement.id), "ok")

        invalid_scope = Risk.objects.create(
            tenant=self.tenant, organization_unit=self.other_unit,
            code="R-SCOPE", title="Invalid organizational scope", owner=self.user,
        )
        self.assertEqual(inspect("risk", invalid_scope.id), "invalid_scope")

        self.risk.deleted_at = timezone.now()
        self.risk.save(update_fields=["deleted_at"])
        self.assertEqual(inspect("risk", self.risk.id), "deleted")


    def test_read_only_integrity_command_reports_deterministic_json_and_nonzero(self):
        import json
        from io import StringIO
        from uuid import uuid4
        from django.core.management import call_command
        from django.core.management.base import CommandError
        from django.utils import timezone
        from apps.actions.models import Action
        from apps.documents.models import Document, DocumentLink
        from apps.evidence.models import Evidence, EvidenceLink
        from apps.workflows.models import WorkflowDefinition, WorkflowInstance, WorkflowState

        evidence = Evidence.objects.create(
            tenant=self.tenant, organization_unit=self.unit,
            title="Audit evidence", owner=self.user,
        )
        valid_link = EvidenceLink.objects.create(
            tenant=self.tenant, evidence=evidence, object_type="risk",
            object_id=self.risk.id,
        )
        EvidenceLink.objects.create(
            tenant=self.tenant, evidence=evidence, object_type="risk",
            object_id=self.foreign_risk.id,
        )
        EvidenceLink.objects.create(
            tenant=self.tenant, evidence=evidence, object_type="risk",
            object_id=uuid4(),
        )
        EvidenceLink.objects.create(
            tenant=self.tenant, evidence=evidence, object_type="unregistered",
            object_id=self.risk.id,
        )
        invalid_action = Action.objects.create(
            tenant=self.tenant, organization_unit=self.unit,
            title="Incomplete source", owner=self.user,
            source_type="finding", source_id=None,
        )
        Action.objects.create(
            tenant=self.tenant, organization_unit=self.unit,
            title="Legitimate unbound action", owner=self.user,
        )

        foreign_document = Document.objects.create(
            tenant=self.other_tenant, organization_unit=self.other_unit,
            document_type="policy", code="FOREIGN-DOC",
            title="Foreign document", owner=self.user,
        )
        DocumentLink.objects.create(
            tenant=self.tenant, document=foreign_document,
            object_type="risk", object_id=self.risk.id,
        )

        wf = WorkflowDefinition.objects.create(
            tenant=self.tenant, name="Domain integrity test", object_type="risk",
        )
        state = WorkflowState.objects.create(
            definition=wf, code="new", name="New", is_initial=True,
        )
        instance = WorkflowInstance.objects.create(
            tenant=self.tenant, definition=wf, current_state=state,
            object_type="risk", object_id=self.risk.id,
            organization_unit=self.other_unit,
        )

        out = StringIO()
        with self.assertRaises(CommandError):
            call_command("verify_domain_references", "--json", stdout=out)
        report = json.loads(out.getvalue())
        self.assertEqual(report["schema"], "grc-domain-reference-integrity-v1")
        self.assertFalse(report["ok"])
        statuses = {x["status"] for x in report["findings"]}
        self.assertTrue({
            "cross_tenant", "missing", "unknown_type",
            "incomplete_reference", "cross_tenant_source", "scope_mismatch",
        }.issubset(statuses))
        self.assertEqual(report["checked"], 7)
        self.assertEqual(
            report["findings"],
            sorted(report["findings"], key=lambda x: (x["source"], x["tenant_id"], x["row_id"])),
        )
        self.assertNotIn("Foreign document", out.getvalue())
        self.assertNotIn("Invalid organizational scope", out.getvalue())

        # No command-side write/repair occurs, even when the audit fails.
        invalid_action.refresh_from_db()
        valid_link.refresh_from_db()
        instance.refresh_from_db()
        self.assertIsNone(invalid_action.source_id)
        self.assertEqual(valid_link.object_id, self.risk.id)
        self.assertEqual(instance.organization_unit_id, self.other_unit.id)

        self.risk.deleted_at = timezone.now()
        self.risk.save(update_fields=["deleted_at"])
        out2 = StringIO()
        with self.assertRaises(CommandError):
            call_command("verify_domain_references", "--json", stdout=out2)
        self.assertIn("deleted", {x["status"] for x in json.loads(out2.getvalue())["findings"]})

        # The --tenant-id option never includes another tenant's stored rows.
        out3 = StringIO()
        with self.assertRaises(CommandError):
            call_command(
                "verify_domain_references", "--json",
                "--tenant-id", str(self.tenant.id), stdout=out3,
            )
        self.assertTrue(
            all(x["tenant_id"] == str(self.tenant.id) for x in json.loads(out3.getvalue())["findings"])
        )


    def test_empty_reference_audit_is_success_and_invalid_filter_rejected(self):
        import json
        from io import StringIO
        from django.core.management import call_command
        from django.core.management.base import CommandError

        out = StringIO()
        call_command("verify_domain_references", "--json", stdout=out)
        report = json.loads(out.getvalue())
        self.assertTrue(report["ok"])
        self.assertEqual(report["checked"], 0)
        self.assertEqual(report["findings"], [])
        with self.assertRaisesMessage(CommandError, "valid UUID"):
            call_command("verify_domain_references", "--tenant-id", "not-a-uuid")


    def test_document_link_type_coverage_and_tenant_safe_resolution(self):
        """Keep previously accepted link types and allow the two missing v2 types."""
        from django.utils import timezone
        from apps.common.domain_objects import DOMAIN_OBJECT_REGISTRY
        from apps.documents.models import Document
        from apps.documents.serializers import DocumentLinkSerializer
        from apps.evidence.models import Evidence
        from apps.internal_audits.models import AuditEngagement

        for type_code in DOMAIN_OBJECT_REGISTRY:
            with self.subTest(type_code=type_code):
                self.assertTrue(
                    supports_domain_object_type(type_code, capability="document_link")
                )
        for type_code in ("audit_engagement", "evidence"):
            self.assertFalse(supports_domain_object_type(type_code, capability="workflow"))
            self.assertFalse(supports_domain_object_type(type_code, capability="ai_target"))
            self.assertFalse(supports_domain_object_type(type_code, capability="evidence"))

        own_audit = AuditEngagement.objects.create(
            tenant=self.tenant, organization_unit=self.unit,
            title="Authorized audit", lead_auditor=self.user,
        )
        foreign_audit = AuditEngagement.objects.create(
            tenant=self.other_tenant, organization_unit=self.other_unit,
            title="Foreign audit", lead_auditor=self.user,
        )
        own_evidence = Evidence.objects.create(
            tenant=self.tenant, organization_unit=self.unit,
            title="Authorized evidence", owner=self.user,
        )
        foreign_evidence = Evidence.objects.create(
            tenant=self.other_tenant, organization_unit=self.other_unit,
            title="Foreign evidence", owner=self.user,
        )
        document = Document.objects.create(
            tenant=self.tenant, organization_unit=self.unit,
            document_type="policy", code="REGISTRY-DOC",
            title="Link target test", owner=self.user,
        )

        def valid_link(type_code, object_id):
            serializer = DocumentLinkSerializer(
                data={
                    "document": str(document.id), "object_type": type_code,
                    "object_id": str(object_id), "relation_type": "supports",
                },
                context={"tenant": self.tenant},
            )
            return serializer.is_valid()

        for type_code, own, foreign in (
            ("audit_engagement", own_audit, foreign_audit),
            ("evidence", own_evidence, foreign_evidence),
        ):
            with self.subTest(type_code=type_code):
                self.assertEqual(
                    resolve_domain_object(self.tenant, type_code, own.id), own
                )
                self.assertEqual(domain_object_scope(type_code, own), self.unit)
                self.assertIsNone(
                    resolve_domain_object(self.tenant, type_code, foreign.id)
                )
                self.assertTrue(valid_link(type_code, own.id))
                self.assertFalse(valid_link(type_code, foreign.id))

                own.deleted_at = timezone.now()
                own.save(update_fields=["deleted_at"])
                self.assertIsNone(
                    resolve_domain_object(self.tenant, type_code, own.id)
                )
                self.assertFalse(valid_link(type_code, own.id))

        # Existing types/legacy workflow alias remain document-link compatible.
        self.assertTrue(valid_link("risk", self.risk.id))
        self.assertTrue(valid_link("audit", foreign_audit.id) is False)
        self.assertFalse(valid_link("unregistered", self.risk.id))
