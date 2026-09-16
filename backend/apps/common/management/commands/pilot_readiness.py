import os

import boto3
import redis
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from apps.ai_gateway.models import AIProviderConfig
from apps.ai_gateway.providers import provider_for


class Command(BaseCommand):
    help = "Run non-destructive pilot readiness checks for core dependencies and optional AI."

    def add_arguments(self, parser):
        parser.add_argument(
            "--ai-provider-id",
            help="Optional AIProviderConfig UUID to smoke-test generation and embeddings.",
        )
        parser.add_argument(
            "--skip-objectstore",
            action="store_true",
            help="Skip S3/object-storage connectivity check (not valid for final pilot acceptance).",
        )

    def handle(self, *args, **options):
        failures = []
        warnings = []

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT version()")
                db_version = cursor.fetchone()[0]
                cursor.execute("SELECT extversion FROM pg_extension WHERE extname='vector'")
                row = cursor.fetchone()
            self.stdout.write(f"Database: {db_version}")
            if row:
                self.stdout.write(self.style.SUCCESS(f"pgvector: {row[0]}"))
            else:
                failures.append("pgvector extension is not enabled")
        except Exception as exc:
            failures.append(f"database readiness failed: {exc}")

        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            redis.Redis.from_url(redis_url, socket_timeout=3, socket_connect_timeout=3).ping()
            self.stdout.write(self.style.SUCCESS("Redis: reachable"))
        except Exception as exc:
            failures.append(f"Redis readiness failed: {exc}")

        if not options["skip_objectstore"]:
            try:
                client = boto3.client(
                    "s3",
                    endpoint_url=settings.S3_ENDPOINT_URL or None,
                    aws_access_key_id=settings.S3_ACCESS_KEY or None,
                    aws_secret_access_key=settings.S3_SECRET_KEY or None,
                    region_name=settings.S3_REGION,
                    use_ssl=settings.S3_USE_SSL,
                )
                client.head_bucket(Bucket=settings.S3_BUCKET)
                self.stdout.write(self.style.SUCCESS(f"Object storage: bucket {settings.S3_BUCKET!r} reachable"))
            except Exception as exc:
                failures.append(f"object-storage readiness failed: {exc}")

        if getattr(settings, "APP_ENV", "development") == "production":
            if settings.DEBUG:
                failures.append("DEBUG must be disabled in production")
            if not settings.SECURE_SSL_REDIRECT:
                warnings.append("SECURE_SSL_REDIRECT is disabled")
            if not settings.SESSION_COOKIE_SECURE or not settings.CSRF_COOKIE_SECURE:
                failures.append("Secure cookies are required")
            if settings.SECRET_KEY in {"unsafe-dev-key", "change-me-in-production"}:
                failures.append("Production secret key is not configured")
            if not settings.CSRF_TRUSTED_ORIGINS:
                failures.append("CSRF_TRUSTED_ORIGINS is empty in production")

        provider_id = options.get("ai_provider_id")
        if provider_id:
            if not getattr(settings, "AI_ENABLED", True):
                failures.append("AI smoke test requested but AI_ENABLED is false")
            else:
                try:
                    provider_cfg = AIProviderConfig.objects.filter(
                        id=provider_id,
                        is_active=True,
                        deleted_at__isnull=True,
                    ).first()
                    if not provider_cfg:
                        raise CommandError("Requested active AI provider was not found.")
                    provider = provider_for(provider_cfg)
                    response = provider.generate(
                        [{"role": "user", "content": "Reply with the single word OK."}],
                        temperature=0,
                    )
                    if not response.text.strip():
                        raise CommandError("AI provider returned an empty generation.")
                    vectors = provider.embed(["pilot readiness"])
                    if not vectors or not vectors[0]:
                        raise CommandError("AI provider returned no embedding vector.")
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"AI provider: {provider_cfg.provider_type}/{provider_cfg.name} generation OK; "
                            f"embedding dimensions={len(vectors[0])}"
                        )
                    )
                except Exception as exc:
                    failures.append(f"AI provider readiness failed: {exc}")
        elif not getattr(settings, "AI_ENABLED", True):
            self.stdout.write(self.style.WARNING("AI: globally disabled by configuration"))
        else:
            warnings.append("AI live smoke test not run; pass --ai-provider-id after configuring a local provider")

        for item in warnings:
            self.stdout.write(self.style.WARNING("WARN: " + item))
        if failures:
            for item in failures:
                self.stdout.write(self.style.ERROR("FAIL: " + item))
            raise CommandError("Pilot readiness checks failed")
        self.stdout.write(self.style.SUCCESS("Pilot readiness checks passed"))
