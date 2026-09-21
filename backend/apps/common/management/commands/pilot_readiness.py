import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from apps.ai_gateway.models import AIProviderConfig
from apps.ai_gateway.providers import provider_for
from apps.common.operations import probe_database, probe_objectstore, probe_redis


SCHEMA = "grc-pilot-readiness-v2"


def _row(name, status, **details):
    payload = {"name": name, "status": status}
    if details:
        payload["details"] = details
    return payload


def _migration_status():
    executor = MigrationExecutor(connection)
    targets = executor.loader.graph.leaf_nodes()
    plan = executor.migration_plan(targets)
    return {"pending_count": len(plan)}


def build_readiness(*, ai_provider_id=None, skip_objectstore=False):
    checks = []

    try:
        database = probe_database(require_pgvector=True)
        checks.append(
            _row(
                "database",
                "pass",
                database_version=database["database_version"],
                pgvector_version=database["pgvector_version"],
            )
        )
    except Exception as exc:
        checks.append(_row("database", "fail", error_type=type(exc).__name__))

    try:
        redis_status = probe_redis()
        checks.append(
            _row(
                "redis",
                "pass",
                queue_name=redis_status.get("queue_name"),
                queue_depth=redis_status.get("queue_depth"),
            )
        )
    except Exception as exc:
        checks.append(_row("redis", "fail", error_type=type(exc).__name__))

    if skip_objectstore:
        checks.append(_row("object_storage", "warning", reason="explicitly_skipped"))
    else:
        try:
            probe_objectstore()
            checks.append(_row("object_storage", "pass"))
        except Exception as exc:
            checks.append(_row("object_storage", "fail", error_type=type(exc).__name__))

    try:
        migration = _migration_status()
        checks.append(
            _row(
                "migrations",
                "pass" if migration["pending_count"] == 0 else "fail",
                pending_count=migration["pending_count"],
            )
        )
    except Exception as exc:
        checks.append(_row("migrations", "fail", error_type=type(exc).__name__))

    if getattr(settings, "APP_ENV", "development") == "production":
        security_checks = {
            "debug_disabled": not settings.DEBUG,
            "secure_ssl_redirect": bool(settings.SECURE_SSL_REDIRECT),
            "secure_cookies": bool(settings.SESSION_COOKIE_SECURE and settings.CSRF_COOKIE_SECURE),
            "secret_key_configured": settings.SECRET_KEY not in {"unsafe-dev-key", "change-me-in-production"},
            "csrf_origins_configured": bool(settings.CSRF_TRUSTED_ORIGINS),
            "metrics_token_configured": bool(getattr(settings, "OPS_METRICS_TOKEN", "")),
        }
        for name, passed in security_checks.items():
            checks.append(_row(f"security:{name}", "pass" if passed else "fail"))

    if ai_provider_id:
        if not getattr(settings, "AI_ENABLED", True):
            checks.append(_row("ai_provider", "fail", reason="ai_disabled"))
        else:
            try:
                provider_cfg = AIProviderConfig.objects.filter(
                    id=ai_provider_id,
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
                checks.append(
                    _row(
                        "ai_provider",
                        "pass",
                        provider_type=provider_cfg.provider_type,
                        embedding_dimensions=len(vectors[0]),
                    )
                )
            except Exception as exc:
                checks.append(_row("ai_provider", "fail", error_type=type(exc).__name__))
    elif not getattr(settings, "AI_ENABLED", True):
        checks.append(_row("ai_provider", "pass", reason="globally_disabled"))
    else:
        checks.append(_row("ai_provider", "warning", reason="live_smoke_not_requested"))

    failed = [item for item in checks if item["status"] == "fail"]
    warnings = [item for item in checks if item["status"] == "warning"]
    return {
        "schema": SCHEMA,
        "status": "fail" if failed else ("warning" if warnings else "pass"),
        "checks": checks,
    }


class Command(BaseCommand):
    help = "Run non-destructive deployment readiness checks for core dependencies and optional AI."

    def add_arguments(self, parser):
        parser.add_argument(
            "--ai-provider-id",
            help="Optional AIProviderConfig UUID to smoke-test generation and embeddings.",
        )
        parser.add_argument(
            "--skip-objectstore",
            action="store_true",
            help="Skip S3/object-storage connectivity check (not valid for final deployment acceptance).",
        )
        parser.add_argument("--json", action="store_true", help="Emit one machine-readable JSON object.")

    def handle(self, *args, **options):
        payload = build_readiness(
            ai_provider_id=options.get("ai_provider_id"),
            skip_objectstore=options["skip_objectstore"],
        )
        if options["json"]:
            self.stdout.write(json.dumps(payload, default=str, sort_keys=True))
        else:
            for item in payload["checks"]:
                label = item["name"]
                status = item["status"].upper()
                if item["status"] == "pass":
                    self.stdout.write(self.style.SUCCESS(f"PASS: {label}"))
                elif item["status"] == "warning":
                    self.stdout.write(self.style.WARNING(f"WARN: {label}"))
                else:
                    self.stdout.write(self.style.ERROR(f"FAIL: {label}"))
            self.stdout.write(f"Readiness result: {payload['status']}")
        if payload["status"] == "fail":
            raise CommandError("Deployment readiness checks failed")
