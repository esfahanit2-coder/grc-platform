import json
import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.identity.models import UserRoleScope
from apps.identity.services import bootstrap_tenant_rbac
from apps.tenancy.models import Tenant, TenantMembership


class Command(BaseCommand):
    help = "Idempotently create the first tenant administrator without using a Django superuser shortcut."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-code", required=True)
        parser.add_argument("--tenant-name", required=True)
        parser.add_argument("--admin-username", required=True)
        parser.add_argument("--admin-email", required=True)
        parser.add_argument("--tenant-type", default=Tenant.TenantType.ENTERPRISE, choices=Tenant.TenantType.values)
        parser.add_argument("--language", default="fa")
        parser.add_argument("--timezone", default="Asia/Tehran")
        parser.add_argument("--json", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        password = os.getenv("GRC_BOOTSTRAP_ADMIN_PASSWORD", "")
        if not password:
            raise CommandError("GRC_BOOTSTRAP_ADMIN_PASSWORD must be supplied through the process environment.")

        User = get_user_model()
        username = options["admin_username"].strip()
        email = options["admin_email"].strip().lower()
        tenant_code = options["tenant_code"].strip()
        tenant_name = options["tenant_name"].strip()
        if not username or not email or not tenant_code or not tenant_name:
            raise CommandError("Tenant code/name and admin username/email must be non-empty.")

        existing_tenant = Tenant.objects.filter(code=tenant_code).first()
        tenant_created = existing_tenant is None
        if existing_tenant is None:
            tenant = Tenant.objects.create(
                code=tenant_code,
                name=tenant_name,
                tenant_type=options["tenant_type"],
                default_language=options["language"],
                timezone=options["timezone"],
                status="active",
            )
        else:
            tenant = existing_tenant
            mismatches = []
            expected = {
                "name": tenant_name,
                "tenant_type": options["tenant_type"],
                "default_language": options["language"],
                "timezone": options["timezone"],
            }
            for field, expected_value in expected.items():
                if str(getattr(tenant, field)) != str(expected_value):
                    mismatches.append(field)
            if mismatches:
                raise CommandError(
                    "Existing tenant does not match requested bootstrap identity fields: " + ", ".join(mismatches)
                )
            if tenant.status != "active":
                raise CommandError("Existing tenant is not active; bootstrap will not reactivate it implicitly.")

        user = User.objects.filter(username=username).first()
        user_created = user is None
        if user is None:
            candidate = User(username=username, email=email, is_active=True)
            try:
                validate_password(password, user=candidate)
            except ValidationError as exc:
                raise CommandError("Bootstrap admin password does not satisfy the configured password policy.") from exc
            candidate.set_password(password)
            candidate.save()
            user = candidate
        else:
            if not user.is_active:
                raise CommandError("Existing bootstrap admin user is inactive; bootstrap will not reactivate it implicitly.")
            if (user.email or "").strip().lower() != email:
                raise CommandError("Existing bootstrap admin username belongs to a different email address.")
            existing_membership = TenantMembership.objects.filter(tenant=tenant, user=user).first()
            if existing_membership is None:
                raise CommandError("Existing user is not already a member of the requested tenant; refusing implicit cross-tenant reuse.")
            if existing_membership.deleted_at is not None:
                raise CommandError("Existing tenant membership is soft-deleted; bootstrap will not restore it implicitly.")

        bootstrap_tenant_rbac(tenant, admin_user=user)
        membership = TenantMembership.objects.get(tenant=tenant, user=user)
        if membership.deleted_at is not None:
            raise CommandError("Tenant membership is soft-deleted; bootstrap will not restore it implicitly.")
        if not membership.is_active:
            raise CommandError("Existing tenant membership is inactive; bootstrap will not reactivate it implicitly.")
        if membership.role_code != "admin":
            membership.role_code = "admin"
            membership.save(update_fields=["role_code", "updated_at"])

        assignment = UserRoleScope.objects.filter(
            tenant=tenant,
            user=user,
            role__code="tenant_admin",
            organization_unit__isnull=True,
        ).first()
        if assignment is None or assignment.deleted_at is not None or not assignment.is_active:
            raise CommandError("Tenant administrator RBAC bootstrap did not produce an active, non-deleted whole-tenant assignment.")

        payload = {
            "schema": "grc-datacenter-bootstrap-v1",
            "status": "ok",
            "tenant_id": str(tenant.id),
            "tenant_code": tenant.code,
            "admin_user_id": str(user.pk),
            "admin_username": user.get_username(),
            "tenant_created": tenant_created,
            "user_created": user_created,
            "password_source": "environment",
            "is_django_superuser": bool(user.is_superuser),
            "role": "tenant_admin",
            "scope": "whole_tenant",
        }
        if options["json"]:
            self.stdout.write(json.dumps(payload, sort_keys=True))
        else:
            action = "created" if tenant_created or user_created else "verified"
            self.stdout.write(self.style.SUCCESS(f"Datacenter bootstrap {action}: tenant={tenant.code} admin={user.get_username()} role=tenant_admin"))
