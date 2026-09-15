# Repository Status

## Canonical repository

`esfahanhonar-cyber/grc-platform` is the canonical private repository.

## Current bootstrap state

The repository already contains the canonical product documentation, governance rules, branching/release policy, security policy, pilot plan and import runbook. The complete Pilot Candidate source tree is staged for one-time import into the `import/pilot-candidate` branch.

## Why source import is separated

The connected GitHub automation can create/update individual files, branches, issues and pull requests, but it cannot directly upload an entire local directory/archive in one safe operation. To avoid hundreds of fragmented commits, the source tree is intentionally imported as one reviewed branch/commit using the runbook.

## Source-of-truth rule

After the Pilot Candidate source tree is merged into `main`, ZIP exports and chat artifacts are no longer authoritative. All future development must flow through repository issues, branches, pull requests, CI and releases.
