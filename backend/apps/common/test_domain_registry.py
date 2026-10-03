import json
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from apps.actions.models import Action
from apps.common.domain_registry import (
    domain_object_display,
    domain_object_scope,
    inspect_domain_reference,
    registered_type_codes,
    resolve_domain_object,
    supports_domain_object,
)
from apps.findings.models import Finding
from apps.organizations.models import OrganizationUnit
from apps.risks.models import Risk, RiskCategory, RiskTreatment
from apps.tenancy.models import Tenant


User = get_user_model()


class DomainObjectRegistryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="registry-owner", password="StrongPassword123!"
        )
        self.tenant = Tenant.objects.create(name="Registry A", code="registry-a")
        self.other_tenant = Tenant.objects.create(
            name="Registry B", code="registry-b"
        )
        self.unit = OrganizationUnit.objects.create(
            tenant=self.tenant,
            unit_type="department",
            code="GRC",
            name="GRC",
        )
        self.other_unit = OrganizationUnit.objects.create(
            tenant=self.other_tenant,
            unit_type="department",
            code="OTHER",
            name="Other",
        )
        self.category = RiskCategory.objects.create(
            tenant=self.tenant, code="ops", name="Operational"
        )
        self.other_category = RiskCategory.objects.create(
            tenant=self.other_tenant, code="ops", name="Operational"
        )
        self.risk = Risk.objects.create(
            tenant=self.tenant,
            organization_unit=self.unit,
            category=self.category,
            code="R-1",
            title="Registry risk",
            owner=self.user,
        )
        self.other_risk = Risk.objects.create(
            tenant=self.other_tenant,
            organization_unit=self.other_unit,
            category=self.other_category,
            code="R-2",
            title="Other tenant risk",
            owner=self.user,
        )

    def test_same_tenant_resolves_and_foreign_tenant_is_cloaked(self):
        resolved = resolve_domain_object(
            tenant=self.tenant,
            type_code="risk",
            object_id=self.risk.id,
            capability="workflow",
        )
        foreign = resolve_domain_object(
            tenant=self.tenant,
            type_code="risk",
            object_id=self.other_risk.id,
            capability="workflow",
        )

        self.assertEqual(resolved, self.risk)
        self.assertIsNone(foreign)
        self.assertEqual(domain_object_scope(resolved, "risk"), self.unit)
        self.assertEqual(domain_object_display(resolved, "risk"), "R-1 · Registry risk")

    def test_capabilities_are_not_interchangeable(self):
        treatment = RiskTreatment.objects.create(
            risk=self.risk,
            strategy=RiskTreatment.Strategy.REDUCE,
            owner=self.user,
        )

        self.assertTrue(supports_domain_object("risk_treatment", capability="action_source"))
        self.assertFalse(supports_domain_object("risk_treatment", capability="workflow"))
        self.assertIsNotNone(
            resolve_domain_object(
                tenant=self.tenant,
                type_code="risk_treatment",
                object_id=treatment.id,
                capability="action_source",
            )
        )
        self.assertIsNone(
            resolve_domain_object(
                tenant=self.tenant,
                type_code="risk_treatment",
                object_id=treatment.id,
                capability="workflow",
            )
        )
        self.assertIn("risk", registered_type_codes(capability="evidence_link"))

    def test_deleted_target_is_hidden_but_integrity_inspection_explains_it(self):
        self.risk.deleted_at = timezone.now()
        self.risk.save(update_fields=["deleted_at", "updated_at"])

        self.assertIsNone(
            resolve_domain_object(
                tenant=self.tenant,
                type_code="risk",
                object_id=self.risk.id,
                capability="evidence_link",
            )
        )
        result = inspect_domain_reference(
            tenant=self.tenant,
            type_code="risk",
            object_id=self.risk.id,
            capability="evidence_link",
        )
        self.assertEqual(result["status"], "deleted")

    def test_integrity_inspection_distinguishes_cross_tenant(self):
        result = inspect_domain_reference(
            tenant=self.tenant,
            type_code="risk",
            object_id=self.other_risk.id,
            capability="workflow",
        )
        self.assertEqual(result["status"], "cross_tenant")

    def test_unknown_and_unsupported_types_are_explicit_for_integrity_tools(self):
        unknown = inspect_domain_reference(
            tenant=self.tenant,
            type_code="does_not_exist",
            object_id=self.risk.id,
            capability="workflow",
        )
        unsupported = inspect_domain_reference(
            tenant=self.tenant,
            type_code="risk_treatment",
            object_id=self.risk.id,
            capability="workflow",
        )
        self.assertEqual(unknown["status"], "unknown_type")
        self.assertEqual(unsupported["status"], "unsupported_capability")


class VerifyDomainReferencesCommandTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="registry-checker", password="StrongPassword123!"
        )
        self.tenant = Tenant.objects.create(name="Checker A", code="checker-a")
        self.other_tenant = Tenant.objects.create(
            name="Checker B", code="checker-b"
        )
        self.unit = OrganizationUnit.objects.create(
            tenant=self.tenant,
            unit_type="department",
            code="A",
            name="A",
        )
        self.other_unit = OrganizationUnit.objects.create(
            tenant=self.other_tenant,
            unit_type="department",
            code="B",
            name="B",
        )
        self.finding = Finding.objects.create(
            tenant=self.other_tenant,
            organization_unit=self.other_unit,
            finding_type="observation",
            title="Foreign finding",
            description="Cross-tenant test fixture",
            severity="low",
            owner=self.user,
        )

    def test_command_reports_cross_tenant_reference_without_mutation(self):
        action = Action.objects.create(
            tenant=self.tenant,
            organization_unit=self.unit,
            title="Broken source reference",
            owner=self.user,
            source_type="finding",
            source_id=self.finding.id,
        )
        out = StringIO()

        with self.assertRaises(CommandError):
            call_command("verify_domain_references", "--json", stdout=out)

        payload = json.loads(out.getvalue().strip())
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["findings"][0]["source"], "action_source")
        self.assertEqual(payload["findings"][0]["row_id"], str(action.id))
        self.assertEqual(payload["findings"][0]["status"], "cross_tenant")

        action.refresh_from_db()
        self.assertEqual(action.source_id, self.finding.id)

    def test_command_succeeds_for_empty_reference_set(self):
        out = StringIO()
        call_command("verify_domain_references", "--json", stdout=out)
        payload = json.loads(out.getvalue().strip())
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["checked"], 0)
        self.assertEqual(payload["findings"], [])
