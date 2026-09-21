# Datacenter operator guide

This guide is the operator-facing implementation record for Issue #73. It builds on the existing offline release, upgrade, backup and recovery contracts instead of defining a second deployment architecture.

## 1. Scope and proof boundary

The repository is responsible for producing an exact, integrity-checked application release; validating production configuration; installing without Internet package/model downloads; bootstrapping the first tenant administrator through normal tenant RBAC; verifying the installed stack; collecting secret-minimized support evidence; and providing explicit upgrade/rollback procedures.

A repository or CI run does **not** prove customer-site capacity, HA failover, storage durability, network reachability, PKI operations, or real RPO/RTO. Those remain environment evidence. Clean-host installation, destructive restore and measured RPO/RTO remain acceptance work under Issue #7.

## 2. Host prerequisites

Provision the host through the customer's normal operating-system process before transferring a release. The operator tooling expects:

- supported Linux and the organization's current security baseline;
- Docker Engine with a reachable daemon;
- Docker Compose v2;
- Git;
- Python 3;
- OpenSSL;
- `tar`, `gzip`, `sha256sum` and normal core utilities;
- approved DNS/NTP and internal routing;
- sufficient local or attached storage for container images, PostgreSQL, object storage and retained backups;
- the organization's trusted release public key delivered independently of release media;
- an approved TLS certificate/private key and CA chain where applicable.

No datacenter script installs OS packages from the Internet.

Run the host/configuration preflight before starting services:

```bash
python scripts/datacenter-preflight.py --env-file .env --tls --json
```

The command reports key names and check status only. It never prints secret values.

## 3. Network and firewall expectations

The normal production exposure is the gateway only. With the TLS compose override the host publishes TCP/80 and TCP/443. TCP/80 exists for the approved redirect/health behavior; user traffic should terminate on TCP/443.

PostgreSQL, Redis, SeaweedFS/S3, backend, Celery worker/beat and the optional local-AI runtime are Compose-internal by default and must not be exposed to untrusted networks. If a customer substitutes approved external PostgreSQL, Redis, S3, SMTP, directory, connector or AI services, allow only the specific outbound/internal flows required by those configured endpoints.

For the production metrics endpoint, route access only from the approved monitoring network and keep `OPS_METRICS_TOKEN` in the deployment secret store. Connector firewall rules are customer-specific because the product intentionally does not assume a universal AD/FortiGate/Veeam/Tenable topology.

## 4. TLS / PKI

Private keys are never committed or embedded in the release bundle. Set `TLS_CERT_PATH` and `TLS_KEY_PATH` to protected files provisioned by the customer's PKI process. The preflight verifies that both files exist, the certificate parses and is not expired, and the private key parses. Certificate trust, issuance, renewal, revocation and private-key custody remain the customer's PKI responsibility.

Do not work around certificate validation in acceptance tooling. For a private CA, provide the CA certificate to the verification command:

```bash
python scripts/datacenter-verify.py \
  --env-file .env \
  --base-url https://grc.example.internal \
  --tls \
  --ca-cert /etc/grc/trust/customer-ca.pem \
  --json
```

## 5. Production environment validation

Start from `.env.pilot.example`, store the resulting production file outside source control, restrict it to the deployment owner (`0600` or stricter), and replace every placeholder. `scripts/datacenter-preflight.py` fails closed for missing required production values, placeholder markers, insecure cookie/redirect settings, malformed MFA key material, contradictory SMTP transport settings, missing host prerequisites, or invalid TLS material when TLS validation is requested.

The current Compose filename retains `pilot` for compatibility with the already-tested deployment/backup tooling. #73 treats it as the controlled single-host datacenter package; the filename is not a claim of HA.

## 6. First tenant and administrator

Do not use Django `createsuperuser` as the application bootstrap path. The first administrator must enter through the same tenant membership and RBAC model used by the product.

Provide the password through the process environment so it is not placed in command history:

```bash
export GRC_BOOTSTRAP_ADMIN_PASSWORD='use-customer-secret-delivery-process'
docker compose --env-file .env -f docker-compose.pilot.yml exec -T backend \
  python manage.py bootstrap_datacenter \
    --tenant-code customer-a \
    --tenant-name 'Customer A' \
    --admin-username grc-admin \
    --admin-email grc-admin@example.internal \
    --json
unset GRC_BOOTSTRAP_ADMIN_PASSWORD
```

The command is idempotent for the same tenant/user identity, creates a normal active user, bootstraps the standard `tenant_admin` role with whole-tenant scope, and refuses to silently claim an unrelated existing user, reactivate disabled identities, or mutate a tenant whose identity fields do not match the requested bootstrap.

## 7. Installation verification

After installation, run the machine-readable verification gate:

```bash
python scripts/datacenter-verify.py \
  --env-file .env \
  --base-url https://grc.example.internal \
  --tls \
  --ca-cert /etc/grc/trust/customer-ca.pem \
  --json > installation-verification.json
```

A passing result requires:

- host/configuration preflight success;
- all required Compose services running;
- database + pgvector, Redis and S3/object storage readiness;
- no pending Django migrations;
- public API live and ready endpoints reachable through the deployed gateway;
- a fresh beat → broker → worker operational heartbeat;
- production security expectations such as secure cookies, SSL redirect, CSRF origins, non-default secrets and metrics token configuration.

The output is intended to be retained as installation evidence. It contains status and bounded technical metadata, not credential values.

## 8. Backup, upgrade and rollback

Use the existing controlled scripts and `docs/HA_DR_UPGRADE_ROLLBACK.md` as the normative recovery contract.

Before an upgrade, validate configuration and target artifacts, confirm current readiness, rehearse/audit the migration plan, create a release-consistent quiesced backup, retain the previous signed release, and assign a rollback owner. The upgrade script rechecks migration safety against the exact target image before applying migrations.

Rollback is **not** defined as “run the old image.” If an upgrade fails before schema migration begins, the prior application containers may be restarted. Once schema migration begins, rollback is backup-based: restore the compatible PostgreSQL state and matching object-storage archive using the source release recorded in the backup manifest. Application-only rollback is acceptable only when no incompatible persistent-state change has occurred and that fact is established by the release/migration contract.

Do not delete the pre-upgrade recovery set until the release observation window is formally closed.

## 9. Support package

Collect the default support package with:

```bash
bash scripts/support-evidence.sh
```

The bundle contains version/source identity, Docker/Compose versions, disk usage, service state, image references, configuration-schema/preflight status, migration plan, readiness, operational status and at most 200 allowlisted ERROR/CRITICAL metadata records.

The log filter deliberately removes the free-form `message` field. Raw service logs, `.env` values, credentials/tokens, TLS key/certificate bytes, database dumps, object-store contents, customer records, Evidence payloads and AI prompts/responses are excluded by design. If deeper logs are required for an incident, review and redact them inside the customer's security boundary before any transfer.

## 10. Provisional sizing guidance

Until target-host benchmarks and real usage observations exist, sizing is a topology and isolation decision rather than a synthetic vCPU/RAM promise. Do not convert these profiles into contractual capacity numbers without measurement.

| Profile | Appropriate starting topology | Primary scaling/validation focus |
| --- | --- | --- |
| Small | Single controlled host with bundled PostgreSQL, Redis, object storage, backend, worker/beat, frontend and gateway. Local AI disabled or separately assessed. | Disk durability, backup window, concurrent interactive users, evidence volume and worker backlog. This is not HA. |
| Medium | Separate or organization-managed PostgreSQL/object storage; dedicated Redis where required; more than one stateless application/worker process where the platform is deployed behind customer ingress. | DB I/O, object throughput, worker queue depth, reporting/import peaks, backup/restore duration and failure-domain separation. |
| Large / Enterprise | Customer HA ingress, replicated stateless app tier, worker pool, approved PostgreSQL HA, HA Redis, replicated S3-compatible storage, isolated backup target; optional AI on separately sized compute/GPU. | Measured peak concurrency, evidence growth, connector schedules, AI workload, node-loss behavior, failover, restore performance and operational staffing. |

For all profiles, PostgreSQL and Evidence/object storage are recovery-critical together. Redis is operationally important but not the authoritative GRC record store. Celery worker count should follow measured queue depth and task latency rather than an invented fixed number. Optional AI capacity must be benchmarked independently because model/runtime/hardware choice can dominate resource needs.

## 11. Acceptance handoff

Before customer UAT, retain these artifacts together:

- approved signed release media and trusted-key fingerprint record;
- production configuration validation result (without secret values);
- installation verification JSON;
- bootstrap result showing a normal tenant administrator, not a Django superuser;
- current backup result and restore-drill evidence when #7 is executed;
- upgrade/rollback change record if applicable;
- support package from the deployed release;
- environment-specific network/PKI/HA evidence owned by the customer team.

Issue #74 is the final datacenter release acceptance gate. Issue #7 remains the clean-host, destructive restore, RPO/RTO and local-AI proof gate.
