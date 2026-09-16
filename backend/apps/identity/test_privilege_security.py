from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.organizations.models import OrganizationUnit
from apps.tenancy.models import Tenant, TenantMembership

from .models import Permission, Role, UserRoleScope
from .services import bootstrap_tenant_rbac

User = get_user_model()


class ScopedPrivilegeEscalationTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="rbac-admin", password="StrongPassword123!")
        self.scoped = User.objects.create_user(username="rbac-scoped", password="StrongPassword123!")
        self.target = User.objects.create_user(username="rbac-target", password="StrongPassword123!")
        self.tenant = Tenant.objects.create(name="RBAC Security", code="rbac-security")
        for user, role_code in (
            (self.admin, "admin"),
            (self.scoped, "member"),
            (self.target, "member"),
        ):
            TenantMembership.objects.create(tenant=self.tenant, user=user, role_code=role_code)
        self.roles = bootstrap_tenant_rbac(self.tenant, admin_user=self.admin)
        self.unit = OrganizationUnit.objects.create(
            tenant=self.tenant,
            unit_type="company",
            code="SCOPED",
            name="Scoped Company",
        )
        privileged_scoped_role = Role.objects.create(
            tenant=self.tenant,
            code="scoped-identity-manager",
            name="Scoped Identity Manager",
        )
        privileged_scoped_role.permissions.set(
            Permission.objects.filter(code__in=["role.manage", "membership.manage"])
        )
        UserRoleScope.objects.create(
            tenant=self.tenant,
            user=self.scoped,
            role=privileged_scoped_role,
            organization_unit=self.unit,
        )
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(self.scoped).access_token}",
            HTTP_X_TENANT_ID=str(self.tenant.id),
        )

    def test_scoped_role_manage_cannot_assign_whole_tenant_role(self):
        response = self.client.post(
            f"/api/v1/tenant-users/{self.target.id}/role-assignments/",
            {"role_code": "viewer", "organization_unit": None},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            UserRoleScope.objects.filter(
                tenant=self.tenant,
                user=self.target,
                role__code="viewer",
                is_active=True,
            ).exists()
        )

    def test_scoped_membership_manage_cannot_disable_tenant_member(self):
        response = self.client.patch(
            f"/api/v1/tenant-users/{self.target.id}/",
            {"membership_active": False},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        membership = TenantMembership.objects.get(tenant=self.tenant, user=self.target)
        self.assertTrue(membership.is_active)
