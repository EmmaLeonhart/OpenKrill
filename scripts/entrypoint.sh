#!/usr/bin/env bash
# krill entrypoint — configures and starts an OpenClaw agent pod
set -euo pipefail

WORKSPACE="/root/.openclaw/workspace"
CONFIG_DIR="/root/.openclaw"
CONTEXT_DIR="/krill/context"
OPENCLAW_CONFIG="${CONFIG_DIR}/openclaw.json"

# Defaults for optional env vars
OPENCLAW_MODEL="${OPENCLAW_MODEL:-anthropic/claude-opus-4-6}"
OPENCLAW_API_BASE="${OPENCLAW_API_BASE:-https://api.anthropic.com}"

echo "[krill] Starting krill pod: ${KRILL_NAME:-unnamed}"
echo "[krill] Model:    ${OPENCLAW_MODEL}"
echo "[krill] API base: ${OPENCLAW_API_BASE}"

# 1. Write openclaw.json from template using envsubst
mkdir -p "${CONFIG_DIR}"
envsubst < /etc/krill/openclaw.json.tpl > "${OPENCLAW_CONFIG}"
echo "[krill] Wrote ${OPENCLAW_CONFIG}"

# 2. If a .claw archive is present in the context volume, import it
INIT_CLAW="${CONTEXT_DIR}/init.claw"
if [ -f "${INIT_CLAW}" ]; then
    echo "[krill] Found init.claw — importing context..."
    python3 /usr/local/bin/claw.py import "${INIT_CLAW}" "${WORKSPACE}"
    echo "[krill] Context imported."
else
    echo "[krill] No init.claw found — starting with fresh workspace."
fi

# 3. If a project AGENTS.md exists in the context volume, inject it
PROJECT_AGENTS="${CONTEXT_DIR}/AGENTS.md"
if [ -f "${PROJECT_AGENTS}" ]; then
    echo "[krill] Injecting AGENTS.md into workspace..."
    cp "${PROJECT_AGENTS}" "${WORKSPACE}/AGENTS.md"
fi

# 4. Start the OpenClaw gateway
echo "[krill] Starting OpenClaw gateway on port 18789..."
exec openclaw gateway --port 18789
