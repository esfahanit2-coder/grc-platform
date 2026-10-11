import hashlib
import io
import json
import tempfile
import zipfile
from pathlib import Path

from botocore.exceptions import ClientError
from unittest.mock import patch

from django.core.management.base import CommandError
from django.test import SimpleTestCase

from apps.common.management.commands.pilot_objectstore_archive import Command


class FakeS3Client:
    def __init__(self, objects=None):
        self.objects = dict(objects or {})
        self.content_types = {key: "application/octet-stream" for key in self.objects}
        self.metadata = {key: {} for key in self.objects}

    def list_objects_v2(self, Bucket, **kwargs):
        return {
            "IsTruncated": False,
            "Contents": [{"Key": key, "Size": len(value)} for key, value in sorted(self.objects.items())],
        }

    def get_object(self, Bucket, Key):
        return {
            "Body": io.BytesIO(self.objects[Key]),
            "ContentType": self.content_types.get(Key, "application/octet-stream"),
            "Metadata": self.metadata.get(Key, {}),
        }

    def upload_fileobj(self, fileobj, bucket, key, ExtraArgs=None):
        self.objects[key] = fileobj.read()
        extra = ExtraArgs or {}
        self.content_types[key] = extra.get("ContentType", "application/octet-stream")
        self.metadata[key] = extra.get("Metadata", {})

    def delete_objects(self, Bucket, Delete):
        for row in Delete.get("Objects") or []:
            self.objects.pop(row["Key"], None)


class PilotObjectStoreArchiveTests(SimpleTestCase):
    def test_export_and_replace_restore_round_trip(self):
        source = FakeS3Client(
            {
                "tenant/a/evidence/one.txt": b"alpha",
                "tenant/a/evidence/two.bin": b"\x00\x01\x02",
            }
        )
        source.content_types["tenant/a/evidence/one.txt"] = "text/plain"
        source.metadata["tenant/a/evidence/one.txt"] = {"classification": "internal"}

        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "objects.zip"
            Command()._export(source, "grc-evidence", archive_path)

            with zipfile.ZipFile(archive_path) as archive:
                manifest = json.loads(archive.read("manifest.json"))
            self.assertEqual(manifest["schema_version"], 1)
            self.assertEqual(manifest["object_count"], 2)
            self.assertTrue(all(len(row["sha256"]) == 64 for row in manifest["objects"]))

            target = FakeS3Client({"stale-object": b"delete-me"})
            Command()._restore(target, "grc-evidence", archive_path, replace=True)
            self.assertEqual(target.objects, source.objects)
            self.assertEqual(target.content_types["tenant/a/evidence/one.txt"], "text/plain")
            self.assertEqual(
                target.metadata["tenant/a/evidence/one.txt"],
                {"classification": "internal"},
            )

    def test_missing_replacement_bucket_requires_opt_in_and_integrity(self):
        source = FakeS3Client({"ci/marker": b"pre-backup"})
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "objectstore.zip"
            Command()._export(source, "grc-evidence", archive)

            class MissingBucket(FakeS3Client):
                created = False

                def head_bucket(self, Bucket):
                    if not self.created:
                        raise ClientError({"Error": {"Code": "404", "Message": "not found"}}, "HeadBucket")

                def create_bucket(self, Bucket, **kwargs):
                    assert Bucket == "grc-evidence"
                    self.created = True

            target = MissingBucket()
            with (
                patch("apps.common.management.commands.pilot_objectstore_archive.s3_client", return_value=target),
                patch("apps.common.management.commands.pilot_objectstore_archive.settings.S3_BUCKET", "grc-evidence"),
                patch("apps.common.management.commands.pilot_objectstore_archive.settings.S3_REGION", "us-east-1"),
            ):
                with self.assertRaises(CommandError):
                    Command().handle(operation="restore", archive=str(archive), replace=True,
                                     initialize_missing_bucket=False)
                self.assertFalse(target.created)
                with self.assertRaises(CommandError):
                    Command().handle(operation="restore", archive=str(archive), replace=False,
                                     initialize_missing_bucket=True)
                self.assertFalse(target.created)

                corrupt = Path(directory) / "invalid.zip"
                corrupt.write_bytes(b"not a zip")
                with self.assertRaises(CommandError):
                    Command().handle(operation="restore", archive=str(corrupt), replace=True,
                                     initialize_missing_bucket=True)
                self.assertFalse(target.created)

                Command().handle(operation="restore", archive=str(archive), replace=True,
                                 initialize_missing_bucket=True)
                self.assertTrue(target.created)
                self.assertEqual(target.objects, source.objects)

    def test_restore_refuses_nonempty_bucket_without_replace(self):
        source = FakeS3Client({"one": b"1"})
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "objects.zip"
            Command()._export(source, "grc-evidence", archive_path)
            target = FakeS3Client({"existing": b"keep"})
            with self.assertRaisesMessage(CommandError, "not empty"):
                Command()._restore(target, "grc-evidence", archive_path, replace=False)
            self.assertEqual(target.objects, {"existing": b"keep"})


    def test_bad_later_object_is_rejected_before_replace_deletes_original(self):
        source = FakeS3Client({"one": b"valid", "two": b"expected-later-object"})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "objects.zip"
            Command()._export(source, "grc-evidence", path)
            with zipfile.ZipFile(path) as archive:
                manifest = json.loads(archive.read("manifest.json"))
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("objects/00000000.bin", b"valid")
                archive.writestr("objects/00000001.bin", b"modified-after-backup")
                archive.writestr("manifest.json", json.dumps(manifest))
            target = FakeS3Client({"existing-valuable-evidence": b"keep this"})
            with self.assertRaisesMessage(CommandError, "checksum/length mismatch"):
                Command()._restore(target, "grc-evidence", path, replace=True)
            self.assertEqual(target.objects, {"existing-valuable-evidence": b"keep this"})

    def test_untrusted_archive_metadata_never_reaches_destructive_restore(self):
        payload = b"evidence bytes"
        valid_row = {
            "key": "tenant/evidence-1", "archive_name": "objects/00000000.bin",
            "size": len(payload), "sha256": hashlib.sha256(payload).hexdigest(),
            "content_type": "application/octet-stream", "metadata": {},
        }
        manifest = {
            "schema_version": 1, "object_count": 1,
            "objects": [valid_row],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "objects.zip"
            cases = [
                ("unsupported-schema", {**manifest, "schema_version": 2}, ["objects/00000000.bin"]),
                ("wrong-count", {**manifest, "object_count": 2}, ["objects/00000000.bin"]),
                ("missing-member", manifest, []),
                ("extra-member", manifest, ["objects/00000000.bin", "extra/file"]),
                ("wrong-member-name", {**manifest, "objects": [
                    {**valid_row, "archive_name": "../other"}]}, ["objects/00000000.bin"]),
                ("wrong-size", {**manifest, "objects": [
                    {**valid_row, "size": len(payload) + 5}]}, ["objects/00000000.bin"]),
                ("wrong-hash", {**manifest, "objects": [
                    {**valid_row, "sha256": "0" * 64}]}, ["objects/00000000.bin"]),
                ("unsafe-metadata", {**manifest, "objects": [
                    {**valid_row, "metadata": {"scope": ["bad-type"]}}]}, ["objects/00000000.bin"]),
                ("duplicate-keys", {**manifest, "object_count": 2, "objects": [
                    valid_row, {**valid_row, "archive_name": "objects/00000001.bin"}]},
                    ["objects/00000000.bin", "objects/00000001.bin"]),
            ]
            for label, sample_manifest, members in cases:
                with self.subTest(case=label):
                    with zipfile.ZipFile(path, "w") as archive:
                        for member in members:
                            archive.writestr(member, payload)
                        archive.writestr("manifest.json", json.dumps(sample_manifest))
                    target = FakeS3Client({"existing": b"cannot-delete"})
                    with self.assertRaises(CommandError):
                        Command()._restore(target, "grc-evidence", path, replace=True)
                    self.assertEqual(target.objects, {"existing": b"cannot-delete"})

    def test_corrupt_archive_and_symlink_fail_before_replace(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.zip"
            path.write_bytes(b"not-a-zip")
            target = FakeS3Client({"existing": b"do-not-delete"})
            with self.assertRaises(CommandError):
                Command()._restore(target, "grc-evidence", path, replace=True)
            link = Path(directory) / "linked.zip"
            link.symlink_to(path)
            with self.assertRaises(CommandError):
                Command()._restore(target, "grc-evidence", link, replace=True)
            self.assertEqual(target.objects, {"existing": b"do-not-delete"})


class PilotBackupScriptContractTests(SimpleTestCase):
    def test_backup_preserves_active_tls_and_local_ai_compose_overlays(self):
        root = Path(__file__).resolve().parents[3]
        script = (root / "scripts" / "pilot-backup.sh").read_text(encoding="utf-8")
        self.assertIn('if [[ "${PILOT_TLS:-NO}" == "YES" ]]', script)
        self.assertIn("COMPOSE+=(-f docker-compose.pilot.tls.yml)", script)
        self.assertIn('if [[ "${PILOT_LOCAL_AI:-NO}" == "YES" ]]', script)
        self.assertIn("COMPOSE+=(--profile local-ai)", script)


class PilotRestoreScriptContractTests(SimpleTestCase):
    def test_restore_migration_plan_preserves_host_operator_ownership(self):
        root = Path(__file__).resolve().parents[3]
        script = (root / "scripts" / "pilot-restore.sh").read_text(encoding="utf-8")
        self.assertIn('--user "$(id -u):$(id -g)"', script)
        self.assertIn("restore-migration-plan.json", script)

    def test_fresh_replacement_volume_waits_for_database_health_before_psql(self):
        root = Path(__file__).resolve().parents[3]
        script = (root / "scripts" / "pilot-restore.sh").read_text(encoding="utf-8")
        dependency_wait = '"${COMPOSE[@]}" up -d --wait postgres redis objectstore'
        first_psql = 'TARGET_PG_VERSION_NUM="$('
        self.assertIn(dependency_wait, script)
        self.assertLess(script.index(dependency_wait), script.index(first_psql))

class PilotRestoreIdentityContractTests(SimpleTestCase):
    def test_critical_key_check_runs_before_any_destructive_restore(self):
        root = Path(__file__).resolve().parents[3]
        script = (root / "scripts" / "pilot-restore.sh").read_text(encoding="utf-8")
        self.assertIn('if [[ "${RESTORE_CONFIG:-NO}" != "YES" ]]', script)
        self.assertIn("datacenter-restore-config-check.py", script)
        self.assertLess(
            script.index("datacenter-restore-config-check.py"),
            script.index('echo "[1/8] Stopping application writers..."'),
        )


class DatacenterRecoveryPreflightContractTests(SimpleTestCase):
    def test_recovery_preflight_is_read_only_and_bypasses_docker(self):
        root = Path(__file__).resolve().parents[3]
        ctl = (root / "scripts" / "datacenterctl").read_text(encoding="utf-8")
        probe = (root / "scripts" / "datacenter-recovery-preflight.py").read_text(encoding="utf-8")
        self.assertIn('if [[ "$COMMAND" == "recovery-preflight" ]]', ctl)
        self.assertLess(
            ctl.index('if [[ "$COMMAND" == "recovery-preflight" ]]'),
            ctl.index("require_env\ncompose_args"),
        )
        self.assertIn("checks.check_restore(backups, name)", probe)
        self.assertIn("crypto.compatible(root / \".env\", selected / \"config.env\")", probe)
        self.assertIn("ready_for_operator_review", probe)


class PilotPostgresComposeContractTests(SimpleTestCase):
    def test_postgres18_uses_parent_persistent_volume_layout(self):
        root = Path(__file__).resolve().parents[3]
        compose = (root / "docker-compose.pilot.yml").read_text(encoding="utf-8")
        self.assertIn("pgvector/pgvector:0.8.6-pg18-trixie", compose)
        self.assertIn("postgres_pilot_data:/var/lib/postgresql", compose)
        self.assertNotIn("postgres_pilot_data:/var/lib/postgresql/data", compose)
