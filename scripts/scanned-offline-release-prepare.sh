#!/usr/bin/env bash
# Connected, operator-controlled release workstation ONLY (Issue #161).
# Build and security-scan each exact app image once; package UNSIGNED candidate.
# This is NOT a GitHub Actions production signing workflow or a customer release.
set -euo pipefail
umask 077

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
VERSION="${1:-}"
SOURCE_SHA="${2:-}"
EVIDENCE_ROOT="${3:-}"

if [[ -z "$VERSION" || -z "$SOURCE_SHA" || -z "$EVIDENCE_ROOT" ]]; then
  echo 'Usage: scanned-offline-release-prepare.sh <version> <exact-sha> <evidence-root-outside-repo>' >&2
  exit 2
fi
if [[ ! "$VERSION" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ || ! "$SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]]; then
  echo 'ERROR: version or 40-character source SHA is invalid.' >&2
  exit 2
fi
for executable in git docker python bandit trivy sha256sum realpath cmp; do
  command -v "$executable" >/dev/null || {
    echo "ERROR: missing trusted release-builder tool: $executable" >&2
    exit 2
  }
done
test "$(git rev-parse HEAD)" = "$SOURCE_SHA" || {
  echo 'ERROR: checkout does not match exact source SHA.' >&2
  exit 2
}
test -z "$(git status --porcelain --untracked-files=all)" || {
  echo 'ERROR: release builder requires a completely clean source checkout.' >&2
  exit 2
}
if [[ -e .env ]]; then
  echo 'ERROR: refusing release scan from a checkout containing a production .env.' >&2
  exit 2
fi
EVIDENCE_ROOT="$(realpath -m "$EVIDENCE_ROOT")"
case "$EVIDENCE_ROOT" in
  "$ROOT"|"$ROOT"/*)
    echo 'ERROR: security reports, archives and SBOMs must be outside the Git checkout.' >&2
    exit 2
    ;;
esac
test ! -e "$EVIDENCE_ROOT" || {
  echo 'ERROR: evidence root must be fresh and absent; no overwriting scan results.' >&2
  exit 2
}
mkdir -m 700 -p "$EVIDENCE_ROOT/security" "$EVIDENCE_ROOT/sbom"
echo '[1/7] Building exact application images on the trusted release workstation.'
df -h "$EVIDENCE_ROOT" || true
docker build --pull -t grc-backend:ci backend
docker build --pull -t grc-frontend:ci frontend
BACKEND_ID="$(docker image inspect --format '{{.Id}}' grc-backend:ci)"
FRONTEND_ID="$(docker image inspect --format '{{.Id}}' grc-frontend:ci)"
SOURCE_TREE="$(git rev-parse "${SOURCE_SHA}^{tree}")"

echo '[2/7] Running Bandit high severity and repository secret scan (fail closed).'
bandit -r backend -lll -ii -f json -o "$EVIDENCE_ROOT/security/bandit-results.json"
trivy fs --scanners secret --format json --exit-code 1 \
  --skip-dirs .git --skip-dirs .next --skip-dirs node_modules \
  --output "$EVIDENCE_ROOT/security/trivy-secret-results.json" .

echo '[3/7] Scanning actual backend/frontend Docker image IDs for high/critical CVEs.'
for role in backend frontend; do
  trivy image --image-src docker --ignore-unfixed \
    --vuln-type os,library --severity CRITICAL,HIGH \
    --format json --exit-code 1 \
    --output "$EVIDENCE_ROOT/security/trivy-${role}-results.json" "grc-${role}:ci"
done

echo '[4/7] Generating CycloneDX SBOM from the exact scanned app images.'
for role in backend frontend; do
  trivy image --image-src docker --format cyclonedx \
    --output "$EVIDENCE_ROOT/sbom/sbom-${role}.cdx.json" "grc-${role}:ci"
done

echo '[5/7] Linking source SHA/tree and exact Docker IDs in BOTH evidence stores.'
for folder in security sbom; do
  python scripts/release-evidence-provenance.py write \
    --source-commit "$SOURCE_SHA" --source-tree "$SOURCE_TREE" \
    --backend-image-id "$BACKEND_ID" --frontend-image-id "$FRONTEND_ID" \
    --out "$EVIDENCE_ROOT/$folder/release-evidence-provenance.json"
done
cmp "$EVIDENCE_ROOT/security/release-evidence-provenance.json" \
  "$EVIDENCE_ROOT/sbom/release-evidence-provenance.json"

echo '[6/7] Tagging the scanned images without building again.'
docker tag grc-backend:ci "grc-backend:$VERSION"
docker tag grc-frontend:ci "grc-frontend:$VERSION"
test "$(docker image inspect --format '{{.Id}}' "grc-backend:$VERSION")" = "$BACKEND_ID"
test "$(docker image inspect --format '{{.Id}}' "grc-frontend:$VERSION")" = "$FRONTEND_ID"

echo '[7/7] Preparing an unsigned full-runtime bundle from exact scanned images.'
OFFLINE_RELEASE_USE_PREBUILT=YES \
  OFFLINE_RELEASE_SBOM_DIR="$EVIDENCE_ROOT/sbom" \
  OFFLINE_RELEASE_SECURITY_DIR="$EVIDENCE_ROOT/security" \
  OFFLINE_RELEASE_OUTPUT_ROOT="$EVIDENCE_ROOT/stages" \
  bash scripts/offline-release-build.sh "$VERSION" "$SOURCE_SHA"

echo 'UNSIGNED scanned-image candidate prepared; no customer security/rights/UAT approval implied.'
echo "Candidate stage: $EVIDENCE_ROOT/stages/$VERSION"
echo 'Offline signing and independent verification require an approved operator/key.'
