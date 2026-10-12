#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TMP="$(mktemp -d)"
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT
STAGE="$TMP/v-ci"
mkdir -p "$STAGE/metadata" "$STAGE/payload"

python scripts/offline-release-manifest.py prepare-metadata --repo "$ROOT" --stage "$STAGE"
python - "$STAGE" <<'PY'
import json
import sys
from pathlib import Path
stage = Path(sys.argv[1])
roles = ["backend", "frontend", "postgres", "redis", "objectstore", "ollama", "gateway"]
images = []
for index, role in enumerate(roles, start=1):
    images.append(
        {
            "role": role,
            "reference": f"example/{role}:v-ci",
            "archive": f"images/{role}.tar",
            "image_id": "sha256:" + f"{index:064x}",
            "repo_digests": [],
        }
    )
(stage / "metadata/images.json").write_text(
    json.dumps({"schema": "grc-offline-images-v1", "images": images}, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
(stage / "metadata/security-evidence.json").write_text(
    json.dumps({"schema": "grc-release-security-evidence-v1", "reports": []}, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
(stage / "payload/probe.txt").write_text("offline-release-ci\n", encoding="utf-8")
PY

SOURCE_SHA="$(git rev-parse HEAD)"
SOURCE_TREE="$(git rev-parse HEAD^{tree})"
python scripts/release-evidence-provenance.py write \
  --source-commit "$SOURCE_SHA" \
  --source-tree "$SOURCE_TREE" \
  --backend-image-id "sha256:$(printf '%064x' 1)" \
  --frontend-image-id "sha256:$(printf '%064x' 2)" \
  --out "$STAGE/metadata/release-evidence-provenance.json"
python scripts/server-pilot-candidate.py \
  --release-version v-ci \
  --source-commit "$SOURCE_SHA" \
  --images "$STAGE/metadata/images.json" \
  --out "$STAGE/metadata/server-candidate.json" >/dev/null
python scripts/offline-release-manifest.py build --stage "$STAGE" --version v-ci --source-commit "$SOURCE_SHA"
python scripts/offline-release-manifest.py verify --stage "$STAGE" >/dev/null

openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out "$TMP/private.pem" >/dev/null 2>&1
openssl pkey -in "$TMP/private.pem" -pubout -out "$TMP/public.pem" >/dev/null 2>&1
bash scripts/offline-release-sign.sh "$STAGE" "$TMP/private.pem" "$TMP/v-ci-offline-signed.tar.gz" >/dev/null
bash scripts/offline-release-verify.sh "$TMP/v-ci-offline-signed.tar.gz" "$TMP/public.pem" >/dev/null
# Both extracted directory and archive entrypoints must return success under set -e.
bash scripts/offline-release-verify.sh "$STAGE" "$TMP/public.pem" >/dev/null

printf 'tampered\n' > "$STAGE/payload/probe.txt"
if bash scripts/offline-release-verify.sh "$STAGE" "$TMP/public.pem" >/dev/null 2>&1; then
  echo "ERROR: tampered bundle unexpectedly verified." >&2
  exit 1
fi

# The opt-in prebuilt release path must refuse missing scanned image identities;
# NEVER silently fall back to docker build or accept stale evidence.
mkdir -p "$TMP/mock-bin" "$TMP/mock-evidence"
for name in \
  sbom-backend.cdx.json sbom-frontend.cdx.json \
  release-evidence-provenance.json \
  bandit-results.json trivy-secret-results.json \
  trivy-backend-results.json trivy-frontend-results.json; do
  printf '{}\n' > "$TMP/mock-evidence/$name"
done
cat > "$TMP/mock-bin/docker" <<'SH'
#!/usr/bin/env bash
case "${1:-} ${2:-}" in
  "image inspect") exit 1 ;;
  *) echo "ERROR: forbidden Docker fallback in prebuilt negative test" >&2; exit 91 ;;
esac
SH
chmod 700 "$TMP/mock-bin/docker"
if PATH="$TMP/mock-bin:$PATH" OFFLINE_RELEASE_USE_PREBUILT=YES \
  OFFLINE_RELEASE_OUTPUT_ROOT="$TMP/negative-prebuilt" \
  OFFLINE_RELEASE_SBOM_DIR="$TMP/mock-evidence" \
  OFFLINE_RELEASE_SECURITY_DIR="$TMP/mock-evidence" \
  bash scripts/offline-release-build.sh v-ci-missing-scanned "$SOURCE_SHA" \
    > "$TMP/missing-scanned.log" 2>&1; then
  echo "ERROR: missing prebuilt images unexpectedly permitted an offline candidate." >&2
  exit 1
fi
grep -q "missing prebuilt scanned image" "$TMP/missing-scanned.log" || {
  echo "ERROR: prebuilt test failed for the wrong reason." >&2
  exit 1
}

echo "offline release signature/checksum/tamper and fail-closed prebuilt self-tests passed"
