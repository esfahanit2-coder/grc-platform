import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from apps.common.management.commands.pilot_upgrade_guard import (
    _load_manifest,
    applied_frontier,
    irreversible_operations,
    migration_state_hash,
)


class FakeIrreversibleOperation:
    reversible = False

    def describe(self):
        return "irreversible test operation"


class FakeReversibleOperation:
    reversible = True

    def describe(self):
        return "reversible test operation"


class UpgradeGuardPureTests(TransactionTestCase):
    reset_sequences = False

    def test_migration_state_hash_is_order_independent(self):
        left = {("alpha", "0001_initial"), ("beta", "0002_next")}
        right = list(reversed(sorted(left)))
        self.assertEqual(migration_state_hash(left), migration_state_hash(right))

    def test_irreversible_operation_is_reported(self):
        migration = SimpleNamespace(
            app_label="demo",
            name="0002_irreversible",
            operations=[FakeReversibleOperation(), FakeIrreversibleOperation()],
        )
        findings = irreversible_operations([(migration, False)])
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["migration"], "demo:0002_irreversible")
        self.assertEqual(findings[0]["direction"], "forward")
        self.assertEqual(findings[0]["operation"], "FakeIrreversibleOperation")

    def test_applied_frontier_matches_current_graph_frontier(self):
        executor = MigrationExecutor(connection)
        applied = set(executor.loader.applied_migrations)
        frontier = applied_frontier(executor.loader.graph, applied)
        self.assertTrue(frontier)
        for node in frontier:
            graph_node = executor.loader.graph.node_map[node]
            self.assertFalse(any(child.key in applied for child in graph_node.children))


class UpgradeGuardCommandTests(TransactionTestCase):
    reset_sequences = False

    def _snapshot(self, directory, name="schema.json"):
        path = Path(directory) / name
        call_command(
            "pilot_upgrade_guard",
            "snapshot",
            output=str(path),
            release_id="test-release",
            source_commit="test-commit",
            verbosity=0,
        )
        return path

    def test_snapshot_preflight_and_restore_check_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest_path = self._snapshot(directory)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["schema_version"], "grc-schema-manifest-v1")
            self.assertTrue(manifest["fully_migrated_to_current_code"])
            self.assertFalse(manifest["pending_snapshot_explicitly_allowed"])
            self.assertTrue(manifest["leaf_targets"])

            call_command(
                "pilot_upgrade_guard",
                "preflight",
                baseline=str(manifest_path),
                rollback_strategy="reversible",
                release_id="candidate",
                source_commit="candidate-commit",
                verbosity=0,
            )
            call_command(
                "pilot_upgrade_guard",
                "restore-check",
                manifest=str(manifest_path),
                verbosity=0,
            )

    def test_tampered_manifest_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest_path = self._snapshot(directory)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["applied_migrations"] = manifest["applied_migrations"][:-1]
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(CommandError, "migration_state_hash"):
                _load_manifest(manifest_path)

    def test_restore_check_rejects_unknown_migration_definition(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest_path = self._snapshot(directory)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["applied_migrations"].append({"app": "missing_app", "name": "9999_absent"})
            nodes = {(row["app"], row["name"]) for row in manifest["applied_migrations"]}
            manifest["migration_state_hash"] = migration_state_hash(nodes)
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(CommandError, "required migration definitions are missing"):
                call_command(
                    "pilot_upgrade_guard",
                    "restore-check",
                    manifest=str(manifest_path),
                    verbosity=0,
                )

    def test_restore_strategy_requires_verified_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest_path = self._snapshot(directory)
            with self.assertRaisesRegex(CommandError, "backup-verified"):
                call_command(
                    "pilot_upgrade_guard",
                    "preflight",
                    baseline=str(manifest_path),
                    rollback_strategy="restore",
                    verbosity=0,
                )

    def test_rollback_requires_explicit_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest_path = self._snapshot(directory)
            with self.assertRaisesRegex(CommandError, "ROLLBACK_SCHEMA"):
                call_command(
                    "pilot_upgrade_guard",
                    "rollback",
                    baseline=str(manifest_path),
                    dry_run=True,
                    verbosity=0,
                )

    def test_restore_check_rejects_pending_baseline_capture_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest_path = self._snapshot(directory)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["fully_migrated_to_current_code"] = False
            manifest["pending_snapshot_explicitly_allowed"] = True
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(CommandError, "not valid as a release backup"):
                call_command(
                    "pilot_upgrade_guard",
                    "restore-check",
                    manifest=str(manifest_path),
                    verbosity=0,
                )
