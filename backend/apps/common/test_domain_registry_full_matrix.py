"""Full real-database contract for every registered domain reference type.

All rows are built with actual Django models; this does not mock the registry or
database. Adding a type without a corresponding fixture must fail the test.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.actions.models import Action
from apps.assessments.models import Assessment, AssessmentItem
from apps.common.domain_objects import (
    DOMAIN_OBJECT_REGISTRY,
    domain_object_display,
    domain_object_scope,
    inspect_domain_reference,
    resolve_domain_object,
    supports_domain_object_type,
)
from apps.context.models import BusinessProcess
from apps.controls.models import Control, ControlImplementation, ControlTest, ControlTestRun
from apps.documents.models import Document
from apps.evidence.models import Evidence
from apps.findings.models import Finding
from apps.frameworks.models import Framework, FrameworkVersion, Requirement
from apps.internal_audits.models import AuditEngagement, Workpaper
from apps.objectives.models import Objective
from apps.organizations.models import OrganizationUnit
from apps.risks.models import Risk, RiskTreatment
from apps.tenancy.models import Tenant, TenantMembership


class AllDomainReferenceTypesContractTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Domain matrix A", code="matrix-a")
        self.foreign_tenant = Tenant.objects.create(
            name="Domain matrix B", code="matrix-b"
        )
        self.user = get_user_model().objects.create_user(
            username="domain-matrix-owner", password="StrongPassword123!"
        )
        for tenant in (self.tenant, self.foreign_tenant):
            TenantMembership.objects.create(
                tenant=tenant, user=self.user, role_code="admin"
            )

    def _actual_records(self, tenant, suffix):
        unit = OrganizationUnit.objects.create(
            tenant=tenant, code=f"UNIT-{suffix}",
            name=f"Security {suffix}", unit_type="department",
        )
        framework = Framework.objects.create(
            tenant=tenant, code=f"fw-{suffix}", name=f"Framework {suffix}",
        )
        version = FrameworkVersion.objects.create(
            framework=framework, version_code="1"
        )
        requirement = Requirement.objects.create(
            framework_version=version, code="REQ-1", title="Requirement"
        )
        control = Control.objects.create(
            tenant=tenant, code=f"ctrl-{suffix}", title="Control"
        )
        impl = ControlImplementation.objects.create(
            tenant=tenant, control=control, organization_unit=unit, owner=self.user
        )
        control_test = ControlTest.objects.create(
            control_implementation=impl, title="Control test",
            method="Inspect evidence", owner=self.user,
        )
        test_run = ControlTestRun.objects.create(
            control_test=control_test, executed_at=timezone.now(),
            result=ControlTestRun.Result.PASS,
        )
        risk = Risk.objects.create(
            tenant=tenant, organization_unit=unit,
            code=f"R-{suffix}", title="Risk", owner=self.user,
        )
        treatment = RiskTreatment.objects.create(
            risk=risk, strategy=RiskTreatment.Strategy.REDUCE, owner=self.user,
        )
        assessment = Assessment.objects.create(
            tenant=tenant, framework_version=version, organization_unit=unit,
            title="Assessment", owner=self.user,
        )
        item = AssessmentItem.objects.create(
            assessment=assessment, requirement=requirement,
            requirement_code_snapshot=requirement.code,
            requirement_title_snapshot=requirement.title,
        )
        engagement = AuditEngagement.objects.create(
            tenant=tenant, organization_unit=unit,
            title="Audit engagement", lead_auditor=self.user,
        )
        workpaper = Workpaper.objects.create(
            engagement=engagement, title="Workpaper", tester=self.user,
        )
        finding = Finding.objects.create(
            tenant=tenant, organization_unit=unit,
            title="Finding", owner=self.user,
        )
        action = Action.objects.create(
            tenant=tenant, organization_unit=unit,
            title="Action", owner=self.user,
        )
        document = Document.objects.create(
            tenant=tenant, organization_unit=unit,
            document_type=Document.Type.POLICY, code=f"D-{suffix}",
            title="Policy", owner=self.user,
        )
        evidence = Evidence.objects.create(
            tenant=tenant, organization_unit=unit,
            title="Evidence", owner=self.user,
        )
        objective = Objective.objects.create(
            tenant=tenant, organization_unit=unit,
            code=f"OBJ-{suffix}", title="Objective", owner=self.user,
        )
        process = BusinessProcess.objects.create(
            tenant=tenant, organization_unit=unit,
            code=f"PROC-{suffix}", name="Process", owner=self.user,
        )

        # Explicit fixture matrix: a new registry type will not pass CI until
        # its real Django model and tenant ownership are exercised here.
        result = {
            "objective": objective,
            "business_process": process,
            "risk": risk,
            "assessment": assessment,
            "assessment_item": item,
            "control_implementation": impl,
            "finding": finding,
            "risk_treatment": treatment,
            "control": control,
            "action": action,
            "requirement": requirement,
            "audit_workpaper": workpaper,
            "control_test_run": test_run,
            "document": document,
            "audit_engagement": engagement,
            "evidence": evidence,
            "audit": engagement,  # Legacy workflow alias remains stable.
        }
        self.assertEqual(set(result), set(DOMAIN_OBJECT_REGISTRY))
        return result, unit

    def test_all_registered_types_resolve_scope_and_cloak_foreign_tenants(self):
        own, unit = self._actual_records(self.tenant, "A")
        foreign, _ = self._actual_records(self.foreign_tenant, "B")

        for type_code, spec in DOMAIN_OBJECT_REGISTRY.items():
            with self.subTest(type_code=type_code):
                self.assertEqual(
                    spec.reference_policy, "capability_gated_scoped_resolution"
                )
                self.assertEqual(
                    spec.deleted_target_policy, "reject_resolution_report_integrity"
                )
                obj = own[type_code]
                self.assertEqual(
                    obj._meta.label_lower,
                    f"{spec.app_label}.{spec.model_name.lower()}",
                )
                self.assertEqual(
                    resolve_domain_object(self.tenant, type_code, obj.pk), obj
                )
                expected_scope = unit if spec.scope_lookup else None
                self.assertEqual(
                    domain_object_scope(type_code, obj), expected_scope
                )
                self.assertEqual(
                    inspect_domain_reference(
                        tenant=self.tenant, type_code=type_code,
                        object_id=obj.pk,
                    ), "ok"
                )
                self.assertIsNone(
                    resolve_domain_object(
                        self.tenant, type_code, foreign[type_code].pk
                    )
                )
                self.assertEqual(
                    inspect_domain_reference(
                        tenant=self.tenant, type_code=type_code,
                        object_id=foreign[type_code].pk,
                    ), "cross_tenant"
                )
                self.assertTrue(
                    domain_object_display(type_code, obj, obj.pk)
                )
                self.assertTrue(supports_domain_object_type(type_code))

    def test_all_registered_types_cloak_soft_deleted_records(self):
        own, _ = self._actual_records(self.tenant, "DELETED")
        # The 'audit' legacy alias points to the same AuditEngagement row.
        for obj in {x.pk: x for x in own.values()}.values():
            obj.__class__.objects.filter(pk=obj.pk).update(
                deleted_at=timezone.now()
            )

        for type_code, obj in own.items():
            with self.subTest(type_code=type_code):
                self.assertIsNone(
                    resolve_domain_object(self.tenant, type_code, obj.pk)
                )
                self.assertEqual(
                    inspect_domain_reference(
                        tenant=self.tenant, type_code=type_code,
                        object_id=obj.pk,
                    ), "deleted"
                )

    def test_only_explicit_global_control_and_requirement_are_shared(self):
        fw = Framework.objects.create(
            code="matrix-global", name="Public globally scoped framework",
            tenant=None,
        )
        version = FrameworkVersion.objects.create(
            framework=fw, version_code="1"
        )
        requirement = Requirement.objects.create(
            framework_version=version, code="GLOBAL-1", title="Global requirement"
        )
        control = Control.objects.create(
            tenant=None, code="matrix-global", title="Global control"
        )
        for type_code, obj in (("control", control), ("requirement", requirement)):
            with self.subTest(type_code=type_code):
                self.assertTrue(DOMAIN_OBJECT_REGISTRY[type_code].allow_global)
                self.assertEqual(
                    resolve_domain_object(self.tenant, type_code, obj.pk), obj
                )
                self.assertEqual(
                    resolve_domain_object(self.foreign_tenant, type_code, obj.pk),
                    obj,
                )
                self.assertIsNone(domain_object_scope(type_code, obj))

        for type_code, spec in DOMAIN_OBJECT_REGISTRY.items():
            if type_code not in {"control", "requirement"}:
                self.assertFalse(spec.allow_global, type_code)
