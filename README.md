# krill

**krill** is a Kubernetes deployment for running multiple small [OpenClaw](https://github.com/openclaw/openclaw) agent instances in parallel, each working on a different project. Krill pods share a central API server and carry persistent context between sessions using the [`.claw` archive format](https://github.com/Emma-Leonhart/claw.py).

> Like krill in the ocean — small, numerous, and collectively capable of feeding something much larger.

---

## The three pieces

| Piece | What it is |
|---|---|
| **[OpenClaw](https://github.com/openclaw/openclaw)** | The AI agent runtime. Each krill pod runs one OpenClaw instance. |
| **krill** (this repo) | The Kubernetes infrastructure for running many OpenClaw pods at once, one per project. |
| **[claw.py](https://github.com/Emma-Leonhart/claw.py)** | A separate tool for packaging agent context into portable `.claw` archives. Included here as a git submodule. |

### What is a `.claw` file?

A `.claw` file is a portable zip archive that captures an OpenClaw agent's working context — conversation traces, scratch notes, memory, and session state. It can be imported into a pod at startup to resume a previous session, and exported from a running pod to save progress.

This is how krill persists agent context across pod restarts and transfers context between pods.

---

## Architecture

```
                        ┌─────────────────────┐
                        │   krill-api-server   │
                        │  (LiteLLM proxy /    │
                        │   OpenAI-compat API) │
                        └──────────┬──────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
         ┌────▼────┐          ┌────▼────┐          ┌────▼────┐
         │ krill-0 │          │ krill-1 │          │ krill-2 │
         │OpenClaw │          │OpenClaw │          │OpenClaw │
         │project A│          │project B│          │project C│
         └────┬────┘          └────┬────┘          └────┬────┘
              │                    │                    │
         ┌────▼────┐          ┌────▼────┐          ┌────▼────┐
         │  PVC-0  │          │  PVC-1  │          │  PVC-2  │
         │workspace│          │workspace│          │workspace│
         └─────────┘          └─────────┘          └─────────┘
```

Each pod runs the OpenClaw WebSocket gateway on port **18789** and gets a stable DNS name via a headless Service:

```
krill-0.krill.krill.svc.cluster.local:18789
krill-1.krill.krill.svc.cluster.local:18789
```

---

## Repository layout

```
krill/
├── Dockerfile                  # Ubuntu 24.04 + Node.js 22 + OpenClaw + claw.py
├── claw.py/                    # git submodule — the .claw archive tool
│   └── claw.py                 #   (from github.com/Emma-Leonhart/claw.py)
├── config/
│   └── openclaw.json.tpl       # OpenClaw config template (env-substituted at runtime)
├── scripts/
│   └── entrypoint.sh           # Container entrypoint
├── k8s/
│   ├── namespace.yaml          # krill namespace
│   ├── secret.example.yaml     # API key secret template (copy → secret.yaml, fill, apply)
│   ├── configmap.yaml          # Shared pod configuration
│   ├── statefulset.yaml        # Krill StatefulSet (one PVC per pod)
│   └── service.yaml            # Headless service for stable pod DNS
└── README.md
```

---

## Quick start

### 1. Clone with submodules

```bash
git clone --recurse-submodules https://github.com/YOUR_ORG/krill.git
# or if already cloned:
git submodule update --init
```

### 2. Build the image

```bash
docker build -t krill:latest .
```

### 3. Configure your API key

```bash
cp k8s/secret.example.yaml k8s/secret.yaml
# Edit k8s/secret.yaml — fill in your API key
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secret.yaml -n krill
```

### 4. Set the API server URL

Edit `k8s/configmap.yaml` and set `OPENCLAW_API_BASE` to your cluster-internal API server URL.

### 5. Deploy

```bash
kubectl apply -f k8s/ -n krill
```

### 6. Scale

```bash
# Run 3 krill pods (krill-0, krill-1, krill-2)
kubectl scale statefulset krill --replicas=3 -n krill
```

---

## Context lifecycle with `.claw` files

### Inject context at pod startup

Drop an `init.claw` file into the pod's `/krill/context/` volume before it starts. The entrypoint imports it automatically into the OpenClaw workspace.

### Export context from a running pod

```bash
kubectl exec krill-0 -n krill -- \
  python3 /usr/local/bin/claw.py export /root/.openclaw/workspace /krill/context/session.claw
```

### Inspect a `.claw` archive locally

```bash
python3 claw.py/claw.py info my_session.claw
```

See the [claw.py repo](https://github.com/Emma-Leonhart/claw.py) for full documentation on the archive format.

---

## Configuration reference

| Environment variable   | Default                        | Description                              |
|------------------------|--------------------------------|------------------------------------------|
| `OPENCLAW_MODEL`       | `anthropic/claude-opus-4-6`    | LiteLLM-style model string               |
| `OPENCLAW_API_BASE`    | `http://krill-api-server:8080` | Base URL of the API server               |
| `OPENCLAW_API_KEY`     | *(from Secret)*                | API key injected from `krill-api-secret` |
| `KRILL_NAME`           | *(pod name)*                   | Auto-set from pod metadata               |

---

## License

MIT — same as OpenClaw.
