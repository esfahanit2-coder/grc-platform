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
