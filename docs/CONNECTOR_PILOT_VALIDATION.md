# Connector pilot validation runbook

This runbook covers Issue #6 for the first read-only evidence-collection pilot.

## Scope

Supported connector types:

- Active Directory / LDAP
- FortiGate REST API
- Veeam Enterprise Manager
- Tenable / Nessus API

The repository contains connector implementations and contract tests. A connector is **not** considered live-validated until its health and sync operations succeed against an authorized representative system.

## Security boundaries

- Credentials are referenced only by environment-variable names. Literal secrets must not be stored in `ConnectorConfig`.
- Production HTTP connectors require HTTPS and TLS verification.
- Redirects are disabled.
- HTTP request paths cannot override the configured host.
- FortiGate collection is restricted to configured `/api/v2/` read paths, maximum 10 per run.
- On-premises private RFC1918/ULA addresses are allowed by design.
- Loopback, link-local/cloud-metadata, multicast, unspecified and reserved address classes are rejected.
- Connector response size and request timeout remain bounded by application settings.
- Failed-run messages are redacted against configured credential environment-variable values before persistence/audit.
- Collected connector facts become Evidence only. They do not mark a control effective or a requirement compliant.

## Evidence contract

A successful sync creates one reusable `Evidence` object with:

- tenant and organization-unit scope;
- connector type and connector id;
- connector run id;
- collection timestamp;
- source hostname;
- SHA-256 of the normalized collected payload;
- `collection_mode=read_only`;
- `human_review_required=true`;
- `asserts_compliance=false`.

The evidence can later be linked to an assessment item, control test, workpaper or other supported object through the normal Evidence linking workflow. That linkage does not change the target object's compliance/effectiveness state automatically.

## Required pilot inputs

Do not commit any values below to the repository. Configure secret values only in the approved runtime secret store/environment.

### Active Directory / LDAP

Configuration:

- `configuration.host` or `base_url`
- `configuration.base_dn`
- `configuration.use_ssl` (prefer true)
- optional `configuration.port`, `search_filter`, `attributes`, `size_limit`
- username environment-variable name
- password environment-variable name

Use an account limited to directory read operations required by the configured search.

### FortiGate

Configuration:

- HTTPS `base_url`
- API-token environment-variable name
- optional `configuration.read_paths` under `/api/v2/`

Use a least-privilege API administrator/profile that permits only the required read endpoints.

### Veeam Enterprise Manager

Configuration:

- HTTPS `base_url`
- username environment-variable name
- password environment-variable name

The pilot reads the Enterprise Manager session endpoint, backups and backup sessions.

### Tenable / Nessus

Configuration:

- HTTPS `base_url`
- access-key environment-variable name
- secret-key environment-variable name

The pilot reads scan inventory from `/scans` and stores a bounded summary.

## Live acceptance checklist

For each available pilot system:

1. Create a tenant-scoped connector configuration without literal secrets.
2. Run `health`; confirm success is audited as `connector.health`.
3. Run `sync`; confirm one `ConnectorRun` finishes `succeeded`.
4. Confirm reusable Evidence is created with provenance metadata and payload hash.
5. Link the Evidence through the normal evidence workflow to a relevant control test or assessment item.
6. Verify the target control/assessment remains unchanged until a human performs the normal review/update action.
7. Trigger one controlled failure (for example a deliberately unavailable test endpoint or revoked test credential) and verify the failed run and redacted diagnostic are visible.

## Issue #6 completion rule

Do not close Issue #6 from mocked tests alone. Completion requires live health/sync evidence for each available pilot system and at least three connector types producing reusable Evidence objects against authorized representative infrastructure.
