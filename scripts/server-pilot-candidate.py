#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

SCHEMA = "grc-server-pilot-candidate-v1"
VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
IMAGE_ID_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
REQUIRED_ROLES = {"backend", "frontend", "postgres", "redis", "objectstore", "ollama", "gateway"}


class CandidateError(RuntimeError):
    pass


def canonical_json(payload: object) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def build_candidate(release_version: str, source_commit: str, images_payload: object) -> dict[str, object]:
    if not VERSION_RE.fullmatch(release_version) or release_version in {"local", "latest"}:
        raise CandidateError("invalid server candidate release version")
    if not SHA_RE.fullmatch(source_commit):
        raise CandidateError("server candidate source commit must be an exact lowercase Git SHA")
    if not isinstance(images_payload, dict) or images_payload.get("schema") != "grc-offline-images-v1":
        raise CandidateError("unsupported images metadata schema")
    rows = images_payload.get("images")
    if not isinstance(rows, list):
        raise CandidateError("images metadata must contain an images list")

    images: list[dict[str, object]] = []
    roles: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise CandidateError("invalid image metadata row")
        role = str(row.get("role") or "")
        reference = str(row.get("reference") or "")
        image_id = str(row.get("image_id") or "")
        repo_digests = row.get("repo_digests")
        if not role or role in roles:
            raise CandidateError("image roles must be unique and non-empty")
        if not reference or not IMAGE_ID_RE.fullmatch(image_id):
            raise CandidateError(f"image identity is incomplete for role {role or 'unknown'}")
        if not isinstance(repo_digests, list) or any(not isinstance(item, str) for item in repo_digests):
            raise CandidateError(f"repo_digests must be a string list for role {role}")
        roles.add(role)
        images.append(
            {
                "role": role,
                "reference": reference,
                "image_id": image_id,
                "repo_digests": sorted(repo_digests),
            }
        )
    missing = sorted(REQUIRED_ROLES - roles)
    if missing:
        raise CandidateError("server candidate is missing image roles: " + ", ".join(missing))

    return {
        "schema": SCHEMA,
        "candidate_class": "pilot-server-candidate",
        "release_status": "pilot-pre-rc",
        "release_version": release_version,
        "source_commit": source_commit,
        "canonical_install_path": "signed-offline-bundle",
        "runtime": {
            "default_profile": "core",
            "optional_profiles": ["local-ai"],
            "ai_enabled_by_default": False,
            "smtp_enabled_by_default": False,
            "connector_credentials_embedded": False,
            "customer_secrets_embedded": False,
            "tls_private_key_embedded": False,
            "third_party_ai_model_bytes_embedded": False,
            "package_or_image_download_required_at_startup": False,
        },
        "network": {
            "required_inbound_tcp": [443],
            "optional_inbound_tcp": [80],
            "published_database_cache_objectstore_ports": False,
        },
        "recovery": {
            "release_consistent_backup_supported": True,
            "destructive_restore_supported": True,
            "off_host_encrypted_backup_copy_required": True,
            "rpo_rto_must_be_measured_on_real_host": True,
        },
        "external_acceptance": {
            "complete": False,
            "gates": ["#5", "#6", "#7", "#8", "#40", "#42", "#74"],
            "policy": "Repository CI and this signed candidate do not replace real target-host, legal/content, connector, security, visual or UAT evidence.",
        },
        "images": sorted(images, key=lambda item: str(item["role"])),
    }


def write_candidate(release_version: str, source_commit: str, images_path: Path, output_path: Path) -> None:
    try:
        images_payload = json.loads(images_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateError(f"cannot read images metadata: {type(exc).__name__}") from exc
    payload = build_candidate(release_version, source_commit, images_payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(canonical_json(payload), encoding="utf-8")


def self_test() -> None:
    image_rows = []
    for index, role in enumerate(sorted(REQUIRED_ROLES), start=1):
        image_rows.append(
            {
                "role": role,
                "reference": f"example/{role}:v-test",
                "archive": f"images/{role}.tar",
                "image_id": "sha256:" + f"{index:064x}",
                "repo_digests": [f"example/{role}@sha256:" + f"{index + 100:064x}"],
            }
        )
    payload = build_candidate(
        "v0.9.0-pilot-test",
        "a" * 40,
        {"schema": "grc-offline-images-v1", "images": image_rows},
    )
    if payload["runtime"]["ai_enabled_by_default"] is not False:
        raise CandidateError("AI default must remain fail-safe disabled")
    if payload["external_acceptance"]["complete"] is not False:
        raise CandidateError("server candidate must not claim external acceptance")
    first = canonical_json(payload)
    second = canonical_json(
        build_candidate(
            "v0.9.0-pilot-test",
            "a" * 40,
            {"schema": "grc-offline-images-v1", "images": list(reversed(image_rows))},
        )
    )
    if first != second:
        raise CandidateError("server candidate metadata is not deterministic")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic exact-SHA Pilot Server Candidate metadata.")
    parser.add_argument("--release-version")
    parser.add_argument("--source-commit")
    parser.add_argument("--images")
    parser.add_argument("--out")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    try:
        if args.self_test:
            self_test()
            print("server Pilot candidate metadata self-test passed")
            return 0
        if not all((args.release_version, args.source_commit, args.images, args.out)):
            parser.error("--release-version, --source-commit, --images and --out are required")
        write_candidate(
            args.release_version,
            args.source_commit,
            Path(args.images).resolve(),
            Path(args.out).resolve(),
        )
        print("server Pilot candidate metadata written")
        return 0
    except CandidateError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
