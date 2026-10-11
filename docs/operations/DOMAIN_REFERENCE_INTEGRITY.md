# Domain Reference Integrity Audit (operator-only)

Tracking: #100 · Architecture: `CANONICAL_DOMAIN_MODEL_V2.md`

This command checks **persisted, typed cross-domain references** against the current
`apps.common.domain_objects` registry. It is a read-only diagnostic. It
does **not** rewrite data, delete or relink objects, change authorization,
or attest that the installation is secure or accepted by a customer.

## Execution

Run from an approved backend/operator environment with authorized database
access. Do not expose this command or its output as a customer-facing API.

```bash
cd backend
python manage.py verify_domain_references --json
python manage.py verify_domain_references --json --tenant-id <AUTHORIZED_TENANT_UUID>
```

Both commands emit a single JSON object on standard output. A nonzero process
exit indicates findings or invalid arguments; operator/CI automation should
treat it as a failed integrity gate. The command never automatically repairs
data. Output includes source row, tenant and referenced target identifiers:
protect the output as organization-sensitive operational metadata and do not
post it to public issues or logs.

## Scope and interpretation

Sources: `EvidenceLink`, `DocumentLink`, `Action.source_type/source_id`,
`WorkflowInstance`, and `AISuggestion.object_type/object_id`. Soft-deleted
**source** rows and intentionally unbound Action/AI rows are skipped. The
source count and finding details are deterministic and sorted.

| Status | Meaning |
| --- | --- |
| `unknown_type` | The referenced object type is not registered |
| `unsupported_capability` | The source needs a capability the type does not offer |
| `incomplete_reference` | Only one of type and target ID was populated |
| `missing` | No object with that ID exists under the expected model |
| `cross_tenant` | Target exists but belongs to a different tenant |
| `deleted` | The target has a soft-deletion marker |
| `invalid_scope` | The target's organizational unit belongs to a different tenant |
| `cross_tenant_source` | A typed link's parent object is owned by another tenant |
| `deleted_source` | The parent evidence/document/definition is soft-deleted |
| `scope_mismatch` | Persisted workflow organization unit differs from the resolved target scope |

Diagnostics deliberately query unscoped targets **only inside this operator
command** to distinguish missing, deleted and foreign-tenant references.
Normal API resolvers remain tenant-cloaked; do not use the diagnostic resolver
to authorize requests or build user-visible error responses.

A `scope_mismatch` can represent post-creation reorganization; investigate
the current approval/audit history before proposing remediation. This audit
does not prove user-level RBAC policy or cover every relational foreign key,
legacy deleted ancestor, or source metadata. It is a targeted integrity check,
not a general security scanner.

## Safe response

1. Preserve the original JSON and record the application source SHA and
   authorized tenant/deployment; store evidence in an approved restricted area.
2. Confirm the expected tenant, target type, source owner and organization
   history with the customer's authorized data steward.
3. File a tracked remediation issue; separately review any proposed data
   changes and define rollback/audit events.
4. Re-run the command and attach redacted status/count evidence.
5. Complete external release and datacenter acceptance independently (#7,
   #8, #40, #42, #74).

No manual SQL or automatic relinking is part of this command.
