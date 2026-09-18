from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.audit.models import AuditEvent
from apps.identity.models import UserRoleScope
from apps.identity.services import bootstrap_tenant_rbac
from apps.organizations.models import OrganizationUnit
from apps.tenancy.models import Tenant, TenantMembership

from .models import Document, DocumentApproval, DocumentVersion


User = get_user_model()


class DocumentsSmokeTests(TestCase):
    def test_models_import(self):
        self.assertTrue(Document and DocumentVersion)


class DocumentExportSecurityTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="doc-admin", password="StrongPassword123!"
        )
        self.tenant = Tenant.objects.create(
            name="Document Security", code="doc-security"
        )
        TenantMembership.objects.create(
            tenant=self.tenant, user=self.user, role_code="admin"
        )
        bootstrap_tenant_rbac(self.tenant, admin_user=self.user)
        self.unit = OrganizationUnit.objects.create(
            tenant=self.tenant, unit_type="company", code="HQ", name="HQ"
        )
        self.document = Document.objects.create(
            tenant=self.tenant,
            organization_unit=self.unit,
            document_type="policy",
            code="POL-1",
            title="Policy",
            owner=self.user,
        )
        self.version = DocumentVersion.objects.create(
            document=self.document,
            version="1.0",
            content="Controlled content",
            created_by=self.user,
        )
        self.document.current_version = self.version
        self.document.save(update_fields=["current_version", "updated_at"])
        self.auth(self.user)

    def auth(self, user):
        token = str(RefreshToken.for_user(user).access_token)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {token}",
            HTTP_X_TENANT_ID=str(self.tenant.id),
        )

    def test_docx_export_creates_audit_event(self):
        response = self.client.get(
            f"/api/v1/document-versions/{self.version.id}/export/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            AuditEvent.objects.filter(
                tenant=self.tenant,
                action="document.export",
                object_type="document_version",
                object_id=self.version.id,
            ).exists()
        )


class ControlledDocumentLifecycleTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="document-admin", password="StrongPassword123!"
        )
        self.viewer = User.objects.create_user(
            username="document-viewer", password="StrongPassword123!"
        )
        self.approver = User.objects.create_user(
            username="document-approver", password="StrongPassword123!"
        )
        self.approver2 = User.objects.create_user(
            username="document-approver-2", password="StrongPassword123!"
        )
        self.outsider = User.objects.create_user(
            username="document-outsider", password="StrongPassword123!"
        )

        self.tenant = Tenant.objects.create(name="Docs Tenant", code="docs-tenant")
        for user, role_code in [
            (self.admin, "admin"),
            (self.viewer, "member"),
            (self.approver, "member"),
            (self.approver2, "member"),
        ]:
            TenantMembership.objects.create(
                tenant=self.tenant, user=user, role_code=role_code
            )

        self.other_tenant = Tenant.objects.create(
            name="Other Docs", code="other-docs"
        )
        TenantMembership.objects.create(
            tenant=self.other_tenant, user=self.outsider, role_code="member"
        )

        self.roles = bootstrap_tenant_rbac(self.tenant, admin_user=self.admin)
        self.unit = OrganizationUnit.objects.create(
            tenant=self.tenant,
            unit_type="department",
            code="GRC",
            name="GRC",
        )
        UserRoleScope.objects.create(
            tenant=self.tenant,
            user=self.viewer,
            role=self.roles["viewer"],
            organization_unit=self.unit,
        )
        UserRoleScope.objects.create(
            tenant=self.tenant,
            user=self.approver,
            role=self.roles["grc_manager"],
            organization_unit=self.unit,
        )
        UserRoleScope.objects.create(
            tenant=self.tenant,
            user=self.approver2,
            role=self.roles["grc_manager"],
            organization_unit=self.unit,
        )

        self.document = Document.objects.create(
            tenant=self.tenant,
            organization_unit=self.unit,
            document_type=Document.Type.POLICY,
            code="POL-GRC",
            title="GRC Policy",
            owner=self.admin,
        )
        self.version = DocumentVersion.objects.create(
            document=self.document,
            version="1.0",
            content="Draft policy",
            change_summary="Initial draft",
            created_by=self.admin,
        )
        self.document.current_version = self.version
        self.document.save(update_fields=["current_version", "updated_at"])
        self.auth(self.admin)

    def auth(self, user):
        token = str(RefreshToken.for_user(user).access_token)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {token}",
            HTTP_X_TENANT_ID=str(self.tenant.id),
        )

    def assign(self, user=None, order=1):
        return DocumentApproval.objects.create(
            version=self.version,
            approver=user or self.approver,
            approval_order=order,
        )

    def submit(self):
        return self.client.post(
            f"/api/v1/document-versions/{self.version.id}/submit/",
            {},
            format="json",
        )

    def test_read_only_status_fields_cannot_forge_lifecycle(self):
        document_response = self.client.patch(
            f"/api/v1/documents/{self.document.id}/",
            {"status": Document.Status.APPROVED},
            format="json",
        )
        version_response = self.client.patch(
            f"/api/v1/document-versions/{self.version.id}/",
            {"status": DocumentVersion.Status.APPROVED},
            format="json",
        )

        self.assertEqual(document_response.status_code, 200)
        self.assertEqual(version_response.status_code, 200)
        self.document.refresh_from_db()
        self.version.refresh_from_db()
        self.assertEqual(self.document.status, Document.Status.DRAFT)
        self.assertEqual(self.version.status, DocumentVersion.Status.DRAFT)

    def test_viewer_cannot_mutate_version_or_approval(self):
        approval = self.assign()
        self.auth(self.viewer)

        version_response = self.client.patch(
            f"/api/v1/document-versions/{self.version.id}/",
            {"content": "unauthorized"},
            format="json",
        )
        approval_response = self.client.patch(
            f"/api/v1/document-approvals/{approval.id}/",
            {"approval_order": 9},
            format="json",
        )

        self.assertEqual(version_response.status_code, 403)
        self.assertEqual(approval_response.status_code, 403)
        self.version.refresh_from_db()
        approval.refresh_from_db()
        self.assertEqual(self.version.content, "Draft policy")
        self.assertEqual(approval.approval_order, 1)

    def test_cross_tenant_approver_is_rejected(self):
        response = self.client.post(
            "/api/v1/document-approvals/",
            {
                "version": str(self.version.id),
                "approver": self.outsider.id,
                "approval_order": 1,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_workspace_participants_are_permission_aware(self):
        owner_response = self.client.get(
            f"/api/v1/documents/participants/?organization_unit={self.unit.id}&kind=owner"
        )
        approver_response = self.client.get(
            f"/api/v1/documents/participants/?organization_unit={self.unit.id}&kind=approver"
        )

        self.assertEqual(owner_response.status_code, 200)
        self.assertEqual(approver_response.status_code, 200)
        owner_ids = {row["id"] for row in owner_response.data["results"]}
        approver_ids = {row["id"] for row in approver_response.data["results"]}
        self.assertIn(self.viewer.id, owner_ids)
        self.assertIn(self.approver.id, approver_ids)
        self.assertNotIn(self.viewer.id, approver_ids)
        self.assertNotIn(self.outsider.id, owner_ids)

    def test_submit_requires_approver_and_locks_reviewed_version(self):
        missing = self.submit()
        self.assertEqual(missing.status_code, 400)

        self.assign()
        submitted = self.submit()
        self.assertEqual(submitted.status_code, 200)

        edit = self.client.patch(
            f"/api/v1/document-versions/{self.version.id}/",
            {"content": "silent rewrite"},
            format="json",
        )
        self.assertEqual(edit.status_code, 400)
        self.version.refresh_from_db()
        self.document.refresh_from_db()
        self.assertEqual(self.version.status, DocumentVersion.Status.REVIEW)
        self.assertEqual(self.document.status, Document.Status.REVIEW)
        self.assertEqual(self.version.content, "Draft policy")

    def test_decision_requires_review_and_cannot_be_replayed(self):
        approval = self.assign()
        self.auth(self.approver)
        before_review = self.client.post(
            f"/api/v1/document-approvals/{approval.id}/decide/",
            {"decision": DocumentApproval.Decision.APPROVED},
            format="json",
        )
        self.assertEqual(before_review.status_code, 400)

        self.auth(self.admin)
        self.assertEqual(self.submit().status_code, 200)

        self.auth(self.approver)
        first = self.client.post(
            f"/api/v1/document-approvals/{approval.id}/decide/",
            {
                "decision": DocumentApproval.Decision.APPROVED,
                "comment": "Approved",
            },
            format="json",
        )
        second = self.client.post(
            f"/api/v1/document-approvals/{approval.id}/decide/",
            {"decision": DocumentApproval.Decision.APPROVED},
            format="json",
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 400)

        self.version.refresh_from_db()
        self.document.refresh_from_db()
        self.assertEqual(self.version.status, DocumentVersion.Status.APPROVED)
        self.assertEqual(self.document.status, Document.Status.APPROVED)

        self.auth(self.admin)
        delete_decided = self.client.delete(
            f"/api/v1/document-approvals/{approval.id}/"
        )
        self.assertEqual(delete_decided.status_code, 400)

    def test_ordered_approval_stages_are_enforced(self):
        first = self.assign(self.approver, order=1)
        second = self.assign(self.approver2, order=2)
        self.assertEqual(self.submit().status_code, 200)

        self.auth(self.approver2)
        too_early = self.client.post(
            f"/api/v1/document-approvals/{second.id}/decide/",
            {"decision": DocumentApproval.Decision.APPROVED},
            format="json",
        )
        self.assertEqual(too_early.status_code, 400)

        self.auth(self.approver)
        ok = self.client.post(
            f"/api/v1/document-approvals/{first.id}/decide/",
            {"decision": DocumentApproval.Decision.APPROVED},
            format="json",
        )
        self.assertEqual(ok.status_code, 200)

        self.auth(self.approver2)
        final = self.client.post(
            f"/api/v1/document-approvals/{second.id}/decide/",
            {"decision": DocumentApproval.Decision.APPROVED},
            format="json",
        )
        self.assertEqual(final.status_code, 200)
        self.version.refresh_from_db()
        self.assertEqual(self.version.status, DocumentVersion.Status.APPROVED)

    def test_changes_requested_ends_review_without_rewriting_history(self):
        first = self.assign(self.approver, order=1)
        second = self.assign(self.approver2, order=2)
        self.assertEqual(self.submit().status_code, 200)

        self.auth(self.approver)
        response = self.client.post(
            f"/api/v1/document-approvals/{first.id}/decide/",
            {
                "decision": DocumentApproval.Decision.CHANGES,
                "comment": "Revise section 4.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        first.refresh_from_db()
        second.refresh_from_db()
        self.version.refresh_from_db()
        self.document.refresh_from_db()
        self.assertEqual(first.decision, DocumentApproval.Decision.CHANGES)
        self.assertEqual(first.comment, "Revise section 4.")
        self.assertIsNotNone(second.deleted_at)
        self.assertEqual(self.version.status, DocumentVersion.Status.SUPERSEDED)
        self.assertEqual(self.document.status, Document.Status.DRAFT)
        self.assertIsNone(self.document.current_version_id)

    def test_removed_pending_approver_can_be_reassigned_without_duplicate(self):
        approval = self.assign()
        removed = self.client.delete(
            f"/api/v1/document-approvals/{approval.id}/"
        )
        self.assertEqual(removed.status_code, 204)

        reassigned = self.client.post(
            "/api/v1/document-approvals/",
            {
                "version": str(self.version.id),
                "approver": self.approver.id,
                "approval_order": 3,
            },
            format="json",
        )
        self.assertEqual(reassigned.status_code, 201)
        approval.refresh_from_db()
        self.assertIsNone(approval.deleted_at)
        self.assertEqual(approval.approval_order, 3)
        self.assertEqual(
            DocumentApproval.objects.filter(
                version=self.version, approver=self.approver
            ).count(),
            1,
        )


    def test_viewer_cannot_create_or_delete_version(self):
        self.auth(self.viewer)
        create_response = self.client.post(
            "/api/v1/document-versions/",
            {
                "document": str(self.document.id),
                "version": "1.1",
                "content": "Unauthorized draft",
            },
            format="json",
        )
        delete_response = self.client.delete(
            f"/api/v1/document-versions/{self.version.id}/"
        )

        self.assertEqual(create_response.status_code, 403)
        self.assertEqual(delete_response.status_code, 403)
        self.assertTrue(
            DocumentVersion.objects.filter(id=self.version.id, deleted_at__isnull=True).exists()
        )

    def test_viewer_cannot_create_or_delete_approval(self):
        approval = self.assign()
        self.auth(self.viewer)

        create_response = self.client.post(
            "/api/v1/document-approvals/",
            {
                "version": str(self.version.id),
                "approver": self.approver2.id,
                "approval_order": 2,
            },
            format="json",
        )
        delete_response = self.client.delete(
            f"/api/v1/document-approvals/{approval.id}/"
        )

        self.assertEqual(create_response.status_code, 403)
        self.assertEqual(delete_response.status_code, 403)
        approval.refresh_from_db()
        self.assertIsNone(approval.deleted_at)

    def test_manager_can_edit_current_draft(self):
        self.auth(self.approver)
        response = self.client.patch(
            f"/api/v1/document-versions/{self.version.id}/",
            {"content": "Manager revision"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.version.refresh_from_db()
        self.assertEqual(self.version.content, "Manager revision")

    def test_new_version_becomes_explicit_working_draft(self):
        self.version.status = DocumentVersion.Status.APPROVED
        self.version.save(update_fields=["status", "updated_at"])
        self.document.status = Document.Status.APPROVED
        self.document.save(update_fields=["status", "updated_at"])

        response = self.client.post(
            "/api/v1/document-versions/",
            {
                "document": str(self.document.id),
                "version": "1.1",
                "content": "Next controlled revision",
                "change_summary": "Annual review",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.document.refresh_from_db()
        new_version = DocumentVersion.objects.get(id=response.data["id"])
        self.assertEqual(new_version.status, DocumentVersion.Status.DRAFT)
        self.assertEqual(self.document.status, Document.Status.DRAFT)
        self.assertEqual(self.document.current_version_id, new_version.id)

    def test_submit_non_draft_is_rejected(self):
        self.assign()
        self.assertEqual(self.submit().status_code, 200)
        replay_submit = self.submit()
        self.assertEqual(replay_submit.status_code, 400)

    def test_approver_without_permission_is_rejected(self):
        response = self.client.post(
            "/api/v1/document-approvals/",
            {
                "version": str(self.version.id),
                "approver": self.viewer.id,
                "approval_order": 1,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_non_assigned_scoped_approver_cannot_decide(self):
        approval = self.assign(self.approver, order=1)
        self.assertEqual(self.submit().status_code, 200)

        self.auth(self.approver2)
        response = self.client.post(
            f"/api/v1/document-approvals/{approval.id}/decide/",
            {"decision": DocumentApproval.Decision.APPROVED},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        approval.refresh_from_db()
        self.assertEqual(approval.decision, DocumentApproval.Decision.PENDING)

    def test_decided_approval_cannot_be_edited(self):
        approval = self.assign()
        self.assertEqual(self.submit().status_code, 200)

        self.auth(self.approver)
        decided = self.client.post(
            f"/api/v1/document-approvals/{approval.id}/decide/",
            {"decision": DocumentApproval.Decision.APPROVED, "comment": "Approved"},
            format="json",
        )
        self.assertEqual(decided.status_code, 200)

        self.auth(self.admin)
        edited = self.client.patch(
            f"/api/v1/document-approvals/{approval.id}/",
            {"approval_order": 5},
            format="json",
        )
        self.assertEqual(edited.status_code, 400)

    def test_rejected_ends_review_with_explicit_new_draft_required(self):
        first = self.assign(self.approver, order=1)
        second = self.assign(self.approver2, order=2)
        self.assertEqual(self.submit().status_code, 200)

        self.auth(self.approver)
        response = self.client.post(
            f"/api/v1/document-approvals/{first.id}/decide/",
            {
                "decision": DocumentApproval.Decision.REJECTED,
                "comment": "Control objective is not met.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        first.refresh_from_db()
        second.refresh_from_db()
        self.version.refresh_from_db()
        self.document.refresh_from_db()
        self.assertEqual(first.decision, DocumentApproval.Decision.REJECTED)
        self.assertEqual(first.comment, "Control objective is not met.")
        self.assertIsNotNone(second.deleted_at)
        self.assertEqual(self.version.status, DocumentVersion.Status.SUPERSEDED)
        self.assertEqual(self.document.status, Document.Status.DRAFT)
        self.assertIsNone(self.document.current_version_id)

    def test_tenant_isolation_hides_foreign_version(self):
        other_unit = OrganizationUnit.objects.create(
            tenant=self.other_tenant,
            unit_type="department",
            code="OTHER-GRC",
            name="Other GRC",
        )
        other_document = Document.objects.create(
            tenant=self.other_tenant,
            organization_unit=other_unit,
            document_type=Document.Type.POLICY,
            code="OTHER-POL",
            title="Other Policy",
            owner=self.outsider,
        )
        other_version = DocumentVersion.objects.create(
            document=other_document,
            version="1.0",
            content="Foreign tenant content",
            created_by=self.outsider,
        )
        other_document.current_version = other_version
        other_document.save(update_fields=["current_version", "updated_at"])

        get_response = self.client.get(
            f"/api/v1/document-versions/{other_version.id}/"
        )
        patch_response = self.client.patch(
            f"/api/v1/document-versions/{other_version.id}/",
            {"content": "cross-tenant rewrite"},
            format="json",
        )

        self.assertEqual(get_response.status_code, 404)
        self.assertEqual(patch_response.status_code, 404)
        other_version.refresh_from_db()
        self.assertEqual(other_version.content, "Foreign tenant content")
