#!/usr/bin/env bash

###############################################################################
# Build & (optionally) push the mcp_server Docker image.
#
# Usage:
#   ./build_and_push.sh                 # build only (local tag)
#   IMAGE_NAME=my-mcp ./build_and_push.sh
#   REGISTRY=myrepo ./build_and_push.sh  # e.g. REGISTRY=docker.io/username
#   VERSION=1.0.0 REGISTRY=ghcr.io/user ./build_and_push.sh
#   PUSH=1 REGISTRY=ghcr.io/user ./build_and_push.sh
#
# Environment variables:
#   REGISTRY   (optional) e.g. docker.io/youruser or ghcr.io/yourorg
#   IMAGE_NAME (default: mcp_server)
#   VERSION    (default: git describe or timestamp)
#   PUSH       (default: 0) set to 1 to push
#   DOCKERFILE (default: mcp_server/Dockerfile relative to src dir)
#   CONTEXT    (default: intent-mcp/src directory of this script's parent)
#   BUILD_ARGS (optional) extra args passed to docker build
#
# Exits non‑zero on failure. Requires Docker CLI.
###############################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$(dirname "$SCRIPT_DIR")"   # /.../intent-mcp/src

: "${IMAGE_NAME:=mcp_server}"
# Default registry user (can override by exporting REGISTRY)
: "${REGISTRY:=docker.io/gabiminz}"
# Default to push every build (set PUSH=0 to skip)
: "${PUSH:=1}"
# When set to 1 and VERSION is not provided, append a timestamp for uniqueness
: "${UNIQUE_TAG:=1}"

if git -C "$SRC_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  GIT_VER=$(git -C "$SRC_DIR" describe --tags --dirty --always 2>/dev/null || true)
else
  GIT_VER=""
fi

# If VERSION not provided, derive it from git or fallback; optionally make it unique
ORIG_VERSION="${VERSION:-}"
if [[ -z "${VERSION:-}" ]]; then
  BASE_VER="${GIT_VER:-latest}"
  if [[ "$UNIQUE_TAG" == "1" ]]; then
    VERSION="${BASE_VER}-$(date +%Y%m%d%H%M%S)"
  else
    VERSION="$BASE_VER"
  fi
fi

# If user had set VERSION but it equals GIT_VER and UNIQUE_TAG=1, still append timestamp
if [[ -n "$ORIG_VERSION" && "$UNIQUE_TAG" == "1" && "$ORIG_VERSION" == "${GIT_VER}" ]]; then
  VERSION="${ORIG_VERSION}-$(date +%Y%m%d%H%M%S)"
fi
: "${DOCKERFILE:=mcp_server/Dockerfile}"
: "${CONTEXT:=$SRC_DIR}"  # build context root

TAG_LOCAL="$IMAGE_NAME:$VERSION"
# Trim trailing slash just in case
REGISTRY_CLEAN="${REGISTRY%/}"
TAG_REMOTE="$REGISTRY_CLEAN/$TAG_LOCAL"

echo "==> Build parameters"
echo "    Context:     $CONTEXT"
echo "    Dockerfile:  $DOCKERFILE"
echo "    Image name:  $IMAGE_NAME"
echo "    Version:     $VERSION"
if [[ -n "$TAG_REMOTE" ]]; then
  echo "    Registry:    $REGISTRY_CLEAN"
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
  if [[ -z "$TAG_REMOTE" ]]; then
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
