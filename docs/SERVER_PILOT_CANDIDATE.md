# Real-Server Pilot Candidate

## Purpose

This document is the canonical handoff for installing the GRC Platform **Pilot Server Candidate** on a real clean Linux host.

The candidate is intentionally **Pilot / pre-RC**. A signed bundle, green repository gates and successful installation do not close the external acceptance issues tracked by #5, #6, #7, #8, #40, #42 and #74.

Do not use the development quick-start or build application images on the target server.

## 1. Candidate identity

The real-host Pilot uses an exact source commit and a unique artifact label.

Recommended artifact label:

```bash
SOURCE_SHA="$(git rev-parse HEAD)"
VERSION="v0.9.0-pilot-${SOURCE_SHA:0:12}"
```

This version string is an **artifact identity**, not a Git release tag and not an RC/production approval.

The signed release manifest binds:

- the exact `release_version`;
- the exact 40-character source commit;
- every payload file checksum and size;
- exact Docker image IDs and available repository digests;
- migration/config/model-reference metadata;
- `metadata/server-candidate.json`.

The server-candidate metadata explicitly records that external acceptance is incomplete.

## 2. Real-server profile

Default profile:

- PostgreSQL 18 + pgvector;
- Redis;
- S3-compatible object storage;
- Django backend;
- Celery worker + beat;
- Next.js frontend;
- Nginx TLS gateway;
- Local AI **disabled by default**;
- SMTP disabled until explicitly configured;
- connector credentials absent until explicitly provisioned;
- malware scanning disabled until an approved scanner is configured; Evidence download remains fail-closed while files are not clean.

Optional profile:

- `local-ai` / Ollama runtime.

Third-party model bytes are never embedded in the release package. An approved model must be transferred separately with provenance, license reference and digest.

## 3. Required handoff material

Transfer through approved channels:

1. signed offline release archive;
2. archive SHA-256 file;
3. trusted release public key/fingerprint through an independent trust channel;
4. TLS certificate/private key through the customer PKI process;
5. optional approved local-AI model material;
6. access to encrypted off-host backup storage;
7. target hostname/DNS;
8. any explicitly approved SMTP/connector/scanner configuration.

Never put customer passwords, API tokens, TLS private keys, production `.env`, model credentials or raw Evidence into GitHub.

## 4. Target-host prerequisites

Provision through the organization's normal OS process:

- supported Linux;
- Docker Engine;
- Docker Compose 2.24.4 or newer;
- Git;
- Python 3.12 or newer;
- OpenSSL;
- tar/gzip/sha256sum/find/realpath and normal core utilities;
- approved DNS and NTP;
- enough disk/RAM for the selected Pilot workload;
- encrypted backup storage outside the application data volumes.

Only TCP/443 is required inbound. TCP/80 is optional for HTTP→HTTPS redirect.

Do not publish PostgreSQL, Redis, object-store, backend, frontend or Ollama ports on the host.

## 5. Build the exact candidate on the controlled release workstation

Use the exact commit that has passed exact-head CI and Release Gate.

Retrieve the matching SBOM/security artifacts from the same validated commit, then:

```bash
SOURCE_SHA="<exact-validated-main-sha>"
VERSION="v0.9.0-pilot-${SOURCE_SHA:0:12}"

export OFFLINE_RELEASE_SBOM_DIR=/approved/release-evidence/sbom
export OFFLINE_RELEASE_SECURITY_DIR=/approved/release-evidence/security

bash scripts/offline-release-build.sh "$VERSION" "$SOURCE_SHA"
```

The resulting unsigned stage contains `metadata/server-candidate.json`.

Inspect it before signing:

```bash
cat "artifacts/offline-release/$VERSION/metadata/server-candidate.json"
python scripts/offline-release-manifest.py verify \
  --stage "artifacts/offline-release/$VERSION"
```

## 6. Sign the candidate

Use the controlled Pilot/release signing key outside the repository:

```bash
bash scripts/offline-release-sign.sh \
  "artifacts/offline-release/$VERSION" \
  /secure/offline-signing/release-private-key.pem
```

The private signing key must never be copied to the target application host.

## 7. Verify on the target host before loading images

The trusted public key/fingerprint must be obtained independently from the bundle.

```bash
bash scripts/offline-release-verify.sh \
  "$VERSION-offline-signed.tar.gz" \
  /etc/grc/trust/release-public-key.pem
```

Do not continue if signature, manifest, checksum or payload verification fails.

## 8. Install source and exact images without starting services

```bash
bash scripts/offline-release-apply.sh install \
  "$VERSION-offline-signed.tar.gz" \
  /etc/grc/trust/release-public-key.pem \
  /opt/grc
```

This verifies the bundle again, installs the exact source commit and loads the exact signed image identities.

No service is started yet.

## 9. Place TLS material

Recommended layout:

```text
/opt/grc/secrets/tls/server.crt
/opt/grc/secrets/tls/server.key
```

Protect the private key from group/other access:

```bash
chmod 600 /opt/grc/secrets/tls/server.key
```

The certificate must cover the real Pilot hostname and its issuing CA must be trusted by the host/browser. For a controlled private-CA Pilot, use the documented `GRC_VERIFY_CA_CERT` / `--ca-cert` verifier option.

## 10. Generate the production environment safely

Do not copy the example file and manually invent secrets.

From the installed exact source:

```bash
cd /opt/grc/repository

python scripts/server-pilot-env.py \
  --hostname grc-pilot.customer.example \
  --release-version "$VERSION" \
  --tls-cert /opt/grc/secrets/tls/server.crt \
  --tls-key /opt/grc/secrets/tls/server.key \
  --output .env
```

The generator:

- creates strong random application/database/object-store/MFA/metrics secrets;
- prints no generated secret values;
- writes atomically with mode 0600 and rejects symbolic-link output paths;
- binds hostname/CORS/CSRF/base URL;
- binds the exact release version;
- defaults AI to disabled;
- leaves SMTP and connector credentials disabled/unset.

Enable optional integrations only after their approved secrets/endpoints are provisioned.

## 11. Validate before startup

```bash
bash scripts/datacenterctl validate
```

This validates production mode, explicit hosts/origins, secret shape, secure cookie/redirect posture, Evidence fail-closed policy, TLS file permissions, certificate parse/expiry and certificate↔private-key match.

## 12. Start the exact release

Core profile:

```bash
CONFIRM_INSTALL=YES bash scripts/datacenterctl install
```

The command uses:

- preloaded images only;
- `--no-build`;
- `--pull never`;
- signed release/source/image identity validation;
- TLS gateway;
- migration/readiness checks;
- Django deployment checks;
- external HTTPS live/ready probes.

No application package/image/model is downloaded at startup.

## 13. First tenant/admin bootstrap

```bash
bash scripts/datacenterctl bootstrap \
  --tenant-code pilot \
  --tenant-name "Pilot Organization" \
  --admin-username pilot-admin \
  --admin-email <approved-admin-email>
```

The initial password is read securely from the terminal and is not placed in shell history.

Enroll MFA immediately after first login.

## 14. Full verification

```bash
bash scripts/datacenterctl verify \
  --json-out artifacts/datacenter-verification.json
```

The verifier also revalidates the signed `server_candidate` contract against the installed release version, source SHA and exact image identities. This is supporting evidence for #7 but does not by itself close #7.

## 15. Local AI Pilot

Local AI remains off in the generated production environment until an approved model/provider exists.

After recording model provenance/license/digest and loading the model without exposing Internet egress:

1. set `AI_ENABLED=1` in the protected production env;
2. create the tenant AI provider configuration through the supported product/admin path;
3. start with `DATACENTER_LOCAL_AI=YES`;
4. validate generation + embeddings;
5. validate no-AI mode;
6. validate provider switching;
7. retain only approved low-risk evidence.

Do not add model bytes to the signed application bundle.

## 16. Backup and destructive restore

Create a controlled pre-backup marker/Evidence object, then:

```bash
bash scripts/datacenterctl backup pilot-drill-001
```

Immediately copy the protected backup directory to approved encrypted **off-host** storage.

Create a post-backup marker, then execute the approved restore:

```bash
CONFIRM_RESTORE=YES bash scripts/datacenterctl restore pilot-drill-001
```

Prove:

- pre-backup marker restored;
- post-backup marker absent;
- Evidence checksum preserved;
- PostgreSQL/object store/application healthy;
- observed RTO measured from the real restore;
- RPO measured from the controlled marker boundary.

Do not infer RPO/RTO from CI or script duration alone.

## 17. Combined Pilot acceptance session

Use this exact candidate for:

- #7 clean-host/TLS/recovery/local-AI evidence;
- #42 genuine running Persian dashboard screenshots;
- #6 authorized live connector evidence for at least three connector types;
- #8 target-environment security/scanner/pentest evidence;
- #74 final operator/customer UAT.

If a release-impacting code change is merged after evidence collection begins, freeze a new exact candidate and repeat the impacted acceptance evidence.

## 18. Exit from Pilot Candidate

Do not promote an RC/final tag merely because installation succeeds.

Promotion remains blocked until the applicable external gates are complete and `scripts/final-release-acceptance.py --require-complete` reports `promotion_ready=true`, followed by named human review of the referenced evidence.
