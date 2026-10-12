from datetime import timedelta
from decimal import Decimal
from io import BytesIO

from docx import Document
from openpyxl import load_workbook

from apps.reporting.formal_reports import table_html

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.actions.models import Action
from apps.assessments.models import Assessment, AssessmentItem
from apps.frameworks.models import Framework, FrameworkVersion, Requirement
from apps.identity.models import UserRoleScope
from apps.identity.services import bootstrap_tenant_rbac
from apps.organizations.models import OrganizationUnit
from apps.tenancy.models import Tenant, TenantMembership


class FormalReportingCenterTests(APITestCase):
    def setUp(self):
        User=get_user_model()
        self.admin=User.objects.create_user(username="report-center-admin",password="StrongPassword123!")
        self.viewer=User.objects.create_user(username="report-center-viewer",password="StrongPassword123!")
        self.tenant=Tenant.objects.create(name="Formal Reports",code="formal-reports")
        TenantMembership.objects.create(tenant=self.tenant,user=self.admin,role_code="admin")
        TenantMembership.objects.create(tenant=self.tenant,user=self.viewer,role_code="viewer")
        roles=bootstrap_tenant_rbac(self.tenant,admin_user=self.admin)
        self.unit=OrganizationUnit.objects.create(tenant=self.tenant,unit_type=OrganizationUnit.UnitType.COMPANY,code="HQ",name="HQ")
        self.other=OrganizationUnit.objects.create(tenant=self.tenant,unit_type=OrganizationUnit.UnitType.BUSINESS_UNIT,code="OPS",name="OPS")
        UserRoleScope.objects.create(user=self.viewer,tenant=self.tenant,role=roles["viewer"],organization_unit=self.unit)
        framework=Framework.objects.create(tenant=self.tenant,code="iso-test",name="ISO Test",status=Framework.Status.ACTIVE)
        version=FrameworkVersion.objects.create(framework=framework,version_code="1",status=FrameworkVersion.Status.ACTIVE)
        req=Requirement.objects.create(framework_version=version,code="A.1",title="Requirement")
        self.assessment=Assessment.objects.create(tenant=self.tenant,framework_version=version,organization_unit=self.unit,title="HQ Assessment",owner=self.admin,status=Assessment.Status.IN_PROGRESS,overall_score=Decimal("80"))
        AssessmentItem.objects.create(assessment=self.assessment,requirement=req,requirement_code_snapshot="A.1",requirement_title_snapshot="Requirement",applicability=AssessmentItem.Applicability.APPLICABLE,status=AssessmentItem.Status.COMPLIANT,score=Decimal("100"))
        self.foreign_assessment=Assessment.objects.create(tenant=self.tenant,framework_version=version,organization_unit=self.other,title="OPS Assessment",owner=self.admin)
        Action.objects.create(tenant=self.tenant,organization_unit=self.unit,title="HQ Action",owner=self.admin,status=Action.Status.TODO,due_date=timezone.localdate()+timedelta(days=2))
        Action.objects.create(tenant=self.tenant,organization_unit=self.other,title="OPS Action",owner=self.admin,status=Action.Status.TODO,due_date=timezone.localdate()+timedelta(days=2))

    def auth(self,user):
        token=str(RefreshToken.for_user(user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}",HTTP_X_TENANT_ID=str(self.tenant.id))

    def test_catalog_requires_report_view(self):
        self.auth(self.viewer)
        response=self.client.get("/api/v1/reports/catalog/")
        self.assertEqual(response.status_code,200)
        self.assertIn("soa",response.json()["reports"])

    def test_scoped_viewer_sees_only_own_actions(self):
        self.auth(self.viewer)
        response=self.client.get("/api/v1/reports/preview/?type=actions")
        self.assertEqual(response.status_code,200)
        rows=response.json()["rows"]
        self.assertEqual([row[0] for row in rows],["HQ Action"])

    def test_scoped_viewer_cannot_target_other_unit(self):
        self.auth(self.viewer)
        response=self.client.get(f"/api/v1/reports/preview/?type=actions&organization_unit={self.other.id}")
        self.assertEqual(response.status_code,400)

    def test_viewer_cannot_export(self):
        self.auth(self.viewer)
        response=self.client.get("/api/v1/reports/export/?type=actions&format=csv")
        self.assertEqual(response.status_code,403)

    def test_admin_exports_csv(self):
        self.auth(self.admin)
        response=self.client.get("/api/v1/reports/export/?type=actions&format=csv")
        self.assertEqual(response.status_code,200)
        self.assertIn("text/csv",response["Content-Type"])
        self.assertIn("attachment",response["Content-Disposition"])

    def test_soa_requires_assessment_and_respects_scope(self):
        self.auth(self.viewer)
        missing=self.client.get("/api/v1/reports/preview/?type=soa")
        self.assertEqual(missing.status_code,400)
        ok=self.client.get(f"/api/v1/reports/preview/?type=soa&assessment={self.assessment.id}")
        self.assertEqual(ok.status_code,200)
        denied=self.client.get(f"/api/v1/reports/preview/?type=soa&assessment={self.foreign_assessment.id}")
        self.assertEqual(denied.status_code,400)

    def test_soa_draft_is_not_a_formal_attestation(self):
        self.auth(self.viewer)
        catalog=self.client.get("/api/v1/reports/catalog/")
        self.assertEqual(catalog.status_code, 200)
        self.assertFalse(catalog.json()["reports"]["soa"]["is_formal_statement_of_applicability"])
        preview=self.client.get(f"/api/v1/reports/preview/?type=soa&assessment={self.assessment.id}")
        self.assertEqual(preview.status_code, 200)
        payload=preview.json()
        self.assertEqual(payload["report_kind"], "assessment_applicability_worksheet")
        self.assertFalse(payload["is_formal_statement_of_applicability"])
        self.assertEqual(payload["summary"]["report_status"], "draft_unapproved")
        self.assertFalse(payload["summary"]["is_formal_statement_of_applicability"])
        self.assertIn("NOT APPROVED", payload["title"])
        self.assertIn("NOT AN APPROVED SoA", payload["notice"])
        self.assertIn("DRAFT", payload["columns"][-1])
        self.assertEqual(payload["rows"][0][-1], "DRAFT — not approved")
        self.assertGreaterEqual(len(payload["summary"]["pending_prerequisites"]), 3)

    def test_soa_csv_xlsx_docx_and_html_exports_carry_draft_warning(self):
        self.auth(self.admin)
        url=f"/api/v1/reports/export/?type=soa&assessment={self.assessment.id}"
        csv_response=self.client.get(url+"&format=csv")
        self.assertEqual(csv_response.status_code, 200)
        csv_content=csv_response.content.decode("utf-8-sig")
        self.assertIn("Attestation: DRAFT, NOT APPROVED", csv_content)
        self.assertIn("DRAFT — not approved", csv_content)

        xlsx_response=self.client.get(url+"&format=xlsx")
        self.assertEqual(xlsx_response.status_code, 200)
        workbook=load_workbook(BytesIO(xlsx_response.content), read_only=True)
        try:
            sheet=workbook.active
            self.assertEqual(sheet.cell(row=1, column=8).value, "Attestation: DRAFT, NOT APPROVED")
            self.assertEqual(sheet.cell(row=2, column=8).value, "DRAFT — not approved")
        finally:
            workbook.close()

        docx_response=self.client.get(url+"&format=docx")
        self.assertEqual(docx_response.status_code, 200)
        document=Document(BytesIO(docx_response.content))
        text=" ".join(p.text for p in document.paragraphs)
        self.assertIn("NOT APPROVED", text)
        self.assertIn("NOT AN APPROVED SoA", text)

        # PDF export uses the same HTML builder; assert the explicit notice is present.
        self.assertIn("NOT APPROVED", table_html({
            "title": "Draft (NOT APPROVED)",
            "notice": "DRAFT / NOT AN APPROVED SoA",
            "columns": ["Control"], "rows": [["A.5.1"]],
        }))

    def test_soa_blocks_foreign_tenant_assessment_even_for_tenant_admin(self):
        foreign_tenant=Tenant.objects.create(name="Other Org", code="other-org-report")
        foreign_framework=Framework.objects.create(tenant=foreign_tenant, code="unrelated", name="Unrelated")
        foreign_version=FrameworkVersion.objects.create(framework=foreign_framework, version_code="1")
        foreign_assessment=Assessment.objects.create(
            tenant=foreign_tenant, framework_version=foreign_version,
            title="Do not disclose", owner=self.admin,
        )
        self.auth(self.admin)
        response=self.client.get(f"/api/v1/reports/preview/?type=soa&assessment={foreign_assessment.id}")
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("Do not disclose", str(response.content))

    def test_invalid_date_range_rejected(self):
        self.auth(self.admin)
        response=self.client.get("/api/v1/reports/preview/?type=actions&from_date=2026-09-20&to_date=2026-09-10")
        self.assertEqual(response.status_code,400)

    def test_unsupported_format_rejected(self):
        self.auth(self.admin)
        response=self.client.get("/api/v1/reports/export/?type=actions&format=docx")
        self.assertEqual(response.status_code,400)
