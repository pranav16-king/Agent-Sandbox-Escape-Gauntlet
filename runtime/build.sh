#!/usr/bin/env bash
# ==============================================================================
# PS01 Agent Sandbox Escape Gauntlet - Hardened Sandbox Image Builder
# Targets: ps01-sandbox:latest
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
IMAGE_NAME="ps01-sandbox:latest"

echo "================================================================================"
echo "[PS01] Building Hardened Agent Sandbox Container Image"
echo "================================================================================"
echo "  Target Tag:  ${IMAGE_NAME}"
echo "  Dockerfile:  ${SCRIPT_DIR}/Dockerfile"
echo "  Context:     ${ROOT_DIR}"
echo "--------------------------------------------------------------------------------"

if ! command -v docker &> /dev/null; then
    echo "[PS01] ERROR: 'docker' command could not be found." >&2
    echo "       Please ensure Docker is installed, running, and accessible in your PATH." >&2
    exit 1
fi

docker build \
    -t "${IMAGE_NAME}" \
    -f "${SCRIPT_DIR}/Dockerfile" \
    "${ROOT_DIR}" \
    "$@"

echo "--------------------------------------------------------------------------------"
echo "[PS01] Successfully built image: ${IMAGE_NAME}"
echo "================================================================================"
