#!/usr/bin/env python3
"""Check the public identifier-only ISO/IEC 27001 structure index.

This fixture intentionally contains no proprietary standard wording.
"""
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "content-packs/references/iso-iec-27001-2022-structure-only.json"


def check():
    source = json.loads(INDEX.read_text(encoding="utf-8"))
    assert source["importable"] is False
    assert source["assessable"] is False
    assert source["rights"]["protected_standard_text_included"] is False
    assert source["source_pdf_sha256"] is None, "No hash may be claimed without PDF byte access"
    assert source["reference_number"] == "ISO/IEC 27001:2022(E)"
    assert source["source_pdf_page_count"] == 26

    clauses = source["clause_identifiers"]
    assert len(clauses) == 44
    codes = [row["code"] for row in clauses]
    assert len(codes) == len(set(codes))
    assert set(str(n) for n in range(1, 11)).issubset(codes)
    assert "6.3" in codes, "Clauses in body take precedence over incomplete TOC extraction"
    for row in clauses:
        assert 7 <= row["pdf_page_1_based"] <= 16
        if row["parent_code"]:
            assert row["parent_code"] in codes
        else:
            assert "." not in row["code"]
        assert set(row) == {"code", "parent_code", "pdf_page_1_based", "kind"}

    controls = source["annex_a_control_identifiers"]
    assert len(controls) == 93
    ids = [row["internal_code"] for row in controls]
    assert len(ids) == len(set(ids))
    for family, count in ((5, 37), (6, 8), (7, 14), (8, 34)):
        expected = {"A." + str(family) + "." + str(i) for i in range(1, count + 1)}
        actual = {row["internal_code"] for row in controls if row["source_group"] == family}
        assert actual == expected, "Annex control identifiers differ from verified source structure"
        for row in controls:
            if row["source_group"] == family:
                assert row["source_identifier"] == row["internal_code"].removeprefix("A.")
                assert row["source_table"] == "A." + str(family - 4)
                assert 17 <= row["pdf_page_1_based"] <= 24
                assert set(row) == {
                    "internal_code", "source_identifier", "source_group",
                    "source_table", "pdf_page_1_based"
                }
    assert source["summary"]["annex_control_count"] == 93
    assert source["summary"]["main_structure_count"] == 44
    print("ISO/IEC 27001 identifier-only source index: PASS (44 structural nodes; 93 Annex A identifiers)")


if __name__ == "__main__":
    check()
