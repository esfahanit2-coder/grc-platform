import json
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from apps.common.management.commands.pilot_readiness import build_readiness


@override_settings(
    APP_ENV="production",
    DEBUG=False,
    SECURE_SSL_REDIRECT=True,
    SESSION_COOKIE_SECURE=True,
    CSRF_COOKIE_SECURE=True,
    SECRET_KEY="x" * 64,
    CSRF_TRUSTED_ORIGINS=["https://grc.example.internal"],
    OPS_METRICS_TOKEN="metrics-token",
    AI_ENABLED=False,
)
class PilotReadinessReportTests(SimpleTestCase):
    def healthy_dependencies(self):
        return (
            patch(
                "apps.common.management.commands.pilot_readiness.probe_database",
                return_value={"database_version": "PostgreSQL", "pgvector_version": "0.8.0"},
            ),
            patch(
                "apps.common.management.commands.pilot_readiness.probe_redis",
                return_value={"queue_name": "celery", "queue_depth": 0},
            ),
            patch(
                "apps.common.management.commands.pilot_readiness.probe_objectstore",
                return_value={"reachable": True},
            ),
            patch(
                "apps.common.management.commands.pilot_readiness._migration_status",
                return_value={"pending_count": 0},
            ),
        )

    def test_machine_readable_readiness_passes_without_optional_live_ai(self):
        db, redis_probe, objectstore, migration = self.healthy_dependencies()
        with db, redis_probe, objectstore, migration:
            payload = build_readiness()
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["schema"], "grc-pilot-readiness-v2")
        self.assertEqual(
            next(row for row in payload["checks"] if row["name"] == "migrations")["details"]["pending_count"],
            0,
        )

    def test_dependency_failure_emits_error_type_not_exception_text(self):
        with (
            patch(
                "apps.common.management.commands.pilot_readiness.probe_database",
                side_effect=RuntimeError("postgres://user:super-secret@private-db/customer"),
            ),
            patch(
                "apps.common.management.commands.pilot_readiness.probe_redis",
                return_value={"queue_name": "celery", "queue_depth": 0},
            ),
            patch(
                "apps.common.management.commands.pilot_readiness.probe_objectstore",
                return_value={"reachable": True},
            ),
            patch(
                "apps.common.management.commands.pilot_readiness._migration_status",
                return_value={"pending_count": 0},
            ),
        ):
            payload = build_readiness()
        rendered = json.dumps(payload)
        self.assertEqual(payload["status"], "fail")
        self.assertIn("RuntimeError", rendered)
        self.assertNotIn("super-secret", rendered)
        self.assertNotIn("private-db", rendered)

    def test_pending_migration_fails_readiness(self):
        db, redis_probe, objectstore, _ = self.healthy_dependencies()
        with (
            db,
            redis_probe,
            objectstore,
            patch(
                "apps.common.management.commands.pilot_readiness._migration_status",
                return_value={"pending_count": 2},
            ),
        ):
            payload = build_readiness()
        self.assertEqual(payload["status"], "fail")
