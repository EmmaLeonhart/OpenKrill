# krill

**krill** is a Kubernetes-based deployment for running multiple small [OpenClaw](https://github.com/openclaw/openclaw) agent instances ("krill") in parallel, each working on a different project. Krill pods share a central API server and can carry persistent context between sessions via `.claw` archives.

> Like krill in the ocean — small, numerous, and collectively capable of feeding something much larger.

---

## What is a krill pod?

Each krill pod is:
- An **Ubuntu 24.04** container running **OpenClaw** (Node.js 22)
- Connected to a **central API server** for model routing
- Backed by a **persistent volume** for workspace memory
- Able to **import and export context** as `.claw` archives using `claw.py`

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
         │ project │          │ project │          │ project │
         │    A    │          │    B    │          │    C    │
         └────┬────┘          └────┬────┘          └────┬────┘
              │                    │                    │
         ┌────▼────┐          ┌────▼────┐          ┌────▼────┐
         │  PVC-0  │          │  PVC-1  │          │  PVC-2  │
         │workspace│          │workspace│          │workspace│
         └─────────┘          └─────────┘          └─────────┘
```

Each pod exposes the OpenClaw WebSocket gateway on port **18789**. Pods are assigned stable DNS names via a headless Service:

```
krill-0.krill.krill.svc.cluster.local:18789
krill-1.krill.krill.svc.cluster.local:18789
```

---

## Repository layout

```
krill/
├── Dockerfile                  # Ubuntu + Node.js 22 + OpenClaw base image
├── claw.py                     # Context archive utility (.claw export/import)
├── config/
│   └── openclaw.json.tpl       # OpenClaw config template (env-substituted at runtime)
├── scripts/
│   └── entrypoint.sh           # Container entrypoint
├── k8s/
│   ├── namespace.yaml          # krill namespace
│   ├── secret.yaml             # API key secret (fill before applying)
│   ├── configmap.yaml          # Shared pod configuration
│   ├── statefulset.yaml        # Krill StatefulSet (one PVC per pod)
│   └── service.yaml            # Headless service for stable pod DNS
└── README.md
```

---

## Quick start

### 1. Build the image

```bash
docker build -t krill:latest .
```

### 2. Configure your API key

Edit `k8s/secret.yaml` and replace `REPLACE_WITH_YOUR_API_KEY` with your actual key, then apply:

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secret.yaml -n krill
```

Or create the secret directly:

```bash
kubectl create secret generic krill-api-secret \
  --from-literal=api-key=YOUR_KEY_HERE \
  -n krill
```

### 3. Configure the API server

Edit `k8s/configmap.yaml` to set `OPENCLAW_API_BASE` to your API server's cluster-internal URL. If you're routing directly to Anthropic, set it to `https://api.anthropic.com`.

### 4. Deploy

```bash
kubectl apply -f k8s/ -n krill
```

### 5. Scale up

```bash
# Run 3 krill pods (krill-0, krill-1, krill-2)
kubectl scale statefulset krill --replicas=3 -n krill
```

---

## Context archives (.claw files)

Krill uses `.claw` archives to carry agent context between sessions. A `.claw` file is a portable zip containing conversation traces, scratch notes, and working memory.

**Inject context at pod startup:**

Place an `init.claw` file into the pod's `/krill/context/` volume before it starts. The entrypoint will import it automatically.

**Export context from a running pod:**

```bash
kubectl exec krill-0 -n krill -- \
  python3 /usr/local/bin/claw.py export /root/.openclaw/workspace /krill/context/session.claw
```

**Inspect a .claw archive locally:**

```bash
python3 claw.py info my_session.claw
```

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
