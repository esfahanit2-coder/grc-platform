#!/usr/bin/env python3
"""Opt-in local preflight for customer-provided restricted framework JSON packs.

No PDF text, filenames, pack bodies, credentials, or PDF bytes are printed.
This does not verify that a claimed license grants the claimed legal rights.
"""
import argparse
import hashlib
import json
import re
import sys
import tempfile
from pathlib import Path


SHA256 = re.compile(r"^[a-fA-F0-9]{64}$")


def _filled(value):
    return isinstance(value, str) and bool(value.strip()) and not any(
        marker in value for marker in ("<", ">", "TODO", "TBD")
    )


def _pdf_digest(path):
    with Path(path).open("rb") as stream:
        if stream.read(5) != b"%PDF-":
            raise ValueError("Source file does not start with a PDF header")
        stream.seek(0)
        digest = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_pack(pack, sources):
    """Return an error list without disclosing protected document contents."""
    errors = []
    if not isinstance(pack, dict):
        return ["Root must be a JSON object"]
    framework = pack.get("framework") or {}
    version = pack.get("version") or {}
    if not isinstance(framework, dict) or not isinstance(version, dict):
        return ["framework and version must be JSON objects"]
    rights = framework.get("license_metadata") or {}
    metadata = version.get("metadata") or {}
    if not isinstance(rights, dict) or not isinstance(metadata, dict):
        return ["license_metadata and version.metadata must be JSON objects"]
    if framework.get("license_type") != "customer_provided":
        errors.append("framework.license_type must be customer_provided")
    if rights.get("content_class") != "CUSTOMER_PROVIDED":
        errors.append("license_metadata.content_class must be CUSTOMER_PROVIDED")
    if rights.get("tenant_restricted") is not True:
        errors.append("license_metadata.tenant_restricted must be true")
    if rights.get("redistribution_allowed") is not False:
        errors.append("license_metadata.redistribution_allowed must be false")
    for field in ("authorization_reference", "rights_basis", "provenance_note"):
        if not _filled(rights.get(field)):
            errors.append("license_metadata." + field + " must be populated and manually verified")
    for field in ("code", "name", "publisher"):
        if not _filled(framework.get(field)):
            errors.append("framework." + field + " must be populated")
    if not _filled(version.get("version_code")):
        errors.append("version.version_code must be populated")

    documents = metadata.get("source_documents")
    if not isinstance(documents, list) or not documents:
        errors.append("version.metadata.source_documents must contain at least one verified source")
        documents = []
    known_ids = set()
    for index, doc in enumerate(documents):
        if not isinstance(doc, dict):
            errors.append("source_documents item must be an object")
            continue
        doc_id = doc.get("document_id")
        if not _filled(doc_id):
            errors.append("source_documents item has missing document_id")
            continue
        if doc_id in known_ids:
            errors.append("Duplicate source document ID")
        known_ids.add(doc_id)
        for field in ("reference", "publisher", "language", "edition"):
            if not _filled(doc.get(field)):
                errors.append("source document " + doc_id + " missing " + field)
        expected_hash = doc.get("sha256")
        if not isinstance(expected_hash, str) or not SHA256.fullmatch(expected_hash):
            errors.append("source document " + doc_id + " has invalid sha256")
        if doc_id not in sources:
            errors.append("source document " + doc_id + " has no local PDF supplied for checksum verification")
        else:
            try:
                actual_hash = _pdf_digest(sources[doc_id])
                if isinstance(expected_hash, str) and actual_hash.lower() != expected_hash.lower():
                    errors.append("source document " + doc_id + " PDF SHA-256 mismatch")
            except (OSError, ValueError) as exc:
                errors.append("source document " + doc_id + " cannot be verified: " + type(exc).__name__)
    for extra in set(sources) - known_ids:
        errors.append("Unreferenced local source ID " + extra)

    rows = pack.get("requirements")
    if not isinstance(rows, list) or not rows:
        errors.append("requirements must be a non-empty list: template-only packs cannot be imported")
        rows = []
    codes = set()
    parents = {}
    for number, row in enumerate(rows, 1):
        tag = "requirement #" + str(number)
        if not isinstance(row, dict):
            errors.append(tag + " must be an object")
            continue
        code = row.get("code")
        if not _filled(code):
            errors.append(tag + " has missing code")
            continue
        if code in codes:
            errors.append(tag + " has duplicate code")
        codes.add(code)
        parents[code] = row.get("parent_code")
        if not _filled(row.get("title")):
            errors.append(tag + " title is missing or a placeholder")
        ref = (row.get("metadata") or {}).get("source_reference") if isinstance(row.get("metadata") or {}, dict) else None
        if not isinstance(ref, dict):
            errors.append(tag + " missing metadata.source_reference")
            continue
        if ref.get("document_id") not in known_ids:
            errors.append(tag + " references an unknown source document")
        if not _filled(ref.get("locator")):
            errors.append(tag + " missing source locator")
        pages = ref.get("pages")
        if not isinstance(pages, list) or not pages or any(type(p) is not int or p < 1 for p in pages):
            errors.append(tag + " must have positive PDF page references")
    for code, parent in parents.items():
        if parent and parent not in codes:
            errors.append("Missing parent for requirement " + code)
        trail = set()
        node = code
        while node in parents and node is not None:
            if node in trail:
                errors.append("Requirement parent cycle detected")
                break
            trail.add(node)
            node = parents[node]
    return errors


def self_test():
    with tempfile.TemporaryDirectory() as folder:
        source = Path(folder) / "source.pdf"
        source.write_bytes(b"%PDF-1.4\n% Synthetic non-standard fixture only\n%%EOF\n")
        digest = _pdf_digest(source)
        pack = {
            "framework": {
                "code": "synthetic-local", "name": "Synthetic local validation fixture",
                "publisher": "Local test", "license_type": "customer_provided",
                "license_metadata": {
                    "content_class": "CUSTOMER_PROVIDED", "tenant_restricted": True,
                    "redistribution_allowed": False, "authorization_reference": "local-fixture-only",
                    "rights_basis": "synthetic test", "provenance_note": "test only"
                },
            },
            "version": {"version_code": "test", "metadata": {"source_documents": [{
                "document_id": "fixture", "reference": "synthetic", "publisher": "Local test",
                "language": "en", "edition": "test", "sha256": digest
            }]}},
            "requirements": [
                {"code": "X", "title": "Synthetic parent", "assessable": False,
                 "metadata": {"source_reference": {"document_id": "fixture", "locator": "synthetic section", "pages": [1]}}},
                {"code": "X.1", "parent_code": "X", "title": "Synthetic child",
                 "metadata": {"source_reference": {"document_id": "fixture", "locator": "synthetic item", "pages": [1]}}},
            ],
        }
        assert not validate_pack(pack, {"fixture": source}), "valid synthetic fixture rejected"
        original = pack["framework"]["license_metadata"]["authorization_reference"]
        pack["framework"]["license_metadata"]["authorization_reference"] = "<required>"
        assert validate_pack(pack, {"fixture": source})
        pack["framework"]["license_metadata"]["authorization_reference"] = original
        pack["requirements"][1]["parent_code"] = "X.1"
        assert any("cycle" in e for e in validate_pack(pack, {"fixture": source}))
        pack["requirements"][1]["parent_code"] = "X"
        pack["version"]["metadata"]["source_documents"][0]["sha256"] = "0" * 64
        assert any("mismatch" in e for e in validate_pack(pack, {"fixture": source}))
        pack["version"]["metadata"]["source_documents"][0]["sha256"] = digest
        pack["requirements"] = []
        assert validate_pack(pack, {"fixture": source})
        assert validate_pack(pack, {})
    print("Restricted content preflight self-test: PASS (synthetic fixtures only)")


def main():
    parser = argparse.ArgumentParser(description="Offline restricted-framework content-pack provenance preflight")
    parser.add_argument("--pack", type=Path, help="Private JSON content pack (never commit the populated file)")
    parser.add_argument("--source-pdf", action="append", default=[], metavar="ID=PATH",
                        help="Map each source document_id to its local licensed PDF")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not args.pack:
        parser.error("--pack is required unless --self-test is used")
    sources = {}
    for value in args.source_pdf:
        if "=" not in value or not value.split("=", 1)[0]:
            parser.error("--source-pdf must have ID=PATH format")
        key, path = value.split("=", 1)
        if key in sources:
            parser.error("Each source ID must appear once")
        sources[key] = Path(path)
    try:
        pack = json.loads(args.pack.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print("FAILED: cannot read valid JSON pack (" + type(exc).__name__ + ")", file=sys.stderr)
        return 2
    errors = validate_pack(pack, sources)
    if errors:
        print("RESTRICTED CONTENT PREFLIGHT FAILED", file=sys.stderr)
        for error in errors:
            print(" - " + error, file=sys.stderr)
        return 1
    print("RESTRICTED CONTENT PREFLIGHT PASSED: structural/source-hash checks only.")
    print("Human content accuracy, usage rights, tenant scope, and approval are still required.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
