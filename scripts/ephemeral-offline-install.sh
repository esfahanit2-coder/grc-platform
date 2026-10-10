#!/usr/bin/env bash
# Disposable signed-package install smoke test. Synthetic OCI image payloads only.
# It never starts application services and is NOT an air-gapped customer acceptance test.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
umask 077

if [[ "${GITHUB_ACTIONS:-}" != "true" || "${GRC_OFFLINE_EPHEMERAL_ONLY:-NO}" != "YES" ]]; then
  echo "ERROR: this test needs explicit opt-in on a disposable GitHub Actions runner." >&2
  exit 2
fi
for required in docker git python openssl tar sha256sum; do
  command -v "$required" >/dev/null || { echo "ERROR: missing $required" >&2; exit 2; }
done
docker info >/dev/null
VERSION="v-ci-offline-${GITHUB_RUN_ID:-local}-${GITHUB_RUN_ATTEMPT:-1}"
SOURCE_SHA="$(git rev-parse HEAD)"
SOURCE_TREE="$(git rev-parse HEAD^{tree})"
TMP="$(mktemp -d)"
STAGE="$TMP/$VERSION"
SIGNED="$TMP/$VERSION-signed.tar.gz"
REF="refs/grc-release/$VERSION"
TAGS=()
cleanup() {
  local code=$?
  trap - EXIT
  git update-ref -d "$REF" >/dev/null 2>&1 || true
  for tag in "${TAGS[@]}"; do docker image rm "$tag" >/dev/null 2>&1 || true; done
  rm -rf -- "$TMP"
  echo "Disposable offline-install cleanup; status=$code"
  exit "$code"
}
trap cleanup EXIT

mkdir -p "$STAGE"/{images,metadata,source} "$TMP/rootfs/etc"
printf 'synthetic package installation check\n' > "$TMP/rootfs/etc/grc-synthetic.txt"
tar -cf "$TMP/minimal-rootfs.tar" -C "$TMP/rootfs" .
echo '[1/7] Creating tiny local images without pulling registries.'
BASE_TAG="grc-offline-install-ci:run-${GITHUB_RUN_ID:-local}-${GITHUB_RUN_ATTEMPT:-1}"
docker import "$TMP/minimal-rootfs.tar" "$BASE_TAG" >/dev/null
TAGS+=("$BASE_TAG")
BASE_ID="$(docker image inspect --format '{{.Id}}' "$BASE_TAG")"
ROWS="$STAGE/metadata/images.rows.jsonl"
: > "$ROWS"
for role in backend frontend postgres redis objectstore ollama gateway; do
  tag="grc-offline-ci-$role:$VERSION"
  docker tag "$BASE_TAG" "$tag"
  TAGS+=("$tag")
  docker save -o "$STAGE/images/$role.tar" "$tag"
  python - "$ROWS" "$role" "$tag" "$BASE_ID" <<'PY'
import json, sys
from pathlib import Path
p, role, ref, image_id = sys.argv[1:]
with Path(p).open('a', encoding='utf-8') as file:
    file.write(json.dumps({'role':role,'reference':ref,'archive':f'images/{role}.tar',
                           'image_id':image_id,'repo_digests':[]}, sort_keys=True)+'\n')
PY
done
python - "$ROWS" "$STAGE/metadata/images.json" <<'PY'
import json, sys
from pathlib import Path
rows = [json.loads(r) for r in Path(sys.argv[1]).read_text().splitlines()]
Path(sys.argv[2]).write_text(json.dumps({'schema':'grc-offline-images-v1','images':rows},
                                     indent=2,sort_keys=True)+'\n',encoding='utf-8')
PY
rm -f "$ROWS"

echo '[2/7] Preparing real signed metadata and exact-source Git bundle.'
python scripts/offline-release-manifest.py prepare-metadata --repo "$ROOT" --stage "$STAGE"
python - "$STAGE/metadata/security-evidence.json" <<'PY'
import json,sys
from pathlib import Path
Path(sys.argv[1]).write_text(json.dumps({'schema':'grc-release-security-evidence-v1',
                                          'reports':[]},sort_keys=True)+'\n',encoding='utf-8')
PY
python scripts/release-evidence-provenance.py write \
  --source-commit "$SOURCE_SHA" --source-tree "$SOURCE_TREE" \
  --backend-image-id "$BASE_ID" --frontend-image-id "$BASE_ID" \
  --out "$STAGE/metadata/release-evidence-provenance.json"
python scripts/server-pilot-candidate.py \
  --release-version "$VERSION" --source-commit "$SOURCE_SHA" \
  --images "$STAGE/metadata/images.json" --out "$STAGE/metadata/server-candidate.json" >/dev/null
if git show-ref --verify --quiet "$REF"; then
  echo "ERROR: temporary release ref unexpectedly exists." >&2
  exit 3
fi
git update-ref "$REF" "$SOURCE_SHA"
git bundle create "$STAGE/source/grc-platform.bundle" "$REF"
git bundle verify "$STAGE/source/grc-platform.bundle" >/dev/null
python scripts/offline-release-manifest.py build --stage "$STAGE" \
  --version "$VERSION" --source-commit "$SOURCE_SHA"
python scripts/offline-release-manifest.py verify --stage "$STAGE" >/dev/null
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 \
  -out "$TMP/signing-private.pem" >/dev/null 2>&1
openssl pkey -in "$TMP/signing-private.pem" -pubout -out "$TMP/trusted-public.pem" >/dev/null 2>&1
bash scripts/offline-release-sign.sh "$STAGE" "$TMP/signing-private.pem" "$SIGNED" >/dev/null
bash scripts/offline-release-verify.sh "$SIGNED" "$TMP/trusted-public.pem" >/dev/null

# Force the installer to materialize every image from signed local archives.
# Leaving these tags preloaded would make the test a false positive for docker load.
for tag in "${TAGS[@]}"; do docker image rm "$tag" >/dev/null; done
for tag in "${TAGS[@]}"; do
  if docker image inspect "$tag" >/dev/null 2>&1; then
    echo "ERROR: a synthetic image remained preloaded before install." >&2
    exit 4
  fi
done

echo '[3/7] Wrong trust anchor must reject before touching install root.'
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 \
  -out "$TMP/untrusted-private.pem" >/dev/null 2>&1
openssl pkey -in "$TMP/untrusted-private.pem" -pubout -out "$TMP/untrusted-public.pem" >/dev/null 2>&1
if OFFLINE_INSTALL_START=NO bash scripts/offline-release-apply.sh install \
   "$SIGNED" "$TMP/untrusted-public.pem" "$TMP/blocked-by-trust" >/dev/null 2>&1; then
  echo 'ERROR: untrusted signing key was accepted.' >&2
  exit 4
fi
[[ ! -e "$TMP/blocked-by-trust" ]] || { echo 'ERROR: untrusted bundle mutated install root.' >&2; exit 4; }

echo '[4/7] Tampered payload must reject before touching install root.'
cp -a "$STAGE" "$TMP/corrupted-stage"
printf '\ntampered after signing\n' >> "$TMP/corrupted-stage/source/grc-platform.bundle"
tar -czf "$TMP/corrupted.tar.gz" -C "$TMP" corrupted-stage
if OFFLINE_INSTALL_START=NO bash scripts/offline-release-apply.sh install \
   "$TMP/corrupted.tar.gz" "$TMP/trusted-public.pem" "$TMP/blocked-by-tamper" >/dev/null 2>&1; then
  echo 'ERROR: modified source payload was accepted.' >&2
  exit 4
fi
[[ ! -e "$TMP/blocked-by-tamper" ]] || { echo 'ERROR: tampered bundle mutated install root.' >&2; exit 4; }

echo '[5/7] Applying approved signed archive from local bytes, without service startup.'
OFFLINE_INSTALL_START=NO bash scripts/offline-release-apply.sh install \
  "$SIGNED" "$TMP/trusted-public.pem" "$TMP/installed" >/dev/null
[[ "$(git -C "$TMP/installed/repository" rev-parse HEAD)" == "$SOURCE_SHA" ]]
[[ ! -e "$TMP/installed/repository/.env" ]] || { echo 'ERROR: runtime env unexpectedly created.' >&2; exit 4; }
openssl dgst -sha256 -verify "$TMP/trusted-public.pem" \
  -signature "$TMP/installed/release/release-manifest.sig" \
  "$TMP/installed/release/release-manifest.json" >/dev/null

echo '[6/7] Confirming local image identities and installed release metadata.'
python - "$TMP/installed/release/images.json" "$BASE_ID" <<'PY'
import json,sys
from pathlib import Path
images = json.loads(Path(sys.argv[1]).read_text())['images']
assert len(images) == 7, 'expected all seven roles'
assert {x['role'] for x in images} == {'backend','frontend','postgres','redis',
                                       'objectstore','ollama','gateway'}
assert all(row['image_id'] == sys.argv[2] for row in images), 'unexpected image identity'
PY
for tag in "${TAGS[@]}"; do
  [[ "$(docker image inspect --format '{{.Id}}' "$tag")" == "$BASE_ID" ]]
done

echo '[7/7] Synthetic signed-install round trip PASS; no app services or customer data used.'
if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  {
    echo '### Disposable signed offline installer: PASS (synthetic images)'
    echo '- Signed archive, independent trust-key verification, exact source Git bundle and image loads were exercised.'
    echo '- Wrong public key and tampered signed payload rejected before install-root mutation.'
    echo '- No application services/TLS/UAT, production image artifacts, air-gapped network or measured RPO/RTO were tested.'
  } >> "$GITHUB_STEP_SUMMARY"
fi
