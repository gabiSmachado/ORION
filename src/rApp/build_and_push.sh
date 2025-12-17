#!/usr/bin/env bash

###############################################################################
# Build & (optionally) push the rApp Docker image.
#
# Usage:
#   ./build_and_push.sh                 # build only (local tag)
#   IMAGE_NAME=my-rapp ./build_and_push.sh
#   REGISTRY=myrepo ./build_and_push.sh  # e.g. REGISTRY=docker.io/username
#   VERSION=1.0.0 REGISTRY=ghcr.io/user ./build_and_push.sh
#   PUSH=1 REGISTRY=ghcr.io/user ./build_and_push.sh
#
# Environment variables:
#   REGISTRY   (optional) e.g. docker.io/youruser or ghcr.io/yourorg
#   IMAGE_NAME (default: rapp)
#   VERSION    (default: git describe or timestamp)
#   PUSH       (default: 1) set to 0 to skip
#   DOCKERFILE (default: rApp/Dockerfile relative to src dir)
#   CONTEXT    (default: repo/src directory of this script's parent)
#   BUILD_ARGS (optional) extra args passed to docker build
#   UNIQUE_TAG (default: 1) append timestamp when deriving VERSION
#
# Exits non-zero on failure. Requires Docker CLI.
###############################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$(dirname "$SCRIPT_DIR")"   # /.../intent-mcp/src

: "${IMAGE_NAME:=rapp}"
# Provide a default registry like server script (override as needed)
: "${REGISTRY:=docker.io/gabiminz}"
: "${PUSH:=1}"   # Opt-in push

if git -C "$SRC_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  GIT_VER=$(git -C "$SRC_DIR" describe --tags --dirty --always 2>/dev/null || true)
else
  GIT_VER=""
fi
: "${VERSION:=${GIT_VER:-$(date +%Y%m%d%H%M%S)}}"
: "${DOCKERFILE:=rApp/Dockerfile}"
: "${CONTEXT:=$SRC_DIR}"  # build context root

TAG_LOCAL="$IMAGE_NAME:$VERSION"
REGISTRY_CLEAN="${REGISTRY%/}"
TAG_REMOTE="$REGISTRY_CLEAN/$TAG_LOCAL"

echo "==> Build parameters"
echo "    Context:     $CONTEXT"
echo "    Dockerfile:  $DOCKERFILE"
echo "    Image name:  $IMAGE_NAME"
echo "    Version:     $VERSION"
if [[ -n "$REGISTRY" ]]; then
  echo "    Registry:    $REGISTRY_CLEAN"
fi
if [[ -n "${BUILD_ARGS:-}" ]]; then
  echo "    Build args:  $BUILD_ARGS"
fi
echo

echo "==> Building image ($TAG_LOCAL)"
docker build \
  -f "$CONTEXT/$DOCKERFILE" \
  -t "$TAG_LOCAL" \
  ${TAG_REMOTE:+-t "$TAG_REMOTE"} \
  ${BUILD_ARGS:-} \
  "$CONTEXT"

echo "==> Build complete: $TAG_LOCAL"
if [[ -n "$TAG_REMOTE" ]]; then
  echo "    Also tagged:  $TAG_REMOTE"
fi

if [[ "$PUSH" == "1" ]]; then
  if [[ -z "$REGISTRY" ]]; then
    echo "[WARN] PUSH=1 but REGISTRY not set; skipping push." >&2
  else
    echo "==> Pushing $TAG_REMOTE"
    if ! docker image inspect "$TAG_REMOTE" >/dev/null 2>&1; then
      echo "[INFO] Remote tag missing locally; re-tagging." 
      docker tag "$TAG_LOCAL" "$TAG_REMOTE"
    fi
    docker push "$TAG_REMOTE"
    echo "==> Push complete"
  fi
else
  echo "==> Skipping push (set PUSH=1 to enable)"
fi

echo -e "\nDone. Available local tags:" 
docker images | awk 'NR==1 || /'$IMAGE_NAME'/' | head -n 10