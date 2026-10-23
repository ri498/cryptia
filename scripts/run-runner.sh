#!/usr/bin/env bash
set -e

# Detect branch if not provided as argument
BRANCH="${1:-$(git rev-parse --abbrev-ref HEAD)}"

echo "=================================================="
echo " Cryptia Local Runner (act + Podman)"
echo " Triggered for branch: $BRANCH"
echo "=================================================="

# Ensure podman socket is listening
if command -v systemctl >/dev/null 2>&1; then
  if ! systemctl --user is-active --quiet podman.socket 2>/dev/null; then
    echo "Starting podman user socket..."
    systemctl --user start podman.socket
  fi
fi

# Ensure act is in PATH and podman socket is set
export PATH="$HOME/.local/bin:$PATH"
export DOCKER_HOST="unix:///run/user/1000/podman/podman.sock"
export CONTAINER_HOST="unix:///run/user/1000/podman/podman.sock"

if ! command -v act >/dev/null 2>&1; then
  echo "Error: 'act' is not found in PATH." >&2
  exit 1
fi

EVENT_FILE="/tmp/act-event-$$.json"
cleanup() {
  rm -f "$EVENT_FILE"
}
trap cleanup EXIT

echo "{\"ref\": \"refs/heads/$BRANCH\"}" > "$EVENT_FILE"

if [ "$BRANCH" = "development" ]; then
  echo "--> Running local build & test job for 'development' branch..."
  act push \
    --pull=false \
    -j build-local \
    -e "$EVENT_FILE"

elif [ "$BRANCH" = "main" ]; then
  echo "--> Running build & deployment job for 'main' branch..."
  SECRET_ARGS=()
  if [ -f .secrets ]; then
    SECRET_ARGS=(--secret-file .secrets)
  else
    echo "Warning: .secrets file not found. Remote upload will be skipped unless secrets are configured."
  fi

  act push \
    --pull=false \
    -j deploy-gce \
    -e "$EVENT_FILE" \
    "${SECRET_ARGS[@]}"
else
  echo "Branch '$BRANCH' has no automated runner configured."
fi
