# Ephemeral signed real-core backup and destructive recovery drill

Relates to Issues #7, #68 and #74. This is a disposable engineering integration checkpoint, NOT real disaster recovery evidence or an approved production release.

## What actually runs

The existing scoped `ephemeral-real-core-install` workflow, on its targeted changes or manual dispatch, builds and signs a temporary source-specific **real application** core image set, imports signed local images, installs the app, and proves it is healthy under ephemeral self-signed HTTPS. With `GRC_CORE_DR_EPHEMERAL_ONLY=YES` the same runner then:

1. Creates synthetic PostgreSQL table rows and an S3 Evidence object with known bytes/content-type/metadata; no accounts/customer data are loaded.
2. Calls the official `datacenterctl backup` (not a reimplementation) with quiesced application writers, capturing actual `pg_dump`, SeaweedFS archive, environment/image/manifest catalog and checksum bundle.
3. Calls the official non-destructive `--restore-preflight`, then mutates the database and writes a new S3 object **after** the snapshot.
4. Corrupts the backup's object archive while keeping a CI-local copy. Proves restore preflight and the official `datacenterctl restore` both fail **before** destructive operations and that later SQL/S3 markers still exist.
5. Returns the original archive bytes, runs `--restore-preflight` again, then explicitly authorizes the **real official destructive** `datacenterctl restore`. The operator script checks PostgreSQL major version, restores DB, checks/audits migration plan, applies migrations, restores S3 archive, and brings up backend/worker/beat/frontend/gateway.
6. Verifies pre-backup SQL marker, S3 Evidence payload SHA-256 and metadata survive; confirms post-backup DB/S3 mutations are absent.
7. Calls `datacenterctl verify` again, checks the original backup, checks restore source commit, and only records the synthetic wall-clock duration as a CI observation with customer RPO unset.
8. Scrubs all temporary files, containers, local volumes and keys in the parent script EXIT trap; the entire runner is disposable. No backup archives, environment files, image tarballs or secrets are uploaded as GitHub artifacts.

## First-run finding and remediation

The initial scoped full-stack run (GitHub Actions run `38083547253`) built and installed the actual signed images and passed real core startup and initial SQL/S3 synthetic markers, but the official backup stopped immediately when it could not create `repository/backups/<name>`: `Permission denied`. The ops container bind mount `./backups:/backups` had created the missing host directory as Docker's root user during the earlier test marker, making it unwritable by the non-root offline-install operator. The **canonical offline installer** now explicitly creates an operator-owned, private mode-0700 `repository/backups` directory as part of clean installation, before any ops container can mount it. The full-stack script also asserts this directory exists, is not a symlink, is writable and has mode 0700 before startup. This is a clean-host operational defect, not a change to Docker daemon permissions or an excuse to run backup with privileged sudo. The next exact-head test must prove the remedy.

## Bounded runtime and controls

- Outer and inner scripts require `GITHUB_ACTIONS=true` plus separate `GRC_CORE_INSTALL_EPHEMERAL_ONLY=YES` and `GRC_CORE_DR_EPHEMERAL_ONLY=YES`. Scripts reject existing checkout .env, source-SHA mismatch or reused backup name.
- Local-AI/Ollama is disabled and its optional signed role is deliberately synthetic, as documented in `EPHEMERAL_REAL_CORE_INSTALL.md`.
- Runner network access is used to fetch/build images; customer air-gapped operation, external PKI and release-signing custody are **not** proven.
- The backup contains ephemeral secrets and stays inside the GitHub runner. In customers' datacenters it MUST instead be moved to approved encrypted/off-host custody and tested on a separately provisioned restore host.
- No tenant functional user journey, authentic customer data/evidence, independent penetration testing, adversarial DR, measured customer RPO/RTO, locality controls or UAT is provided.
- All CI reports retain `pilot-pre-rc` and `release-ready` boundaries. **Do not close** Issues #7, #8, #68 or #74 or describe the product as Production Ready based on this result.

A FAIL, timeout or insufficient disk means **incomplete**; do not waive. If an actual code defect is exposed, fix in the same PR and rerun on the latest exact head.
