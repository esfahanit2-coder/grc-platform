# Ephemeral signed install of real GRC core services

Related: #7, #68, #74. This is a narrowly scoped engineering bridge beyond the all-synthetic signed installer in PR #122 and beyond the SQL/S3-only DR integration in PR #121.

## Procedure

When the test script or dedicated workflow changes (or when manually dispatched), an isolated GitHub-hosted Ubuntu runner:

1. Builds the **real** Django/DRF and Next.js/React application images from the exact tested source commit, and pulls the pinned production PostgreSQL/pgvector, Redis, SeaweedFS and Nginx images.
2. Substitutes only the **unused optional Ollama image role** with an explicitly marked tiny synthetic placeholder to avoid several GB of unrelated AI runtime. Local-AI profile stays disabled.
3. Creates role-specific Docker image archives and a source Git bundle, records actual image IDs and a candidate manifest, and signs the manifest using a runner-local temporary RSA key. The security-evidence manifest here is **explicitly test-only** and empty; it is not a security attestation or an approved offline release artifact.
4. Removes source image tags to prove actual Docker archive loading at install time.
5. Generates disposable test hostname, local self-signed TLS certificate and fresh production-shaped secrets with the existing generator. Nothing is uploaded.
6. Calls the unchanged official offline release installer in preload-only mode, then calls normal `datacenterctl install`. AI remains off. Exercises actual Docker Compose health, Django migration/deployment readiness, frontend and secure gateway.
7. Asserts real core services, signed release identities and machine-readable verification passed. Destroys containers, Docker volumes, keys, synthetic data and staged files.

A nonzero result is **FAIL/INCOMPLETE** and requires diagnosis. This is deliberately separate from the normal expensive release-gate security scan and only runs when its own test is changed or manually triggered.

## Exact scope and limits

This is **not** the production `offline-release-build.sh` output, cannot replace the required SBOM/scan-provenance check, is **not** a disconnected network (image builds/pulls use internet), and does not test licensed Ollama or a locally loaded AI model. The runner's one-day certificate is test-only, not customer PKI; neither customer operators, customer data, independent penetration testing, destructive full-stack backup/restore, encrypted off-host custody nor measured RPO/RTO are tested.

CI work on hosted runners does not demonstrate that an approved clean on-premise host can be provisioned/operated. Do not mark #7/#8/#74 complete and do not publish or promote a release based on this job. Use the documented production build/sign/custody workflow and independent acceptance evidence.

Safety: requires explicit CI-only environment guard, refuses an existing checkout .env, uses a unique Compose project and fresh temporary paths; cleans up in an EXIT trap. No environment files, TLS keys, dumps, bundle, raw logs or other secret-bearing items are attached as GitHub artifacts.

## Findings from first real-core CI execution

The first test run (workflow run `38081610882`) built and signed real images, imported them from signed archives, and booted PostgreSQL and Redis successfully, but Docker Compose stopped because the Django backend healthcheck was unhealthy. The existing readiness probe connected to `127.0.0.1` and sent the default `Host: 127.0.0.1:8000`, while the production environment generator sets a restrictive `DJANGO_ALLOWED_HOSTS` with only the approved FQDN. Django correctly rejects unapproved Host headers. The fix sets **only the local probe's Host header** to the first approved `DJANGO_ALLOWED_HOSTS` entry while connecting to loopback; it does **not** expand Django's allowed-host policy, disable HTTPS redirect or weaken proxy/CSRF configuration.

A subsequent exact-head real-runtime run is required to confirm this diagnosis. A successful static syntax check alone must not be counted as successful live backend startup. Preserve this regression finding with the associated CI run in Issues #7/#68.
