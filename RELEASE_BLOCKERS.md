# Release blockers

The repository remains a **Pilot Candidate**. This file distinguishes checks already proven by repository CI from validation that still depends on a real deployment, licensed content, or independent review.

## Cleared by repository/runtime gates

- `frontend/package-lock.json` is committed and frontend builds use `npm ci --ignore-scripts`.
- PostgreSQL 18 + pgvector migrations run from an empty database in CI.
- Full Django tests, Golden E2E and connector contract tests pass in the reusable runtime gate.
- Next.js typecheck, lint and production build pass.
- Dependency audit, Bandit high-severity SAST, repository secret scan, backend/frontend Trivy HIGH/CRITICAL image scans and CycloneDX SBOM generation are enforced by the release gate.
- Release composition rejects mutable `:latest` application image tags.
- Deterministic negative-path tests cover key tenant/authorization, MFA replay, CSRF, IDOR, evidence quarantine, report-fetch and RAG boundaries.

## Remaining before v1.0 RC / production rollout

1. **Authorized content (#5):** complete the real ISMS source path, rights/provenance record and human-approved AFTA/ISMS/internal crosswalk without unauthorized redistribution.
2. **Live connector proof (#6):** run health/sync against authorized AD/LDAP, FortiGate, Veeam and Tenable/Nessus systems; at least three connector types must create real reusable Evidence.
3. **Clean-host operations proof (#7):** execute clean install, real TLS/cookie/CSRF validation, backup/restore drill, measured RPO/RTO and no-egress local-AI proof.
4. **Security validation (#8):** complete/schedule independent penetration testing, validate a real malware-scanner workflow and document final security sign-off.
5. **Operational UI (#19):** remove production-facing demo dashboard data and expose connector operations safely.
6. **Performance/load readiness (#20):** establish repeatable load scenarios and pilot engineering budgets without treating CI runners as production capacity proof.
7. **HA/DR + upgrade/rollback (#21):** document topology assumptions and rehearse release migration/rollback behavior.
8. **Offline release/support (#22):** build deterministic offline release verification/install flow and operator support handbook.
9. Run `python manage.py check --deploy` using the actual target production environment and approved secrets/TLS settings.
10. Pin all production infrastructure/application images to organization-approved versions or immutable digests for the final deployment manifest.

## Content/legal boundary

Do not bundle proprietary ISO/COBIT/AFTA text unless the distribution/use license explicitly permits embedding that content in the product. Customer-provided restricted content remains tenant-scoped unless broader rights are documented.
