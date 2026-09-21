#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
umask 077

VERSION="${1:-}"
SOURCE_REF="${2:-HEAD}"
OUTPUT_ROOT="${OFFLINE_RELEASE_OUTPUT_ROOT:-$ROOT/artifacts/offline-release}"
SBOM_DIR="${OFFLINE_RELEASE_SBOM_DIR:-$ROOT}"
SECURITY_DIR="${OFFLINE_RELEASE_SECURITY_DIR:-$ROOT}"

if [[ -z "$VERSION" || ! "$VERSION" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]]; then
  echo "Usage: $0 <release-version> [source-ref]" >&2
  echo "release-version may contain letters, numbers, dot, underscore and dash." >&2
  exit 2
fi
for command in docker git python sha256sum; do
  command -v "$command" >/dev/null || { echo "ERROR: required command not found: $command" >&2; exit 2; }
done
if [[ -n "$(git status --porcelain --untracked-files=all)" ]]; then
  echo "ERROR: release build requires a completely clean checkout, including no untracked files." >&2
  exit 2
fi
SOURCE_SHA="$(git rev-parse "${SOURCE_REF}^{commit}" 2>/dev/null || true)"
if [[ ! "$SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]]; then
  echo "ERROR: source-ref must resolve to an exact Git commit." >&2
  exit 2
fi
HEAD_SHA="$(git rev-parse HEAD)"
if [[ "$HEAD_SHA" != "$SOURCE_SHA" ]]; then
  echo "ERROR: checked-out HEAD must exactly match source-ref before building release images." >&2
  exit 2
fi
SOURCE_TREE="$(git rev-parse "${SOURCE_SHA}^{tree}")"

STAGE="$OUTPUT_ROOT/$VERSION"
if [[ -e "$STAGE" ]]; then
  echo "ERROR: output already exists: $STAGE" >&2
  exit 2
fi
mkdir -p "$STAGE"/{images,metadata,sbom,source,config,docs}

cleanup() {
  git update-ref -d "refs/grc-release/$VERSION" >/dev/null 2>&1 || true
}
trap cleanup EXIT

for required in sbom-backend.cdx.json sbom-frontend.cdx.json release-evidence-provenance.json; do
  if [[ ! -s "$SBOM_DIR/$required" ]]; then
    echo "ERROR: required SBOM/provenance artifact is missing: $SBOM_DIR/$required" >&2
    exit 3
  fi
done
SECURITY_REPORTS=(
  bandit-results.json
  trivy-secret-results.json
  trivy-backend-results.json
  trivy-frontend-results.json
)
for required in "${SECURITY_REPORTS[@]}" release-evidence-provenance.json; do
  if [[ ! -s "$SECURITY_DIR/$required" ]]; then
    echo "ERROR: required security/provenance artifact is missing: $SECURITY_DIR/$required" >&2
    exit 3
  fi
done

BACKEND_IMAGE="grc-backend:$VERSION"
FRONTEND_IMAGE="grc-frontend:$VERSION"
EXTERNAL_IMAGES=(
  "pgvector/pgvector:0.8.6-pg18-trixie"
  "redis:8.2.1-alpine"
  "chrislusf/seaweedfs:4.47"
  "ollama/ollama:0.34.1"
  "nginx:1.28.0-alpine"
)

echo "[1/8] Building release application images..."
docker build --pull -t "$BACKEND_IMAGE" backend
docker build --pull -t "$FRONTEND_IMAGE" frontend

BACKEND_IMAGE_ID="$(docker image inspect --format '{{.Id}}' "$BACKEND_IMAGE")"
FRONTEND_IMAGE_ID="$(docker image inspect --format '{{.Id}}' "$FRONTEND_IMAGE")"
for provenance in \
  "$SBOM_DIR/release-evidence-provenance.json" \
  "$SECURITY_DIR/release-evidence-provenance.json"
do
  python scripts/release-evidence-provenance.py verify \
    --provenance "$provenance" \
    --source-commit "$SOURCE_SHA" \
    --source-tree "$SOURCE_TREE" \
    --backend-image-id "$BACKEND_IMAGE_ID" \
    --frontend-image-id "$FRONTEND_IMAGE_ID"
done

echo "[2/8] Pulling pinned runtime dependency images..."
for image in "${EXTERNAL_IMAGES[@]}"; do
  docker pull "$image"
done

echo "[3/8] Exporting exact image archives..."
IMAGE_ROWS="$STAGE/metadata/images.rows.jsonl"
: > "$IMAGE_ROWS"
export_image() {
  local role="$1"
  local image="$2"
  local archive="images/${role}.tar"
  docker image inspect "$image" >/dev/null
  docker save -o "$STAGE/$archive" "$image"
  local image_id
  image_id="$(docker image inspect --format '{{.Id}}' "$image")"
  local repo_digests
  repo_digests="$(docker image inspect --format '{{json .RepoDigests}}' "$image")"
  python - "$IMAGE_ROWS" "$role" "$image" "$archive" "$image_id" "$repo_digests" <<'PY'
import json
import sys
from pathlib import Path
path, role, image, archive, image_id, repo_digests = sys.argv[1:]
row = {
    "role": role,
    "reference": image,
    "archive": archive,
    "image_id": image_id,
    "repo_digests": json.loads(repo_digests) if repo_digests not in ("null", "") else [],
}
with Path(path).open("a", encoding="utf-8") as handle:
    handle.write(json.dumps(row, sort_keys=True) + "\n")
PY
}
export_image backend "$BACKEND_IMAGE"
export_image frontend "$FRONTEND_IMAGE"
export_image postgres "${EXTERNAL_IMAGES[0]}"
export_image redis "${EXTERNAL_IMAGES[1]}"
export_image objectstore "${EXTERNAL_IMAGES[2]}"
export_image ollama "${EXTERNAL_IMAGES[3]}"
export_image gateway "${EXTERNAL_IMAGES[4]}"
python - "$IMAGE_ROWS" "$STAGE/metadata/images.json" <<'PY'
import json
import sys
from pathlib import Path
rows = [json.loads(line) for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines() if line]
Path(sys.argv[2]).write_text(json.dumps({"schema": "grc-offline-images-v1", "images": rows}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
rm -f "$IMAGE_ROWS"

python scripts/server-pilot-candidate.py \
  --release-version "$VERSION" \
  --source-commit "$SOURCE_SHA" \
  --images "$STAGE/metadata/images.json" \
  --out "$STAGE/metadata/server-candidate.json"

echo "[4/8] Creating source Git bundle at the exact release commit..."
git update-ref "refs/grc-release/$VERSION" "$SOURCE_SHA"
git bundle create "$STAGE/source/grc-platform.bundle" "refs/grc-release/$VERSION"
git bundle verify "$STAGE/source/grc-platform.bundle" >/dev/null

echo "[5/8] Copying SBOMs and public runtime templates..."
install -m 600 "$SBOM_DIR/sbom-backend.cdx.json" "$STAGE/sbom/sbom-backend.cdx.json"
install -m 600 "$SBOM_DIR/sbom-frontend.cdx.json" "$STAGE/sbom/sbom-frontend.cdx.json"
install -m 600 .env.pilot.example "$STAGE/config/.env.pilot.example"
install -m 600 docker-compose.pilot.yml "$STAGE/config/docker-compose.pilot.yml"
install -m 600 docker-compose.pilot.tls.yml "$STAGE/config/docker-compose.pilot.tls.yml"
install -m 700 scripts/server-pilot-env.py "$STAGE/config/server-pilot-env.py"
if [[ -f docs/OFFLINE_RELEASE_AND_SUPPORT.md ]]; then
  install -m 600 docs/OFFLINE_RELEASE_AND_SUPPORT.md "$STAGE/docs/OFFLINE_RELEASE_AND_SUPPORT.md"
fi
if [[ -f docs/DATACENTER_OPERATIONS.md ]]; then
  install -m 600 docs/DATACENTER_OPERATIONS.md "$STAGE/docs/DATACENTER_OPERATIONS.md"
fi
if [[ -f docs/FINAL_RELEASE_ACCEPTANCE.md ]]; then
  install -m 600 docs/FINAL_RELEASE_ACCEPTANCE.md "$STAGE/docs/FINAL_RELEASE_ACCEPTANCE.md"
fi
if [[ -f docs/FINAL_RELEASE_ATTESTATIONS.example.json ]]; then
  install -m 600 docs/FINAL_RELEASE_ATTESTATIONS.example.json "$STAGE/docs/FINAL_RELEASE_ATTESTATIONS.example.json"
fi
if [[ -f docs/SERVER_PILOT_CANDIDATE.md ]]; then
  install -m 600 docs/SERVER_PILOT_CANDIDATE.md "$STAGE/docs/SERVER_PILOT_CANDIDATE.md"
fi

python scripts/offline-release-manifest.py prepare-metadata --repo "$ROOT" --stage "$STAGE"

echo "[6/8] Recording security evidence by digest without embedding raw secret-scan output..."
python - "$SECURITY_DIR" "$STAGE/metadata/security-evidence.json" "${SECURITY_REPORTS[@]}" <<'PY'
import hashlib
import json
import sys
from pathlib import Path
root = Path(sys.argv[1])
out = Path(sys.argv[2])
rows = []
for name in sys.argv[3:]:
    path = root / name
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    rows.append({"artifact": name, "sha256": digest, "included_in_bundle": False})
payload = {
    "schema": "grc-release-security-evidence-v1",
    "reports": rows,
    "raw_reports_policy": "not embedded because secret-scan artifacts may contain sensitive findings; retain in the approved CI/security evidence store",
}
out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

echo "[7/8] Building deterministic manifest and verifying payload..."
python scripts/offline-release-manifest.py build --stage "$STAGE" --version "$VERSION" --source-commit "$SOURCE_SHA"
python scripts/offline-release-manifest.py verify --stage "$STAGE"

echo "[8/8] Offline release candidate prepared: $STAGE"
echo "IMPORTANT: this candidate is not approved for distribution until release-manifest.json is signed with the controlled offline signing key."
echo "Raw security scan reports were intentionally not copied into the bundle."
