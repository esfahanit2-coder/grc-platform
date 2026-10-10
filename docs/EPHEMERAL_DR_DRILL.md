# Disposable PostgreSQL + S3 recovery integration test

Related: Issues #7, #68, #74.

This targeted GitHub-hosted integration test uses actual disposable Docker PostgreSQL 18, Redis and SeaweedFS S3 services, with only synthetic database rows and Evidence objects. It provides an intermediate engineering signal between fake-S3 unit tests and real customer datacenter acceptance.

## Execution boundary

The test is isolated behind GITHUB_ACTIONS=true and GRC_DR_EPHEMERAL_ONLY=YES. It refuses to overwrite any existing .env, uses its own Compose project, generates temporary credentials, omits AI/connectors and removes volumes, backup files and secrets at exit. No database dumps, .env, object archives or service logs are uploaded as artifacts.

The ephemeral-synthetic-dr workflow runs only on pull requests changing its workflow or integration script, or through manual dispatch. It does not duplicate routine full CI on every PR.

## Tested with real dependencies

1. Start the pinned PostgreSQL, Redis and S3 services; run Django migrations with the backend ops container.
2. Write pre-backup SQL marker and S3 Evidence object with metadata.
3. Perform actual pg_dump custom-format backup and the real pilot_objectstore_archive export.
4. Generate **synthetic CI** metadata and run the production restore-preflight against genuine dump/archive bytes.
5. Write post-backup markers. Attempt a corrupt ZIP restore; assert that existing S3 objects are not deleted.
6. Execute pg_restore and Django S3 archive restore --replace.
7. Assert pre-backup records and object bytes/metadata survived, post-backup data disappeared, and the original backup still passes preflight.

Exit is nonzero on any failed assertion. The GitHub Job Summary contains only synthetic PASS/FAIL conclusions and disclaimers.

## Strict limitations

This does NOT prove signed offline bundle installation, full frontend/worker/gateway restore, TLS/PKI, customer-held encryption keys, authentication, protected recovery media, restore atomicity, customer UAT or measured RPO/RTO. To conserve runner resources it builds only the backend operations image.

No synthetic CI report or manifest should be used as Issue #7 customer field evidence. Issue #7 remains OPEN until real approved clean/replacement host testing using the full signed install and restore runbooks, controlled before/after markers, application Evidence checksum and operator-reviewed measured RPO/RTO.

A runner disk, image download or timeout failure is INCOMPLETE, not PASS; investigate the scoped job without weakening the production release gate.
