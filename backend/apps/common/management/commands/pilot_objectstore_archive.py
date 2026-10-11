import hashlib
import json
import re
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


ARCHIVE_SCHEMA_VERSION = 1
CHUNK_SIZE = 1024 * 1024


def s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL or None,
        aws_access_key_id=settings.S3_ACCESS_KEY or None,
        aws_secret_access_key=settings.S3_SECRET_KEY or None,
        region_name=settings.S3_REGION,
        use_ssl=settings.S3_USE_SSL,
    )


def list_objects(client, bucket):
    token = None
    while True:
        kwargs = {"Bucket": bucket}
        if token:
            kwargs["ContinuationToken"] = token
        response = client.list_objects_v2(**kwargs)
        for row in response.get("Contents") or []:
            yield row
        if not response.get("IsTruncated"):
            break
        token = response.get("NextContinuationToken")
        if not token:
            raise CommandError("Object-store listing was truncated without a continuation token.")


def delete_all_objects(client, bucket):
    batch = []
    for row in list_objects(client, bucket):
        batch.append({"Key": row["Key"]})
        if len(batch) == 1000:
            client.delete_objects(Bucket=bucket, Delete={"Objects": batch, "Quiet": True})
            batch = []
    if batch:
        client.delete_objects(Bucket=bucket, Delete={"Objects": batch, "Quiet": True})


class Command(BaseCommand):
    help = "Export or restore the configured S3-compatible pilot object store."

    def add_arguments(self, parser):
        parser.add_argument("operation", choices=["export", "restore"])
        parser.add_argument("--archive", required=True, help="Archive path inside the backend container.")
        parser.add_argument(
            "--replace",
            action="store_true",
            help="For restore only: delete existing objects before restoring the archive.",
        )
        parser.add_argument(
            "--initialize-missing-bucket", action="store_true",
            help="Explicit replacement-host --replace recovery only, after archive validation.",
        )

    def handle(self, *args, **options):
        path = Path(options["archive"])
        client = s3_client()
        bucket = settings.S3_BUCKET
        init_bucket = options.get("initialize_missing_bucket", False)
        if init_bucket and (options["operation"] != "restore" or not options["replace"]):
            raise CommandError("Bucket initialization requires an explicitly approved --replace restore.")
        try:
            client.head_bucket(Bucket=bucket)
        except ClientError as exc:
            code = str(exc.response.get("Error", {}).get("Code", ""))
            if init_bucket and code in {"404", "NotFound", "NoSuchBucket"}:
                self._initialize_missing_bucket(client, bucket, path)
            else:
                raise CommandError("Cannot access the configured target S3 bucket.") from exc
        except Exception as exc:
            raise CommandError("Cannot access the configured target S3 bucket.") from exc

        if options["operation"] == "export":
            self._export(client, bucket, path)
        else:
            self._restore(client, bucket, path, replace=options["replace"])

    @classmethod
    def _initialize_missing_bucket(cls, client, bucket, path):
        """Never create a missing recovery bucket from corrupt or mismatched bytes."""
        if not path.is_file() or path.is_symlink():
            raise CommandError("Archive is missing or is not a regular file.")
        try:
            with zipfile.ZipFile(path, "r") as archive:
                cls._validate_archive(archive)
                manifest = json.loads(archive.read("manifest.json"))
                if manifest.get("source_bucket") != bucket:
                    raise CommandError("Archive source bucket differs from configured recovery bucket.")
        except (zipfile.BadZipFile, EOFError, UnicodeError, RuntimeError, OSError, ValueError) as exc:
            raise CommandError("Invalid archive; no target bucket was created.") from exc
        parameters = {"Bucket": bucket}
        region = settings.S3_REGION
        if region and region != "us-east-1":
            parameters["CreateBucketConfiguration"] = {"LocationConstraint": region}
        try:
            client.create_bucket(**parameters)
        except Exception as exc:
            raise CommandError("Approved replacement bucket initialization failed.") from exc

    def _export(self, client, bucket, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        objects = list(list_objects(client, bucket))
        manifest = {
            "schema_version": ARCHIVE_SCHEMA_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_bucket": bucket,
            "object_count": len(objects),
            "objects": [],
        }
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
            for index, row in enumerate(objects):
                key = row["Key"]
                response = client.get_object(Bucket=bucket, Key=key)
                archive_name = f"objects/{index:08d}.bin"
                digest = hashlib.sha256()
                size = 0
                with archive.open(archive_name, "w", force_zip64=True) as destination:
                    body = response["Body"]
                    while True:
                        chunk = body.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        digest.update(chunk)
                        size += len(chunk)
                        destination.write(chunk)
                manifest["objects"].append(
                    {
                        "key": key,
                        "archive_name": archive_name,
                        "size": size,
                        "sha256": digest.hexdigest(),
                        "content_type": response.get("ContentType") or "application/octet-stream",
                        "metadata": response.get("Metadata") or {},
                    }
                )
            archive.writestr(
                "manifest.json",
                json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2),
            )
        self.stdout.write(self.style.SUCCESS(f"Exported {len(objects)} objects to {path}"))

    @staticmethod
    def _validate_archive(archive):
        """Validate every ZIP payload before destination deletion or upload."""
        members = archive.infolist()
        if len(members) > 1000001:
            raise CommandError("Archive contains too many members.")
        names = [info.filename for info in members]
        name_set = set(names)
        if len(names) != len(name_set) or "manifest.json" not in name_set:
            raise CommandError("Archive has duplicate or missing members.")
        header = archive.getinfo("manifest.json")
        if header.is_dir() or header.file_size > 32 * 1024 * 1024:
            raise CommandError("Archive manifest is not a bounded regular member.")
        try:
            manifest = json.loads(archive.read(header))
        except (json.JSONDecodeError, UnicodeError) as exc:
            raise CommandError("Archive manifest is invalid.") from exc
        if not isinstance(manifest, dict) or manifest.get("schema_version") != ARCHIVE_SCHEMA_VERSION:
            raise CommandError("Unsupported or invalid object-store archive schema.")
        rows = manifest.get("objects")
        count = manifest.get("object_count")
        if (
            not isinstance(rows, list) or isinstance(count, bool)
            or not isinstance(count, int) or count != len(rows)
            or len(members) != len(rows) + 1
        ):
            raise CommandError("Archive object count or member list is inconsistent.")
        seen_keys = set()
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                raise CommandError("Archive object entry must be a mapping.")
            key = row.get("key")
            name = row.get("archive_name")
            length = row.get("size")
            digest_expected = row.get("sha256")
            content_type = row.get("content_type", "application/octet-stream")
            metadata = row.get("metadata", {})
            expected_name = f"objects/{index:08d}.bin"
            if (
                not isinstance(key, str) or not key or key in seen_keys
                or name != expected_name or name not in name_set
                or isinstance(length, bool) or not isinstance(length, int) or length < 0
                or not isinstance(digest_expected, str)
                or not re.fullmatch(r"[0-9a-f]{64}", digest_expected)
                or not isinstance(content_type, str) or not content_type
                or not isinstance(metadata, dict)
                or not all(isinstance(k, str) and isinstance(v, str)
                           for k, v in metadata.items())
            ):
                raise CommandError("Archive object metadata failed validation.")
            seen_keys.add(key)
            member = archive.getinfo(name)
            if member.is_dir() or member.file_size != length:
                raise CommandError("Archive member size differs from manifest.")
            checksum = hashlib.sha256()
            observed_size = 0
            with archive.open(member, "r") as source:
                while True:
                    chunk = source.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    checksum.update(chunk)
                    observed_size += len(chunk)
            if observed_size != length or checksum.hexdigest() != digest_expected:
                raise CommandError("Archive object checksum/length mismatch.")
        return rows

    def _restore(self, client, bucket, path, *, replace):
        if not path.is_file() or path.is_symlink():
            raise CommandError("Archive is missing or is not a regular file.")
        existing = list(list_objects(client, bucket))
        if existing and not replace:
            raise CommandError(
                "Target object-storage bucket is not empty. Re-run with --replace only after explicit restore approval."
            )
        try:
            with zipfile.ZipFile(path, "r") as archive:
                # A direct manage.py restore must be as safe as the outer
                # datacenterctl preflight: validate ALL objects before delete.
                rows = self._validate_archive(archive)
                if existing and replace:
                    delete_all_objects(client, bucket)
                restored = 0
                for row in rows:
                    key = row["key"]
                    digest = hashlib.sha256()
                    size = 0
                    with archive.open(row["archive_name"], "r") as source, tempfile.SpooledTemporaryFile(max_size=8 * CHUNK_SIZE) as staged:
                        while True:
                            chunk = source.read(CHUNK_SIZE)
                            if not chunk:
                                break
                            digest.update(chunk)
                            size += len(chunk)
                            staged.write(chunk)
                        if size != row["size"] or digest.hexdigest() != row["sha256"]:
                            raise CommandError("Archive object changed after preflight validation.")
                        staged.seek(0)
                        extra = {
                            "ContentType": row.get("content_type") or "application/octet-stream",
                            "Metadata": row.get("metadata") or {},
                        }
                        client.upload_fileobj(staged, bucket, key, ExtraArgs=extra)
                    restored += 1
        except (zipfile.BadZipFile, EOFError, UnicodeError, RuntimeError, OSError) as exc:
            raise CommandError("Archive is corrupt or unreadable; restore was not completed.") from exc
        self.stdout.write(self.style.SUCCESS(f"Restored {restored} objects into bucket {bucket}"))
