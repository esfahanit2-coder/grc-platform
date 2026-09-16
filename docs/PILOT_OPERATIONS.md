# Clean-host pilot operations runbook

This runbook is the execution record for Issue #7. It distinguishes repository/CI readiness from observations that must be measured on an actual pilot host.

## Current validation boundary

The repository can prove configuration syntax, application tests, object-archive round trips, AI provider switching/disable behavior and security gates in CI. It cannot prove clean-host timing, host networking, real certificates, real backup media throughput or a local model until those are exercised on the target environment.

Do not close Issue #7 until the **Measured pilot observations** section is populated from a real drill.

## Runtime composition

`docker-compose.pilot.yml` provides:

- PostgreSQL 18 + pgvector;
- Redis with append-only persistence;
- bundled S3-compatible object storage using pinned SeaweedFS 4.47;
- Django backend;
- Celery worker and beat;
- Next.js frontend;
- Nginx gateway;
- optional pinned Ollama 0.34.1 under the `local-ai` profile;
- an `ops` profile used only for backup/restore commands.

The Django application still talks only to the S3 abstraction. An approved external S3-compatible service can replace the bundled object store through `.env` without changing domain code.

## 1. Clean-host prerequisites

Prepare a Linux host with:

- Docker Engine and Docker Compose v2;
- enough disk for PostgreSQL, evidence objects, container images, backups and optional local models;
- DNS/name resolution for the chosen GRC hostname;
- an approved TLS certificate and private key;
- encrypted backup storage separate from the application data volumes;
- no inbound exposure of PostgreSQL, Redis, object storage or Ollama ports.

Copy the repository at the release commit to the host. Do not copy a developer `.env`.

## 2. Production environment file

```bash
cp .env.pilot.example .env
chmod 600 .env
```

Replace every placeholder secret and set the real hostname/origin values. In particular verify:

- `DJANGO_SECRET_KEY`;
- `POSTGRES_PASSWORD`;
- `S3_ACCESS_KEY` / `S3_SECRET_KEY`;
- `MFA_ENCRYPTION_KEY`;
- `DJANGO_ALLOWED_HOSTS`;
- `CORS_ALLOWED_ORIGINS`;
- `CSRF_TRUSTED_ORIGINS`.

For the bundled object store keep:

- `S3_ENDPOINT_URL=http://objectstore:8333`;
- `S3_USE_SSL=0`.

This HTTP hop stays on the private Compose network. User/browser traffic must use the TLS gateway.

## 3. TLS gateway

Keep certificate material outside Git, for example:

```text
runtime/tls/server.crt
runtime/tls/server.key
```

Set permissions according to the host security policy and set `TLS_CERT_PATH` / `TLS_KEY_PATH` in `.env` if different.

Validate the merged Compose configuration before startup:

```bash
docker compose --env-file .env \
  -f docker-compose.pilot.yml \
  -f docker-compose.pilot.tls.yml \
  config >/dev/null
```

Start the core stack:

```bash
docker compose --env-file .env \
  -f docker-compose.pilot.yml \
  -f docker-compose.pilot.tls.yml \
  up -d --build --wait
```

Verify that HTTP redirects to HTTPS and that browser/API traffic presents the approved certificate. Confirm authentication cookies are `Secure`, CSRF requests succeed only for the configured trusted origin, and the backend sees `X-Forwarded-Proto: https`.

## 4. Dependency readiness

Run the non-destructive probe from the backend container:

```bash
docker compose --env-file .env -f docker-compose.pilot.yml \
  exec -T backend python manage.py pilot_readiness
```

A final pilot acceptance run must show:

- PostgreSQL reachable;
- pgvector enabled;
- Redis reachable;
- configured S3 bucket reachable;
- production secure-cookie checks passing.

Review service state and recent logs:

```bash
docker compose --env-file .env -f docker-compose.pilot.yml ps
docker compose --env-file .env -f docker-compose.pilot.yml logs --tail=200 backend worker beat frontend gateway objectstore
```

## 5. Local AI / air-gapped inference

AI is globally switchable with `AI_ENABLED` and provider selection remains tenant configuration.

Start the optional local service:

```bash
docker compose --env-file .env -f docker-compose.pilot.yml \
  --profile local-ai up -d --wait ollama
```

The stack deliberately does **not** download a model at startup. For an air-gapped deployment, preload approved model artifacts/volumes from controlled offline media before the final isolation test. Configure a tenant `AIProviderConfig` with:

- `provider_type=ollama`;
- `base_url=http://ollama:11434`;
- an approved preloaded chat model in `model_name`;
- `configuration.embedding_model` set to an approved preloaded embedding-capable model;
- `allow_confidential=true` only after the local deployment is approved for that classification.

Then run a real generation + embedding smoke test:

```bash
docker compose --env-file .env -f docker-compose.pilot.yml \
  --profile local-ai exec -T backend \
  python manage.py pilot_readiness --ai-provider-id <AI_PROVIDER_CONFIG_UUID>
```

For the no-AI mode, set `AI_ENABLED=0`, recreate backend/worker, and verify AI calls are rejected while ordinary GRC functions remain usable. To switch from Ollama to vLLM/private/OpenAI-compatible, change the tenant provider configuration; domain modules must not change.

For the confidential-data acceptance test, disconnect/block internet egress after the approved model is loaded and repeat the smoke test.

## 6. Backup

Before the drill, create a controlled application marker (for example a clearly named test Evidence or Action) and record its timestamp.

Run:

```bash
bash scripts/pilot-backup.sh pilot-drill-001
```

The backup directory contains:

- `postgres.dump` — PostgreSQL custom-format dump;
- `objectstore.zip` — portable S3-level archive with per-object SHA-256 values;
- `config.env` — **secret-bearing** deployment configuration;
- Compose/source/image manifests;
- `SHA256SUMS`;
- `backup-observation.json`.

`backups/` is Git-ignored. Copy the completed directory to approved encrypted backup media separated from the application volumes. TLS private keys are intentionally not copied by the script; recover them through the approved PKI/key-recovery process.

After backup completion, create a second clearly named marker. This marker is expected **not** to exist after restoring the earlier recovery point.

## 7. Destructive restore drill

Use a clean/replacement pilot environment when possible. Restore requires explicit approval:

```bash
CONFIRM_RESTORE=YES RESTORE_CONFIG=YES PILOT_TLS=YES \
  bash scripts/pilot-restore.sh pilot-drill-001
```

If the drill also includes local AI and the restored database already contains the provider configuration:

```bash
CONFIRM_RESTORE=YES RESTORE_CONFIG=YES PILOT_TLS=YES PILOT_LOCAL_AI=YES \
AI_PROVIDER_ID=<AI_PROVIDER_CONFIG_UUID> \
  bash scripts/pilot-restore.sh pilot-drill-001
```

The restore script:

1. verifies `SHA256SUMS`;
2. requires explicit destructive confirmation;
3. stops application writers;
4. restores PostgreSQL with `pg_restore`;
5. restores the object bucket only with explicit replacement mode;
6. starts the application and waits for health;
7. runs `pilot_readiness`;
8. writes `restore-observation.json` with observed time from application stop to readiness.

After restore, manually prove:

- the pre-backup marker exists;
- the post-backup marker does not exist;
- at least one evidence file can be downloaded and its application SHA-256 still matches;
- login, secure-cookie and CSRF flows work through HTTPS;
- scheduled/background processing works;
- local AI generation/embedding works with internet egress disabled when local AI is in scope.

## 8. RPO / RTO measurement

Do not estimate these values in advance.

- **Observed RTO:** use `observed_rto_seconds` written by the restore script, then add any manual validation time required by the organization's definition of service recovery.
- **Observed RPO:** compare the timestamp/state of the controlled marker immediately before the backup with the restored state. Record the real recoverable cutoff and any data intentionally created after that cutoff.

## Measured pilot observations

| Item | Actual result | Evidence / notes |
|---|---|---|
| Clean host / OS | NOT_MEASURED | Populate during target-host drill |
| Release commit | NOT_MEASURED | Record exact Git SHA |
| Core services healthy | NOT_MEASURED | Attach `docker compose ps` + readiness output |
| HTTPS / secure cookie / CSRF | NOT_MEASURED | Record browser/API checks |
| Backup duration | NOT_MEASURED | `backup-observation.json` |
| Restore RTO | NOT_MEASURED | `restore-observation.json` |
| Restore RPO | NOT_MEASURED | Controlled marker evidence |
| Object evidence restored | NOT_MEASURED | Record object/evidence id + checksum |
| Local AI offline | NOT_MEASURED | Provider/model + no-egress test |
| AI disable/provider switch | NOT_MEASURED | Record tested configurations |
| Operational gaps | NOT_MEASURED | Convert unresolved items into tracked issues |

Issue #7 stays open until these real observations meet the acceptance criteria.
