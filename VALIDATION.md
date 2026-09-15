# Product Hardening & Pilot Validation Report

## Scope

This validation covers the post-Sprint-6 pilot hardening layer: pgvector semantic RAG, read-only evidence connectors, golden end-to-end scenario, pilot deployment compose, release reproducibility gate, and an original redistribution-safe ISMS/security baseline.

## Checks executed in this environment

PASS:
- Static checker passed across Python, TypeScript/TSX, JSON and YAML.
- Python bytecode compilation passed for backend source.
- 249 Python files parsed successfully.
- 38 TypeScript/TSX files parsed successfully.
- 28 migration files are present and all local migration dependency references resolve.
- 20 Django app packages are present.
- Pilot framework JSON parses and contains 16 requirements.
- `docker-compose.yml`, `docker-compose.pilot.yml`, CI and release-gate YAML parse successfully.
- Actual Persian PDF rendering smoke test passed with WeasyPrint (`%PDF` output, non-empty file).
- Release packaging files are checksum-manifested before ZIP creation.

## Product hardening implemented

### Semantic RAG
- PostgreSQL remains the source of truth.
- pgvector extension migration is included.
- Knowledge chunks can hold embeddings plus model/dimension provenance.
- Retrieval supports `lexical`, `semantic`, and `hybrid` modes.
- Semantic retrieval applies tenant and organization scope filtering before similarity ordering.
- Multiple embedding models can coexist during pilot; exact cosine search is used until a production model/dimension is standardized.
- Local Ollama `/api/embed`, OpenAI-compatible `/embeddings`, vLLM/private compatible endpoints, and deterministic Mock embeddings are supported through the provider adapter boundary.

### Connector framework
- Active Directory / LDAP read-only inventory adapter.
- Tenable-compatible read-only scan inventory adapter.
- Veeam Enterprise Manager read-only backup/session evidence adapter.
- FortiGate read-only REST `/api/v2/` collection adapter.
- Connector raw secret values are not stored in DB; DB records only reference environment-variable names.
- Production HTTP connectors require HTTPS and TLS verification.
- HTTP redirects are rejected and response sizes are bounded.
- Connector outputs become ordinary Evidence objects; connectors do not directly declare a control compliant/effective.
- Connector runs are audit-logged and retain success/failure history.

### Pilot lifecycle
- Golden Django test covers Tenant/Organization → Framework/Requirement → Common Control → Control Implementation → Asset → Risk → Inherent/Residual Evaluation → Treatment/Action → Compliance Assessment → Evidence → Finding/CAPA → RTP payload.
- Original pilot security/ISMS baseline is included without reproducing ISO/COBIT/AFTA copyrighted requirement text.

### Release hardening
- Normal CI uses pgvector PostgreSQL 18 for migration/runtime tests.
- Tagged/manual release gate requires a committed `frontend/package-lock.json` and uses `npm ci`.
- Release gate rejects mutable `:latest` image tags in the pilot compose file.
- Pilot compose uses pgvector PostgreSQL and version-pinned infrastructure image tags.
- `.env.pilot.example` ships production-oriented cookie/TLS/security defaults and external secret placeholders.
- `pilot_readiness` management command checks database/pgvector and production security basics.
- `reindex_knowledge` management command builds embeddings for authorized tenant knowledge chunks.

## Runtime checks not executable in this environment

NOT EXECUTED here:
- Django `makemigrations --check` / `migrate`.
- Full Django/DRF test suite against PostgreSQL/pgvector.
- Golden pilot Django test at runtime.
- Connector adapter integration calls to real AD, Tenable, Veeam or FortiGate systems.
- Docker / Docker Compose boot and health checks.
- Next.js lint and production build.
- Celery worker/beat runtime integration.
- Real AI/embedding model calls.

Reason:
- Django, DRF and pgvector Python packages are not installed in this execution environment.
- Docker/Podman are not installed.
- npm registry access timed out, so a trustworthy `package-lock.json` could not be generated here.

These runtime checks are deliberately left to connected CI/pilot infrastructure. No unexecuted runtime check is reported as passed.

## Release blocker

A tagged production release is intentionally blocked until `frontend/package-lock.json` is generated in a connected trusted environment, reviewed, committed, and passes `npm ci` plus the dependency audit. Normal source CI can continue to use `npm install` until then.

## Pilot acceptance recommendation

Do not call the repository production-ready until all of the following pass in the target pilot environment:
1. Full CI on PostgreSQL/pgvector.
2. `python manage.py pilot_readiness`.
3. Golden pilot scenario test.
4. Frontend lint/build.
5. One real scoped AD evidence sync.
6. One real FortiGate or Tenable evidence sync.
7. One real Veeam evidence sync where applicable.
8. Tenant/scope security tests and manual IDOR verification.
9. Local-AI semantic RAG smoke test using approved confidential-data policy.
10. Backup/restore test for database and object storage.
