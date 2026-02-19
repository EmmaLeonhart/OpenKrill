# krill — Claude Code Instructions

## What this project is

**krill** is a Kubernetes deployment for running multiple [OpenClaw](https://github.com/openclaw/openclaw) agent instances in parallel. Each pod (a "krill") is a Ubuntu 24.04 container running OpenClaw (Node.js 22), backed by a persistent volume, and connected to a central API server for model routing.

## Three-part system — keep this clear

- **OpenClaw** — the AI agent runtime running inside each pod
- **krill** (this repo) — the Kubernetes infrastructure that runs many OpenClaw pods
- **claw.py** ([submodule](https://github.com/Emma-Leonhart/claw.py)) — a separate tool for the `.claw` context archive format; krill uses `.claw` files to save and restore agent context across pod restarts

Do not conflate these. `claw.py` is not a krill-specific tool — it is its own project that krill depends on.

## Workflow guidelines

- **Commit early and often.** Every meaningful change gets a descriptive commit.
- **Keep this file up to date.** Update with every architectural decision.
- **No planning-only modes.** All thoughts go into files and commits.
- **Update README.md** whenever the architecture or usage changes.

## Architecture decisions (recorded here as they are made)

### 2026-02-18 — Initial architecture
- **StatefulSet** chosen over Deployment because each krill needs stable pod identity and per-pod PVCs for workspace persistence.
- **Headless Service** (clusterIP: None) gives each pod a stable DNS name (`krill-N.krill.krill.svc.cluster.local`).
- **OpenClaw config** is templated via `envsubst` at container startup from `config/openclaw.json.tpl`. This keeps secrets out of images.
- **API key** is injected via Kubernetes Secret → env var `OPENCLAW_API_KEY`. OpenClaw is expected to read this from the environment.
- **API server** is assumed to be an in-cluster LiteLLM proxy or OpenAI-compatible endpoint. Configured via `OPENCLAW_API_BASE` in the ConfigMap.
- **claw.py** is included as a **git submodule** (at `claw.py/`, pointing to `github.com/Emma-Leonhart/claw.py`). The Dockerfile copies `claw.py/claw.py` into the image at `/usr/local/bin/claw.py`. Do NOT copy the file directly — keep it as a submodule reference.
- **Context injection**: mounting `/krill/context/` volume lets operators inject `init.claw` and `AGENTS.md` before pod startup.

## File layout

```
krill/
├── Dockerfile                  # Ubuntu + Node.js 22 + OpenClaw
├── claw.py                     # Context archive utility
├── config/
│   └── openclaw.json.tpl       # Config template (envsubst at runtime)
├── scripts/
│   └── entrypoint.sh           # Container entrypoint
├── k8s/
│   ├── namespace.yaml
│   ├── secret.yaml             # API key (template — fill before applying)
│   ├── configmap.yaml          # Shared env config
│   ├── statefulset.yaml        # Main workload
│   └── service.yaml            # Headless service
└── README.md
```

## Conventions

- **Python**: use `python3` inside containers (Ubuntu default). On Windows dev machines, use `python` per the global CLAUDE.md.
- **Kubernetes namespace**: `krill`
- **Image name**: `krill:latest` (local dev), tag with semver for production.
- **Port**: 18789 (OpenClaw WebSocket gateway default)
- **Workspace path in container**: `/root/.openclaw/workspace`
- **Context volume in container**: `/krill/context/`

## Things to do next

- Add a `krill-api-server` deployment (LiteLLM proxy) so krill pods don't hit provider APIs directly.
- Add a `Makefile` for common ops (build, push, deploy, scale, exec into pod).
- Consider a Helm chart if per-krill config diverges significantly.
- Add resource limit tuning once real usage patterns are known.
- Add context export CronJob to auto-snapshot workspaces to `.claw` files.
