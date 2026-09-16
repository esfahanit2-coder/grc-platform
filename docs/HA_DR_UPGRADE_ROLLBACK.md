# HA/DR and Upgrade/Rollback Guide

## 1. Purpose and evidence boundary

This guide defines the supported single-host pilot topology, a production-oriented HA/DR reference architecture, failure/recovery ordering, and executable upgrade/rollback rehearsal procedures for the GRC Platform.

It intentionally distinguishes **tested software behavior** from **reference architecture assumptions**.

### Tested in repository automation

The following behavior is or will be exercised by CI/rehearsal tooling:

- PostgreSQL 18 + pgvector migrations from a known previous repository state to a candidate image.
- Exact migration-state baseline capture and integrity hashing.
- Candidate preflight against an exact baseline migration state.
- Detection of migration operations that Django declares non-reversible.
- Fail-closed rejection of a reversible rollback strategy when candidate migration operations are not reversible.
- Reversible schema rollback when the exact migration delta can be reversed.
- Backup/restore rollback rehearsal in a disposable PostgreSQL database when `restore` is the selected strategy.
- A second forward migration after rollback/restore, proving migration repeatability in the disposable environment.
- Backup schema metadata generation and restore compatibility checks.
- Shell syntax and existing pilot compose/TLS validation in the runtime gate.

### Not proven by repository CI

The following require a representative deployment and must not be claimed from GitHub-hosted runners:

- real production/pilot RPO or RTO;
- automatic PostgreSQL failover;
- multi-node object-storage durability/failover;
- Redis Sentinel/Cluster failover;
- load-balancer or DNS failover timing;
- certificate automation/rotation in the customer's PKI;
- local-AI failover or model warm-up time;
- recovery from a host/site/storage/network disaster.

Real clean-host restore and observed RPO/RTO remain acceptance evidence for Issue #7.

## 2. Supported single-host pilot topology

The current executable pilot composition is intentionally simple:

```text
Client
  |
  v
Nginx gateway / TLS
  |----------------------|
  v                      v
Next.js frontend      Django/Gunicorn backend
                         |      |       |
                         |      |       +--> Redis / Celery
                         |      +----------> S3-compatible object storage
                         +-----------------> PostgreSQL 18 + pgvector

Optional: Ollama/local AI on the same private deployment network
```

This topology is suitable for controlled pilot validation and does **not** provide host-level high availability. A failure of the Docker host, local storage, or its network path can affect the complete service.

## 3. Production-oriented HA reference topology

The following is a reference design, not an assertion that the repository deploys/configures these third-party HA mechanisms automatically:

```text
                           +------------------+
Users / internal clients ->| Redundant LB/VIP |<-- DNS / internal PKI
                           +---------+--------+
                                     |
                    +----------------+----------------+
                    |                                 |
             Gateway/App node A               Gateway/App node B
             Next.js + Django                  Next.js + Django
             Celery workers                    Celery workers
                    |                                 |
                    +----------------+----------------+
                                     |
        +----------------------------+----------------------------+
        |                            |                            |
PostgreSQL HA pair/cluster     HA Redis service            Replicated S3-compatible
(primary + replica +           or managed equivalent       object storage
controlled failover)
        |
Independent encrypted backup destination / second failure domain
```

### Reference principles

- Application/gateway/frontend/worker nodes should be horizontally replaceable and hold no authoritative local state.
- Database, object storage and backup destination should not share a single physical failure domain in a production HA design.
- Redis is operational state/cache/queue infrastructure; authoritative GRC business records remain PostgreSQL/object storage.
- A production scheduler must have **one effective Celery Beat leader** unless the scheduling solution provides its own distributed locking/leader election. Running independent Beat instances can duplicate scheduled tasks.
- Local AI can be independent of core GRC availability; failure of an optional AI provider must not make authoritative GRC data unavailable.

## 4. Failure domains and expected operator response

| Failure domain | Authoritative data at risk? | Immediate effect | Recovery/failover direction | Repository proof |
|---|---|---|---|---|
| Gateway/frontend node | No | Browser/API entry point impaired | route to healthy node / replace container | single-node restart behavior only |
| Django app node | No local authoritative state | API degraded | remove unhealthy node, replace instance | container health/restart foundation |
| Celery worker | No local authoritative state | async jobs delayed | replace worker; inspect task idempotency | worker composition only |
| Celery Beat | No business data | scheduled jobs stop or duplicate if multi-active | restore one scheduler leader | reference assumption |
| Redis | Queue/cache/throttle state can be lost | auth throttles, queue/result behavior affected | fail over/restart Redis; reconcile queued work | single-instance readiness only |
| PostgreSQL | **Yes** | core GRC unavailable/inconsistent if mishandled | controlled DB failover or restore | migrations/backup tooling; no HA failover proof |
| Object storage | **Yes** for evidence binaries | evidence/document file access impaired | storage failover or restore | archive/restore logic; no multi-node proof |
| Docker/app host | Potentially all services | complete pilot outage | restore on replacement host | real clean-host proof remains #7 |
| Site/network/PKI/DNS | Depends on architecture | clients cannot reach service | DR/site/network/DNS/PKI procedure | reference only |
| AI provider | No authoritative GRC state | AI assistance unavailable | switch/disable provider | provider abstraction tested; real HA not proven |

## 5. Recovery ordering

When recovering a full deployment, prefer this order unless the incident requires a different documented decision:

1. **Establish infrastructure trust:** host/network, time, DNS, secrets and certificate/key access.
2. **Recover PostgreSQL:** ensure the authoritative relational state is available and internally consistent.
3. **Recover object storage:** evidence/document binaries must correspond to the restored relational metadata boundary.
4. **Recover Redis:** start cache/queue infrastructure only after the authoritative stores are selected.
5. **Validate schema compatibility/migrations:** use `pilot_upgrade_guard` before exposing application writers after a restore/upgrade transition.
6. **Start backend application nodes.**
7. **Start one scheduler leader and workers.**
8. **Start frontend/gateway and validate TLS/browser paths.**
9. **Validate evidence download, login/CSRF, core GRC marker and optional local AI.**
10. **Re-enable integrations/background operations** after the authoritative state and permissions are confirmed.

Do not infer RPO merely from backup duration. Use a controlled application marker and observed restore state during the real drill.

## 6. Backup compatibility metadata

New pilot backups include `schema-manifest.json` generated by:

```bash
python manage.py pilot_upgrade_guard snapshot ...
```

The manifest records:

- release identifier and source commit;
- Django version;
- database vendor/server description;
- all applied migrations;
- the applied migration frontier used as rollback targets;
- migration-state SHA-256;
- whether the database was fully migrated to the code that created the backup.

Normal backup creation refuses to generate this release manifest if migrations are pending. This prevents a backup from silently claiming a release/schema pairing that never actually existed.

`pilot-restore.sh` requires the schema manifest and validates it before destructive restore actions. Legacy backups without this metadata are intentionally not automatically restored by the new script; they require a separately reviewed legacy procedure and the application code appropriate to that backup.

## 7. Upgrade decision process

### Step 1 — identify immutable inputs

Record:

- current/previous image digest or immutable release identifier;
- candidate image digest or immutable release identifier;
- current source commit;
- approved backup identifier;
- intended rollback strategy;
- maintenance/change window owner.

Do not use mutable `:latest` tags for upgrade rehearsal or release decisions.

### Step 2 — create and verify backup

Run the approved pilot/production backup procedure before changing authoritative state. The `restore` rollback strategy requires a verified backup; `pilot_upgrade_guard preflight` refuses it without explicit `--backup-verified`.

### Step 3 — preflight against the exact current schema

The candidate must execute:

```bash
python manage.py pilot_upgrade_guard preflight \
  --baseline /path/to/schema-manifest.json \
  --rollback-strategy reversible|restore
```

The preflight fails if:

- candidate code no longer contains migration definitions required by the baseline;
- the database has migration drift relative to the baseline manifest;
- the migration-to-leaf plan unexpectedly requires backward migration;
- `reversible` was selected but an operation in the candidate migration plan is marked non-reversible;
- `restore` was selected without explicit verified-backup acknowledgement.

### Step 4 — choose rollback path before migration

There are only two supported policy choices:

**Reversible schema rollback** — only when every migration operation in the delta is reversible and the exact delta can be mapped back to the baseline frontier.

**Backup restore rollback** — required when migration reversal is not safe/available. This is slower and must use a verified backup. Do not describe this as an in-place schema rollback.

### Step 5 — quiesce writers and apply candidate

A production change procedure should prevent concurrent writes while crossing a schema boundary unless the exact migration has been deliberately designed/tested for online compatibility. The current pilot backend command automatically runs `migrate` at startup; production upgrade orchestration should therefore control which backend instance is allowed to start first during the migration window.

### Step 6 — validate before reopening traffic

At minimum:

- `python manage.py check --deploy` under production settings;
- core readiness checks;
- migration state has no unexpected pending entries;
- login/MFA/cookie/CSRF path appropriate to deployment;
- representative tenant read/write;
- evidence object metadata/download path;
- worker/scheduler health;
- connector/AI checks required by the change scope.

## 8. Disposable migration rehearsal

Use immutable previous/candidate backend images:

```bash
PREVIOUS_BACKEND_IMAGE='registry.example/grc-backend@sha256:...' \
CANDIDATE_BACKEND_IMAGE='registry.example/grc-backend@sha256:...' \
PREVIOUS_RELEASE_ID='v0.9.0' \
CANDIDATE_RELEASE_ID='v1.0.0-rc1' \
ROLLBACK_STRATEGY='reversible' \
bash scripts/pilot-upgrade-rehearsal.sh
```

The rehearsal:

1. creates disposable PostgreSQL 18 + pgvector;
2. migrates it with the previous image;
3. captures the previous migration baseline using candidate guard logic with explicit `--allow-pending`;
4. creates/verifies a custom-format PostgreSQL backup;
5. candidate-preflights the exact baseline;
6. applies candidate migrations/checks;
7. exercises either reversible schema rollback or baseline backup restore;
8. proves the DB again exactly matches the baseline;
9. reapplies candidate migrations and writes a machine-readable PASS report.

On pull requests that change migration/upgrade paths, `.github/workflows/upgrade-rehearsal.yml` builds the PR base SHA as the previous image and the PR head as the candidate image. Pull-request automation deliberately defaults to `reversible`; an intentional non-reversible migration therefore fails closed instead of silently switching rollback policy. A manually approved workflow run can explicitly select `restore` to exercise the backup-restore path.

## 9. Rollback command guardrails

Schema rollback requires explicit confirmation:

```bash
python manage.py pilot_upgrade_guard rollback \
  --baseline /path/to/baseline-schema.json \
  --confirm ROLLBACK_SCHEMA \
  --dry-run
```

Before execution the guard verifies:

- baseline migrations are a subset of current applied migrations;
- candidate code still contains required migration definitions;
- the generated rollback plan contains no forward steps;
- every migration operation in the plan is reversible;
- the plan exactly equals the migration delta after the baseline.

If any condition fails, use the verified backup restore path rather than forcing migration reversal.

## 10. DNS, TLS and load-balancer assumptions

A production HA topology needs explicit ownership of:

- internal/external DNS TTL and change/failover authority;
- load-balancer/VIP health-check behavior;
- TLS certificate/key storage and renewal;
- SAN/CN names matching the stable service endpoint;
- reverse-proxy forwarding of `X-Forwarded-Proto=https`;
- firewall routes between application and stateful services;
- time synchronization across nodes.

Failing over an application node does not help if the stable DNS/VIP/TLS endpoint still points to an unavailable path.

## 11. PostgreSQL HA assumptions

The application expects a PostgreSQL-compatible authoritative endpoint. A production HA implementation may use an approved PostgreSQL HA solution, but selection/configuration of Patroni, managed database failover, synchronous/asynchronous replication or quorum policy is infrastructure-specific and is not automated by this repository.

Operator policy must document:

- failover authority and fencing/split-brain controls;
- synchronous vs asynchronous replication and resulting data-loss window;
- pgvector extension compatibility on all candidate nodes;
- backup/WAL retention as applicable;
- endpoint/DNS/proxy behavior after promotion;
- when application writers may resume.

## 12. Object-storage DR assumptions

Evidence/document binaries are authoritative data and must receive an independently designed durability/backup policy. An S3-compatible endpoint change is supported by application abstraction, but replication/failover semantics belong to the selected storage platform.

Recovery must avoid claiming success solely because PostgreSQL is healthy while evidence binaries are missing or from an incompatible recovery point.

## 13. Redis recovery assumptions

Redis contains operational cache/queue/result/throttle state, not the authoritative GRC relational record. Loss can still affect:

- pending Celery work;
- result state;
- distributed authentication throttles;
- transient cache state.

After Redis replacement/failover, operators must verify workers, queues and security-throttle behavior. Do not replay unknown non-idempotent tasks blindly.

## 14. Operator decision record

Every production/pilot upgrade or DR event should record:

- previous/candidate release and image digests;
- schema manifest hashes;
- rollback strategy chosen before change;
- backup identifier/checksum status;
- preflight and rehearsal reports;
- maintenance start/end;
- unexpected findings and decision owner;
- restore/failover timestamps where relevant;
- post-change validation;
- measured RPO/RTO only when a real controlled drill/event supports them.

## 15. Relationship to release blockers

This guide/tooling can satisfy the **software and procedural** portion of HA/DR and upgrade/rollback readiness. It does not close real-host recoverability evidence. Issue #7 remains the source of truth for clean-host restore, measured RPO/RTO and real local-AI/no-egress pilot validation.
