# Disposable replacement-install recovery (separate root and fresh volumes)

Related: #7, #68, #74, and the earlier single-install full-stack DR proof in #124.

## Purpose and hard boundary

Prove that a **different installation checkout** of the identical verified signed release can recover the real PostgreSQL 18 and SeaweedFS Evidence archives onto **previously nonexistent Docker Compose volumes**. This is an intermediate engineering test, not a second physical machine, off-host backup custody, actual air gap, PKI ceremony or field UAT. The source and target share the disposable GitHub-hosted runner's Docker daemon and TLS test hostname; source services are stopped before target ones start. Production acceptance issues remain OPEN.

## Actual test sequence

The existing `ephemeral-real-core-install` workflow still builds the real Django, Next.js, pgvector/Postgres, Redis, SeaweedFS and Nginx image set, signs a source-specific release with ephemeral test-only keys, imports images, boots eight real services over test TLS, and runs the official single-install destructive backup/restore test. **Only after that succeeds**, `scripts/ephemeral-replacement-core-dr.sh`:

1. Requires four independently explicit opt-ins, GitHub-hosted execution, a pristine replacement path, exact Git SHA, protected signed bundle and matching backup name.
2. Stages synthetic backups in a separate mode-0700 temporary custody directory, checks the original via the production `--restore-preflight`. These temporary bytes are not uploaded anywhere.
3. Calls `docker compose down --volumes` on the source Compose project and asserts its Postgres/Redis/SeaweedFS volumes no longer exist. This is intentionally destructive **only** to disposable synthetic CI state.
4. Invokes the canonical signed `offline-release-apply.sh install` with the original trust key but a different installation directory and a different Compose project. Confirms the source Git SHA and privately writable backup directory.
5. Copies the backup to the new checkout and checks the same official restore preflight. Confirms target volumes never existed before restore.
6. Runs official `CONFIRM_RESTORE=YES scripts/datacenterctl restore` against the fresh volumes, with `RESTORE_INITIALIZE_MISSING_BUCKET=YES` explicitly approved. This option is **off by default**: it permits creating only a genuinely missing configured S3 bucket, only for `restore --replace`, **after validating all object archive bytes and source-bucket identity**. Authentication and other S3 failures remain hard errors.
7. Verifies the recovered synthetic SQL marker, exact S3 Evidence payload hash/metadata/key set, production-shaped HTTPS live/readiness, source SHA and signed-install verification. Then shuts down and deletes *target* Docker volumes, source archives, temporary private keys and runner-local custody.
8. Publishes only a short PASS/FAIL summary with limitations, never uploaded backups, customer records, keys, dumps or environment files.

The pre-restore check refuses a corrupt checksum catalog or unsafe backup paths before any SQL replacement. The archive command independently verifies every S3 object before delete. The explicit missing-bucket path must likewise reject corrupt ZIPs, wrong bucket names, missing authorization and inaccessible/forbidden targets.

## First execution finding and production fix

Initial scoped real-stack run [38111905387](https://github.com/esfahanit2-coder/grc-platform/actions/runs/38111905387) **FAILED as designed** rather than reporting an unsupported PASS. It completed exact signed-image installation, canonical source backup and same-install restore, destruction of source containers/volumes, second signed installation and new-volume preflight. The production restore attempted its first `psql` immediately after `docker compose up -d postgres redis objectstore` returned, while the **newly initialized** PostgreSQL 18 volume was not yet ready (`/var/run/postgresql/.s.PGSQL.5432: No such file or directory`). The canonical `pilot-restore.sh` now uses `docker compose up -d --wait postgres redis objectstore`, requiring actual PostgreSQL/Redis health before any database SQL is read or restored. A Django contract test asserts the dependency wait precedes the version probe; the dedicated workflow triggers on future modifications to the canonical restore and S3 archive restore code. A new exact-head run must prove end-to-end recovery, or this remains an unaccepted defect.

## Additional live operator-preflight assertions

After PR #127 adds the Docker-independent `datacenterctl recovery-preflight`, this CI drill now exercises **that exact public command** against real signed-image backups rather than only invoking its Python self-test. The signed single-install test checks that complete, originally valid PostgreSQL/S3/metadata and the exact Git SHA produce `ready_for_operator_review=true`. It then deliberately replaces the target MFA key and requires `critical_config_identity.ok=false` before verifying the *still-running* post-backup SQL and Evidence markers were not destroyed. Separately, tampering with the objectstore ZIP must yield `backup_integrity.ok=false` and leave all application markers unchanged. Once original configuration and archive are restored, the same command must pass again before destructive restore. Finally, the separately signed replacement checkout must also pass this public command **before any destination Docker volume is created**. These are disposable synthetic integration assertions, not customer storage custody or host-isolation evidence.

## Field acceptance still required

Only an approved customer change window and a truly independent replacement host can demonstrate off-host recovery. At the customer, obtain a signed *production* release (actual security scan attestations and approved signing key), a provisioned dedicated restore host, customer-controlled TLS/PKI material and sealed/encrypted offsite backup media. Validate immutable source SHA/PostgreSQL compatibility, access permissions, checksum and independent archive custody; rehearse application login, tenant isolation, evidence download and CSRF; record independent operator-reviewed actual RPO/RTO and rollback result. Keep customer secrets/media out of GitHub and chats.

A GitHub-hosted green workflow **must not** close #7, #8, #68 or #74, certify a disconnected network, prove security attestation, satisfy customer acceptance or trigger an RC/production release. Any failure or timeout requires diagnosis on the same PR, not bypassing checks.
