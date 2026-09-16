from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient, APITestCase

from apps.tenancy.models import Tenant, TenantMembership

User = get_user_model()


class CookieSessionRevocationTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username="cookie-session", password="StrongPassword123!")
        self.tenant = Tenant.objects.create(name="Cookie Session", code="cookie-session")
        TenantMembership.objects.create(tenant=self.tenant, user=self.user, role_code="member")

    @override_settings(AUTH_COOKIE_MODE=True, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
    def test_cookie_logout_revokes_refresh_server_side(self):
        client = APIClient(enforce_csrf_checks=True)
        login = client.post(
            "/api/v1/auth/token",
            {"username": "cookie-session", "password": "StrongPassword123!"},
            format="json",
        )
        self.assertEqual(login.status_code, 200)
        csrf = client.cookies["csrftoken"].value
        refresh_value = client.cookies["grc_refresh"].value
        self.assertEqual(client.cookies["grc_refresh"]["path"], "/api/v1/auth/")

        logout = client.post(
            "/api/v1/auth/logout",
            {},
            format="json",
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(logout.status_code, 200)

        replay_client = APIClient()
        replay = replay_client.post(
            "/api/v1/auth/token/refresh",
            {"refresh": refresh_value},
            format="json",
        )
        self.assertEqual(replay.status_code, 401)
