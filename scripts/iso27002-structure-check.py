#!/usr/bin/env python3
"""Validate public numeric-only ISO/IEC 27002 edition indices and optional private PDFs.

No original PDF, copyrighted titles, statements, attributes or guidance may be
stored in the public repository or used as CI fixtures.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DIR = ROOT / "content-packs/references"
VERSIONS = {
    "2022": {
        "file": "iso-iec-27002-2022-structure-only.json",
        "sha256": "175bb0a035c764ff15513cbbc01bb0ecd7b6e03b44b1cb4b707478ef705e209a",
        "pages": 164,
        "groups": {5: 37, 6: 8, 7: 14, 8: 34},
        "total": 93,
    },
    "2013": {
        "file": "iso-iec-27002-2013-structure-only.json",
        "sha256": "546993de0d9b0be68483e4b190b745f05113d6ef35ebf75784f5e591d30b0188",
        "pages": 90,
        "groups": {5: 2, 6: 7, 7: 6, 8: 10, 9: 14, 10: 2, 11: 15, 12: 14, 13: 7, 14: 13, 15: 5, 16: 7, 17: 4, 18: 8},
        "total": 114,
    },
}


def validate_original_pdf(path: Path, expected: str) -> None:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        if f.read(5) != b"%PDF-":
            raise AssertionError("Private source has no valid PDF header")
        f.seek(0)
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    assert digest.hexdigest() == expected, "Original PDF bytes do not match pinned source SHA-256"


def validate_version(version: str, original_pdf: Path | None = None) -> set[str]:
    spec = VERSIONS[version]
    obj = json.loads((REFERENCE_DIR / spec["file"]).read_text(encoding="utf-8"))
    assert obj["schema"] == "grc.structural-index.v1"
    assert obj["importable"] is False and obj["assessable"] is False
    assert obj["rights"]["protected_standard_text_included"] is False
    assert obj["rights"]["redistribution_of_standard_text_authorized"] is False
    assert obj["reference_number"] == f"ISO/IEC 27002:{version}(E)"
    assert obj["source_pdf_page_count"] == spec["pages"]
    assert obj["source_pdf_sha256"] == spec["sha256"]
    assert re.fullmatch(r"[0-9a-f]{64}", obj["source_pdf_sha256"])
    if original_pdf is not None:
        validate_original_pdf(original_pdf, spec["sha256"])

    rows = obj["control_identifiers"]
    assert len(rows) == spec["total"] == obj["summary"]["control_count"]
    counts: dict[int, int] = {}
    identifiers: set[str] = set()
    categories: set[str] = set()
    for row in rows:
        key = "linkable_27001_2022_annex_a_identifier" if version == "2022" else "legacy_27001_2013_annex_a_identifier"
        assert set(row) == {"source_identifier", key, "source_group", "pdf_page_1_based"}
        code = row["source_identifier"]
        assert re.fullmatch(r"\d+\.\d+" if version == "2022" else r"\d+\.\d+\.\d+", code)
        assert row[key] == "A." + code
        assert code not in identifiers
        identifiers.add(code)
        counts[row["source_group"]] = counts.get(row["source_group"], 0) + 1
        assert row["source_group"] == int(code.split(".")[0])
        assert (11 if version == "2022" else 9) <= row["pdf_page_1_based"] < spec["pages"]
        if version == "2013":
            categories.add(".".join(code.split(".")[:2]))
    assert counts == spec["groups"]
    if version == "2013":
        assert len(categories) == obj["summary"]["control_category_count"] == 35
        assert obj["summary"]["control_clause_count"] == 14
    else:
        assert obj["summary"]["by_group"] == {
            "organizational": 37, "people": 8, "physical": 14, "technological": 34
        }
        for group, n in spec["groups"].items():
            assert {f"{group}.{i}" for i in range(1, n + 1)}.issubset(identifiers)
    return identifiers


def main(pdf_2022: Path | None = None, pdf_2013: Path | None = None) -> None:
    current = validate_version("2022", pdf_2022)
    legacy = validate_version("2013", pdf_2013)
    index_27001 = json.loads(
        (REFERENCE_DIR / "iso-iec-27001-2022-structure-only.json").read_text(encoding="utf-8")
    )
    expected = {c["source_identifier"] for c in index_27001["annex_a_control_identifiers"]}
    assert current == expected, "ISO 27002:2022 controls and ISO 27001:2022 Annex A identifiers disagree"
    assert "5.1" in current and "5.1.1" in legacy and "5.1.1" not in current
    print("ISO 27002 structural and 27001 Annex A numeric alignment: PASS (2022=93, 2013=114)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-pdf-2022", type=Path, help="Private ISO 27002:2022 source path, not for public CI")
    parser.add_argument("--source-pdf-2013", type=Path, help="Private ISO 27002:2013 source path, not for public CI")
    args = parser.parse_args()
    main(args.source_pdf_2022, args.source_pdf_2013)
