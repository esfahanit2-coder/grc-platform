# GRC Platform — Detailed Roadmap (English)

This roadmap explains not only what is scheduled, but why each gate exists and what evidence is required before it is considered complete.

## Release targets

- `v0.9.0-pilot`: usable end-to-end pilot candidate with real GRC workflows and controlled operational proof.
- `v1.0.0-rc1`: release candidate after pre-v1 engineering, security and operational readiness gates.

## Gate 0 — Repository and CI normalization — COMPLETE

**Purpose:** make GitHub the reproducible source of truth before feature acceleration.

Completed outcomes include the canonical private repository, committed npm lockfile, backend/frontend CI, PostgreSQL 18 + pgvector migration from empty DB, full Django tests, Next.js production build, SAST, secret scan, container scan, SBOM generation and release gating.

**Done means:** a fresh commit cannot be merged/released while the core build/security/runtime gates fail.

## Gate 1 — Internal pilot foundation — SOFTWARE COMPLETE, REAL-HOST PROOF PENDING (#7)

**Purpose:** prove that the product can run as a sovereign on-premise system, not only inside development/CI.

Software already includes pilot compose, TLS gateway, local S3-compatible storage, optional local AI, readiness checks, backup/restore tooling and operational runbooks.

Remaining real-world proof:
- deploy on a clean pilot host;
- run real destructive backup/restore drill;
- measure observed RPO/RTO rather than inventing values;
- verify browser cookie/CSRF mode under real TLS;
- run local Ollama/vLLM with internet egress disabled.

**Done means:** another operator can deploy, restore and operate the pilot from documented artifacts with measured recovery evidence.

## Gate 2 — Content pilot — FOUNDATION COMPLETE, AUTHORIZED CONTENT PENDING (#5)

**Purpose:** prove the framework-as-content model using real legally usable content.

Completed:
- versioned content-pack/import model;
- licensing/provenance metadata;
- tenant-scoped restricted-content path;
- AFTA customer-provided conversion foundation;
- human approval path for mappings/crosswalks;
- internal example control baseline;
- SoA/RTP/audit/report outputs.

Remaining:
- authorized ISMS/ISO 27001 source material;
- documented software-use/redistribution rights where relevant;
- at least one human-approved real AFTA ↔ ISMS ↔ Internal/Common-Control mapping.

**Done means:** the product demonstrates real multi-framework reuse without violating content rights.

## Gate 3 — Connector pilot — IMPLEMENTATION/UI COMPLETE, LIVE PROOF PENDING (#6)

**Purpose:** prove that infrastructure facts can become auditable reusable Evidence without bypassing human judgment.

Implemented providers:
- AD/LDAP;
- FortiGate;
- Veeam;
- Tenable/Nessus.

Implemented boundaries include read-only collection, secret references, SSRF restrictions, target validation, normalized provider datasets, Evidence provenance/hash, failure diagnostics, human-review metadata and Connector Operations UI with health/sync/run history.

Remaining:
- run authorized live health/sync against available internal systems;
- create reusable Evidence from at least three real connector types;
- record representative failures and confirm diagnosability.

**Done means:** live internal systems prove the same contracts already exercised by offline/synthetic tests.

## Gate 4 — v1.0 Release Candidate hardening

### #19 Operational UI — COMPLETE

Production-facing fabricated dashboard values were removed. Management metrics are live tenant-scoped data. Connector Operations UI exists with explicit loading/empty/error states and safe operational metadata.

### #20 Performance/load readiness — IN PROGRESS

**Purpose:** establish repeatable engineering budgets before real pilot scale exposes avoidable query and latency problems.

Work includes:
- remove known N+1/query amplification in list serializers;
- regression tests that query counts do not grow linearly with row count;
- dependency-light HTTP load harness reporting p50/p95/max/error rate/status distribution;
- document how to run read-only load safely against a pilot tenant;
- measure real-host budgets later without claiming GitHub runner latency as production capacity.

### #21 HA/DR and upgrade/rollback — PLANNED PRE-v1

**Purpose:** define how an enterprise deployment survives failures and software upgrades.

Required output:
- reference topology and failure domains;
- DB/object-store/Redis/application recovery expectations;
- upgrade sequence;
- migration safety rules;
- rollback and backup prerequisites;
- rehearsal checklist and evidence template.

### #22 Offline release bundle and support — PLANNED PRE-v1

**Purpose:** make disconnected deployment/install/update/support deterministic.

Required output:
- version-pinned images/packages/manifests;
- checksums and verification instructions;
- SBOM/security artifacts carried with release;
- offline installation/update procedure;
- operator/support handbook;
- troubleshooting and escalation boundaries.

### #8 Independent security validation — AUTOMATED HARDENING COMPLETE, EXTERNAL PROOF PENDING

Automated hardening already covers auth throttling, TOTP replay resistance, CSRF negative paths, cross-tenant IDOR, Evidence quarantine/fail-closed download, export audit, renderer SSRF/local-file boundaries, RAG untrusted-context guardrails, SAST, secret scanning, container scanning and SBOMs.

Remaining:
- independent penetration test;
- real malware scanning workflow or formally accepted operational substitute;
- adversarial testing of configured real AI providers;
- final security sign-off and remediation closure.

## Post-v1 product expansion

Post-v1 priorities discussed and retained:
- TPRM/vendor portal;
- BCM/BIA and continuity workflows;
- incident management;
- continuous control monitoring;
- additional connector packs;
- FAIR/quantitative risk/Monte Carlo;
- advanced regulated document/report templates;
- AI-governance content such as ISO 42001 where authorized;
- digital-transformation maturity packs;
- mobile/PWA approvals.

## Roadmap discipline

A gate is not complete merely because code exists. If acceptance requires a real host, real connector, licensed content or independent validation, the issue stays open until that evidence exists. Conversely, unavailable customer infrastructure must not block unrelated software engineering work that can be completed and tested offline.
