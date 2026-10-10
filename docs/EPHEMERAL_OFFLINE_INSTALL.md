# Disposable signed offline-installer contract test

Related issues: #68, #7, #74. This test is intentionally narrower than a complete clean-host pilot. It exercises the existing production `offline-release-sign.sh`, `offline-release-verify.sh` and `offline-release-apply.sh install` tools using a signed **synthetic** package and real local Docker archive load. It does not change the operator install interface.

## Execution and cost

- Run the `ephemeral-offline-install` GitHub Actions workflow manually or for PRs that modify its script/workflow or selected signed-release tools.
- Test environment is a disposable GitHub-hosted runner with a working Docker daemon. Explicit guard: `GITHUB_ACTIONS=true` and `GRC_OFFLINE_EPHEMERAL_ONLY=YES`.
- Create one tiny local OCI/Docker image from a synthetic rootfs tar and tag/save it under all seven required release roles. **The synthetic image is not a GRC application or runtime.**
- Use the existing metadata generators, source Git bundle, deterministic manifest, RSA test signing key (outside repository), detached signature and SHA-256 verification.
- Assert wrong trusted public key and post-signing source bundle tampering are rejected by the real installer before creating their target installation roots.
- Successfully call the normal installer in preload-only mode, verify installed exact source commit, signed manifest, all seven image IDs and absence of an application `.env`.
- Delete all temporary keys, source bundles, staged artifacts and Docker image tags after the test. Nothing secret-bearing is uploaded as an artifact.

The exercise does not pull image registries or start the GRC services. It is **not an enforced network-isolated/air-gapped test**; the hosted runner is still Internet-capable.

## What PASS means

The signed package trust boundary, release Git source handoff and container image load/install path have been exercised together with real Git, OpenSSL, tar and Docker on an ephemeral runner. Both negative-path install attempts must leave their target directories absent.

## What PASS does not mean

This job never executes the backend, frontend, worker, beat, gateway, database, TLS, MFA or Evidence UI. Its tiny synthetic image cannot prove real production image compatibility, complete services startup, network isolation, customer PKI, secure backup custody, production upgrade/rollback, actual disaster recovery or measured RPO/RTO.

Real installation using the signed **actual GRC images** and approved OS/host prerequisites, end-to-end recovery, security evaluation and UAT remain outstanding external release acceptance under #7/#8/#74. Keep those issues open.

If GitHub runner disk, Docker availability or the test assertion fails, the result is FAILED/INCOMPLETE, not an acceptance waiver.
