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
SRC_DIR="$(dirname "$SCRIPT_DIR")"

: "${IMAGE_NAME:=rapp}"
: "${REGISTRY:=docker.io/gabiminz}"
: "${PUSH:=1}"
: "${UNIQUE_TAG:=1}"

if git -C "$SRC_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  GIT_VER=$(git -C "$SRC_DIR" describe --tags --dirty --always 2>/dev/null || true)
else
  GIT_VER=""
fi

ORIG_VERSION="${VERSION:-}"
if [[ -z "${VERSION:-}" ]]; then
  BASE_VER="${GIT_VER:-latest}"
  if [[ "$UNIQUE_TAG" == "1" ]]; then
    VERSION="${BASE_VER}-$(date +%Y%m%d%H%M%S)"
  else
    VERSION="$BASE_VER"
  fi
fi

if [[ -n "$ORIG_VERSION" && "$UNIQUE_TAG" == "1" && "$ORIG_VERSION" == "$GIT_VER" ]]; then
  VERSION="${ORIG_VERSION}-$(date +%Y%m%d%H%M%S)"
fi

: "${DOCKERFILE:=rApp/Dockerfile}"
: "${CONTEXT:=$SRC_DIR}"

TAG_LOCAL="$IMAGE_NAME:$VERSION"
REGISTRY_CLEAN="${REGISTRY%/}"
TAG_REMOTE="$REGISTRY_CLEAN/$TAG_LOCAL"

printf '==> Build parameters\n'
printf '    Context:     %s\n' "$CONTEXT"
printf '    Dockerfile:  %s\n' "$DOCKERFILE"
printf '    Image name:  %s\n' "$IMAGE_NAME"
printf '    Version:     %s\n' "$VERSION"
if [[ -n "$REGISTRY_CLEAN" ]]; then
  printf '    Registry:    %s\n' "$REGISTRY_CLEAN"
fi
printf '\n'

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
  if [[ -z "$REGISTRY_CLEAN" ]]; then
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

echo
printf 'Done. Available local tags:\n'
docker images | awk -v name="$IMAGE_NAME" 'NR==1 || $1 == name' | head -n 10
