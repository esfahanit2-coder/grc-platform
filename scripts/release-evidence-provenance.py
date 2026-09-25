#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

SCHEMA = "grc-release-evidence-provenance-v1"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
IMAGE_ID_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class ProvenanceError(RuntimeError):
    pass


def canonical_json(payload: object) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def validate_sha(value: str, label: str) -> str:
    value = value.strip().lower()
    if not SHA_RE.fullmatch(value):
        raise ProvenanceError(f"{label} must be a lowercase 40-character Git SHA")
    return value


def validate_image_id(value: str, label: str) -> str:
    value = value.strip()
    if not IMAGE_ID_RE.fullmatch(value):
        raise ProvenanceError(f"{label} must be a Docker sha256 image ID")
    return value


def build_payload(
    source_commit: str,
    source_tree: str,
    backend_image_id: str,
    frontend_image_id: str,
) -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "source_commit": validate_sha(source_commit, "source_commit"),
        "source_tree": validate_sha(source_tree, "source_tree"),
        "application_images": {
            "backend": validate_image_id(backend_image_id, "backend_image_id"),
            "frontend": validate_image_id(frontend_image_id, "frontend_image_id"),
        },
    }


def load(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProvenanceError(f"cannot read provenance: {type(exc).__name__}") from exc
    if not isinstance(payload, dict) or payload.get("schema") != SCHEMA:
        raise ProvenanceError("unsupported release evidence provenance schema")
    return payload


def verify(
    path: Path,
    source_commit: str,
    source_tree: str,
    backend_image_id: str,
    frontend_image_id: str,
) -> None:
    actual = load(path)
    expected = build_payload(source_commit, source_tree, backend_image_id, frontend_image_id)
    if actual != expected:
        raise ProvenanceError("release evidence provenance does not match the exact source/image identities")


def self_test() -> None:
    payload = build_payload(
        "a" * 40,
        "b" * 40,
        "sha256:" + "1" * 64,
        "sha256:" + "2" * 64,
    )
    with tempfile.TemporaryDirectory(prefix="grc-release-evidence-") as tmp:
        path = Path(tmp) / "provenance.json"
        path.write_text(canonical_json(payload), encoding="utf-8")
        verify(
            path,
            "a" * 40,
            "b" * 40,
            "sha256:" + "1" * 64,
            "sha256:" + "2" * 64,
        )
        try:
            verify(
                path,
                "a" * 40,
                "b" * 40,
                "sha256:" + "3" * 64,
                "sha256:" + "2" * 64,
            )
        except ProvenanceError:
            pass
        else:
            raise ProvenanceError("image mismatch self-test did not fail closed")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bind release security/SBOM evidence to exact source and app image IDs.")
    sub = parser.add_subparsers(dest="command", required=True)

    write = sub.add_parser("write")
    write.add_argument("--source-commit", required=True)
    write.add_argument("--source-tree", required=True)
    write.add_argument("--backend-image-id", required=True)
    write.add_argument("--frontend-image-id", required=True)
    write.add_argument("--out", required=True)

    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("--provenance", required=True)
    verify_parser.add_argument("--source-commit", required=True)
    verify_parser.add_argument("--source-tree", required=True)
    verify_parser.add_argument("--backend-image-id", required=True)
    verify_parser.add_argument("--frontend-image-id", required=True)

    sub.add_parser("self-test")
    args = parser.parse_args()

    try:
        if args.command == "write":
            payload = build_payload(
                args.source_commit,
                args.source_tree,
                args.backend_image_id,
                args.frontend_image_id,
            )
            out = Path(args.out)
            out.write_text(canonical_json(payload), encoding="utf-8")
        elif args.command == "verify":
            verify(
                Path(args.provenance),
                args.source_commit,
                args.source_tree,
                args.backend_image_id,
                args.frontend_image_id,
            )
        else:
            self_test()
            print("release evidence provenance self-test passed")
        return 0
    except ProvenanceError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
