# GRC Content Packs

Sprint 2 introduces framework-as-data. Content packs are imported into the Framework Engine; application code must not contain framework-specific conditionals.

Supported import formats in Sprint 2:

- JSON content pack
- XLSX workbook (`manifest` + `requirements` sheets)

Do **not** bundle copyrighted ISO/ISACA/other licensed text unless the product has the required distribution/software-integration rights. Customer-provided licensed material should use `license_type=customer_provided` and retain provenance in `license_metadata`.

See `spec/v1.md` and the public-domain/internal demo in `examples/demo-baseline.json`.
