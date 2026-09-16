import hashlib
import json
import os
from pathlib import Path

from django import get_version as django_version
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone


MANIFEST_SCHEMA = "grc-schema-manifest-v1"
REPORT_SCHEMA = "grc-upgrade-preflight-v1"


def _migration_key(node):
    return f"{node[0]}:{node[1]}"


def migration_state_hash(nodes):
    rendered = "\n".join(sorted(_migration_key(node) for node in nodes)) + "\n"
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def irreversible_operations(plan):
    findings = []
    for migration, backwards in plan:
        for index, operation in enumerate(migration.operations):
            if not bool(getattr(operation, "reversible", True)):
                try:
                    description = operation.describe()
                except Exception:
                    description = operation.__class__.__name__
                findings.append(
                    {
                        "migration": _migration_key((migration.app_label, migration.name)),
                        "direction": "backward" if backwards else "forward",
                        "operation_index": index,
                        "operation": operation.__class__.__name__,
                        "description": str(description)[:300],
                    }
                )
    return findings


def _manifest_nodes(manifest):
    try:
        return {(row["app"], row["name"]) for row in manifest["applied_migrations"]}
    except (KeyError, TypeError) as exc:
        raise CommandError("Schema manifest does not contain valid applied_migrations.") from exc


def _load_manifest(path):
    try:
        manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CommandError(f"Unable to read schema manifest: {exc}") from exc
    if manifest.get("schema_version") != MANIFEST_SCHEMA:
        raise CommandError(
            f"Unsupported schema manifest version: {manifest.get('schema_version')!r}; expected {MANIFEST_SCHEMA!r}."
        )
    expected_hash = manifest.get("migration_state_hash")
    actual_hash = migration_state_hash(_manifest_nodes(manifest))
    if not expected_hash or expected_hash != actual_hash:
        raise CommandError("Schema manifest migration_state_hash is missing or invalid.")
    return manifest


def _write_json(path, payload):
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(rendered, encoding="utf-8")
    try:
        os.chmod(target, 0o600)
    except OSError:
        pass


class Command(BaseCommand):
    help = "Snapshot migration compatibility, preflight upgrades and guard schema rollback."

    def add_arguments(self, parser):
        parser.add_argument("action", choices=["snapshot", "preflight", "restore-check", "rollback"])
        parser.add_argument("--output", help="Output manifest path for snapshot.")
        parser.add_argument("--baseline", help="Baseline schema manifest for preflight/rollback.")
        parser.add_argument("--manifest", help="Backup schema manifest for restore-check.")
        parser.add_argument("--report", help="Optional JSON report path.")
        parser.add_argument("--release-id", default=os.getenv("GRC_RELEASE_VERSION", "unknown"))
        parser.add_argument("--source-commit", default=os.getenv("GRC_SOURCE_COMMIT", "unknown"))
        parser.add_argument(
            "--rollback-strategy",
            choices=["reversible", "restore"],
            help="Required for preflight: reversible schema rollback or backup/restore rollback.",
        )
        parser.add_argument(
            "--backup-verified",
            action="store_true",
            help="Required with --rollback-strategy restore; asserts an approved verified backup exists.",
        )
        parser.add_argument(
            "--confirm",
            help="Rollback requires the exact value ROLLBACK_SCHEMA.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="For rollback, validate and print the plan without changing the database.",
        )

    def handle(self, *args, **options):
        action = options["action"]
        if action == "snapshot":
            return self._snapshot(options)
        if action == "preflight":
            return self._preflight(options)
        if action == "restore-check":
            return self._restore_check(options)
        if action == "rollback":
            return self._rollback(options)
        raise CommandError(f"Unsupported action: {action}")

    def _executor(self):
        return MigrationExecutor(connection)

    def _database_description(self):
        description = {"vendor": connection.vendor}
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT version()")
                description["server_version"] = cursor.fetchone()[0]
        except Exception as exc:
            description["server_version"] = f"unavailable: {type(exc).__name__}"
        return description

    def _snapshot(self, options):
        if not options.get("output"):
            raise CommandError("snapshot requires --output.")
        executor = self._executor()
        leaves = executor.loader.graph.leaf_nodes()
        pending = executor.migration_plan(leaves)
        if pending:
            names = ", ".join(_migration_key((m.app_label, m.name)) for m, _ in pending[:10])
            raise CommandError(
                "Refusing schema snapshot because pending migrations exist. "
                f"Migrate the release first. Pending: {names}"
            )
        applied = set(executor.loader.applied_migrations)
        leaf_targets = [node for node in leaves if node in applied]
        payload = {
            "schema_version": MANIFEST_SCHEMA,
            "generated_at": timezone.now().isoformat(),
            "release_id": options.get("release_id") or "unknown",
            "source_commit": options.get("source_commit") or "unknown",
            "django_version": django_version(),
            "database": self._database_description(),
            "migration_state_hash": migration_state_hash(applied),
            "applied_migrations": [
                {"app": app, "name": name} for app, name in sorted(applied)
            ],
            "leaf_targets": [
                {"app": app, "name": name} for app, name in sorted(leaf_targets)
            ],
        }
        _write_json(options["output"], payload)
        self.stdout.write(
            self.style.SUCCESS(
                f"Schema manifest written: {options['output']} ({len(applied)} applied migrations)"
            )
        )

    def _preflight(self, options):
        baseline_path = options.get("baseline")
        strategy = options.get("rollback_strategy")
        if not baseline_path or not strategy:
            raise CommandError("preflight requires --baseline and --rollback-strategy.")
        if strategy == "restore" and not options.get("backup_verified"):
            raise CommandError(
                "restore rollback strategy requires --backup-verified; do not proceed without an approved verified backup."
            )

        manifest = _load_manifest(baseline_path)
        baseline = _manifest_nodes(manifest)
        executor = self._executor()
        current = set(executor.loader.applied_migrations)
        graph_nodes = set(executor.loader.graph.nodes)
        missing_definitions = sorted(baseline - graph_nodes)
        drift_missing = sorted(baseline - current)
        drift_extra = sorted(current - baseline)
        if missing_definitions:
            raise CommandError(
                "Candidate code is missing migrations required by the baseline: "
                + ", ".join(_migration_key(node) for node in missing_definitions[:20])
            )
        if drift_missing or drift_extra:
            details = []
            if drift_missing:
                details.append("missing=" + ",".join(_migration_key(node) for node in drift_missing[:10]))
            if drift_extra:
                details.append("extra=" + ",".join(_migration_key(node) for node in drift_extra[:10]))
            raise CommandError(
                "Database migration state does not exactly match the baseline manifest; refusing upgrade preflight ("
                + "; ".join(details)
                + ")."
            )

        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        backward_steps = [m for m, backwards in plan if backwards]
        if backward_steps:
            raise CommandError("Upgrade-to-leaf plan unexpectedly contains backward migrations; refusing to continue.")
        irreversible = irreversible_operations(plan)
        report = {
            "schema_version": REPORT_SCHEMA,
            "generated_at": timezone.now().isoformat(),
            "baseline_release_id": manifest.get("release_id", "unknown"),
            "baseline_source_commit": manifest.get("source_commit", "unknown"),
            "baseline_migration_hash": manifest["migration_state_hash"],
            "candidate_release_id": options.get("release_id") or "unknown",
            "candidate_source_commit": options.get("source_commit") or "unknown",
            "rollback_strategy": strategy,
            "backup_verified": bool(options.get("backup_verified")),
            "pending_migrations": [
                _migration_key((migration.app_label, migration.name)) for migration, _ in plan
            ],
            "irreversible_operations": irreversible,
            "schema_rollback_possible": not irreversible,
            "upgrade_allowed": not irreversible or strategy == "restore",
        }
        if options.get("report"):
            _write_json(options["report"], report)
        self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        if irreversible and strategy == "reversible":
            raise CommandError(
                "Candidate includes irreversible migration operations; reversible rollback strategy is not valid. "
                "Use a verified backup/restore strategy after explicit change approval."
            )
        self.stdout.write(self.style.SUCCESS("Upgrade preflight passed."))

    def _restore_check(self, options):
        manifest_path = options.get("manifest")
        if not manifest_path:
            raise CommandError("restore-check requires --manifest.")
        manifest = _load_manifest(manifest_path)
        backup_nodes = _manifest_nodes(manifest)
        executor = self._executor()
        graph_nodes = set(executor.loader.graph.nodes)
        missing = sorted(backup_nodes - graph_nodes)
        if missing:
            raise CommandError(
                "Current application code cannot understand the backup schema because required migration definitions are missing: "
                + ", ".join(_migration_key(node) for node in missing[:20])
            )
        backup_vendor = (manifest.get("database") or {}).get("vendor")
        if backup_vendor and backup_vendor != connection.vendor:
            raise CommandError(
                f"Backup database vendor {backup_vendor!r} does not match current configured vendor {connection.vendor!r}."
            )
        candidate_only = sorted(graph_nodes - backup_nodes)
        report = {
            "schema_version": "grc-restore-compatibility-v1",
            "backup_release_id": manifest.get("release_id", "unknown"),
            "backup_source_commit": manifest.get("source_commit", "unknown"),
            "backup_migration_hash": manifest["migration_state_hash"],
            "candidate_known_migrations_not_in_backup": [
                _migration_key(node) for node in candidate_only
            ],
            "compatible": True,
            "note": "After database restore, run candidate migrations before exposing application writers.",
        }
        if options.get("report"):
            _write_json(options["report"], report)
        self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        self.stdout.write(self.style.SUCCESS("Backup schema compatibility check passed."))

    def _rollback(self, options):
        baseline_path = options.get("baseline")
        if not baseline_path:
            raise CommandError("rollback requires --baseline.")
        if options.get("confirm") != "ROLLBACK_SCHEMA":
            raise CommandError(
                "Schema rollback is destructive. Pass --confirm ROLLBACK_SCHEMA only in an approved maintenance/rehearsal window."
            )
        manifest = _load_manifest(baseline_path)
        baseline = _manifest_nodes(manifest)
        executor = self._executor()
        current = set(executor.loader.applied_migrations)
        graph_nodes = set(executor.loader.graph.nodes)
        missing_definitions = sorted((baseline | current) - graph_nodes)
        if missing_definitions:
            raise CommandError(
                "Rollback cannot be planned because migration definitions are missing: "
                + ", ".join(_migration_key(node) for node in missing_definitions[:20])
            )
        if not baseline.issubset(current):
            missing = sorted(baseline - current)
            raise CommandError(
                "Current database is already behind/incompatible with the baseline: "
                + ", ".join(_migration_key(node) for node in missing[:20])
            )

        baseline_targets = {
            (row["app"], row["name"]) for row in manifest.get("leaf_targets", [])
        }
        baseline_apps = {app for app, _ in baseline}
        current_apps = {app for app, _ in current}
        targets = sorted(baseline_targets)
        for app in sorted(current_apps - baseline_apps):
            targets.append((app, None))
        if not targets and current:
            raise CommandError("Baseline manifest has no rollback leaf targets; refusing schema rollback.")

        plan = executor.migration_plan(targets)
        forward_steps = [m for m, backwards in plan if not backwards]
        if forward_steps:
            raise CommandError("Rollback plan unexpectedly contains forward migrations; refusing to continue.")
        irreversible = irreversible_operations(plan)
        if irreversible:
            names = ", ".join(item["migration"] + "/" + item["operation"] for item in irreversible[:10])
            raise CommandError(
                "Schema rollback is not reversible for all operations. Restore a verified backup instead. Irreversible: "
                + names
            )

        planned_keys = {(migration.app_label, migration.name) for migration, _ in plan}
        delta = current - baseline
        if planned_keys != delta:
            unexpected = sorted(planned_keys ^ delta)
            raise CommandError(
                "Rollback plan does not exactly match migrations applied after the baseline; refusing to continue. Difference: "
                + ", ".join(_migration_key(node) for node in unexpected[:20])
            )

        report = {
            "schema_version": "grc-schema-rollback-v1",
            "baseline_release_id": manifest.get("release_id", "unknown"),
            "rollback_migrations": [
                _migration_key((migration.app_label, migration.name)) for migration, _ in plan
            ],
            "dry_run": bool(options.get("dry_run")),
            "reversible": True,
        }
        if options.get("report"):
            _write_json(options["report"], report)
        self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        if options.get("dry_run"):
            self.stdout.write(self.style.SUCCESS("Schema rollback dry-run passed."))
            return

        executor.migrate(targets, plan=plan)
        verify = self._executor()
        after = set(verify.loader.applied_migrations)
        if after != baseline:
            raise CommandError(
                "Rollback execution completed but resulting migration state does not match the baseline manifest."
            )
        self.stdout.write(self.style.SUCCESS("Schema rollback completed and baseline migration state verified."))
