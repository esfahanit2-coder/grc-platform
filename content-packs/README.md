# GRC Content Packs

Sprint 2 introduces framework-as-data. Content packs are imported into the Framework Engine; application code must not contain framework-specific conditionals.

Supported import formats in Sprint 2:

- JSON content pack
- XLSX workbook (`manifest` + `requirements` sheets)

Do **not** bundle copyrighted ISO/ISACA/other licensed text unless the product has the required distribution/software-integration rights. Customer-provided licensed material should use `license_type=customer_provided` and retain provenance in `license_metadata`.

See `spec/v1.md` and the public-domain/internal demo in `examples/demo-baseline.json`.

For the AFTA / ISMS pilot, use `AFTA_ISMS_PILOT.md`. Restricted customer source material starts from `templates/customer-provided-restricted-framework.json.example`, is populated outside this repository, imported into the customer tenant, and is never committed back without verified redistribution rights.

## First actual ISO/IEC 27001:2022 content source (#5)

The public repository contains a **source-verified numeric identifier-only index** in `references/iso-iec-27001-2022-structure-only.json` (44 structural nodes, 93 Annex A control IDs, PDF page references, **no text/titles/guidance**, no import capability, source-bytes checksum still pending), plus a **metadata-only, deliberately non-importable** ISO/IEC 27001:2022 customer-source template: `templates/iso-iec-27001-2022.customer-provided.json.example`. Follow `ISO_27001_AUTHORIZED_IMPORT_FA.md` and use `python scripts/restricted-content-preflight.py --self-test` to verify the local preflight tool. Once licensed PDF sources and human authorization are available, populate the pack **outside the repository**, run local source-PDF SHA checks, and use tenant-scoped Framework import dry-run. Neither the original PDF nor populated protected wording may be pushed to the public repository. The preflight cannot independently establish legal distribution rights, clause correctness or compliance.
