# krill — Getting to Running

Gaps identified before the system can be built and deployed for the first time.
Work through these in order — items higher up unblock items below them.

---

## Hard blockers

### 1. Confirm the `openclaw` npm package exists
The Dockerfile does `npm install -g openclaw@latest`. If this package doesn't
exist on npm (or has a different name), the Docker build fails and nothing else
matters. Before anything else:

- [ ] Check that `openclaw` is published on npm and has a `gateway` subcommand
- [ ] Confirm the exact flag syntax: `openclaw gateway --port 18789` (or adjust
      `scripts/entrypoint.sh` line 42 if the flag differs)

### 2. Create `k8s/secret.yaml`
The file is gitignored and must be created locally before deploying.

```bash
cp k8s/secret.example.yaml k8s/secret.yaml
# Edit k8s/secret.yaml — replace REPLACE_WITH_YOUR_API_KEY with your real key
```

### 3. Decide on API routing and fix `configmap.yaml`
`OPENCLAW_API_BASE` currently points at `http://krill-api-server:8080`, which
doesn't exist yet. Two options:

- **Option A — Direct Anthropic (for initial testing):** Change `configmap.yaml`
  to `https://api.anthropic.com`. Simplest path to a first working pod.
- **Option B — Deploy a LiteLLM proxy:** Create `k8s/api-server/` with a
  LiteLLM Deployment + ClusterIP Service named `krill-api-server`. Required
  for the full intended architecture (see CLAUDE.md "things to do next").

- [ ] Pick an option and update `k8s/configmap.yaml` accordingly

### 4. Have a Kubernetes cluster running
Nothing in this repo sets one up. Pick a local option:

- Docker Desktop → Settings → Kubernetes → Enable
- `minikube start`
- `kind create cluster`

- [ ] Cluster running and `kubectl cluster-info` returns OK

---

## Likely functional bug (fix before first deploy)

### 5. Add `apiKey` to `config/openclaw.json.tpl`
The API key is injected as `OPENCLAW_API_KEY` into the container environment
but is **never written into `openclaw.json`**. If OpenClaw reads its key from
the config file rather than the environment, it will fail to authenticate.

Current template (`config/openclaw.json.tpl`):
```json
{
  "agent": {
    "model": "${OPENCLAW_MODEL}",
    "apiBase": "${OPENCLAW_API_BASE}",
    "workspace": "/root/.openclaw/workspace"
  }
}
```

Likely needs to become:
```json
{
  "agent": {
    "model": "${OPENCLAW_MODEL}",
    "apiBase": "${OPENCLAW_API_BASE}",
    "apiKey": "${OPENCLAW_API_KEY}",
    "workspace": "/root/.openclaw/workspace"
  }
}
```

- [ ] Check OpenClaw docs/source for the correct config key name
- [ ] Update `config/openclaw.json.tpl` accordingly

---

## Build and deploy steps (once blockers are resolved)

```bash
# 1. Build the image
docker build -t krill:latest .

# 2. Load into local cluster if needed (minikube/kind)
# minikube: minikube image load krill:latest
# kind:     kind load docker-image krill:latest

# 3. Apply manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secret.yaml -n krill
kubectl apply -f k8s/configmap.yaml -n krill
kubectl apply -f k8s/service.yaml -n krill
kubectl apply -f k8s/statefulset.yaml -n krill

# 4. Watch pod come up
kubectl get pods -n krill -w

# 5. Check logs
kubectl logs krill-0 -n krill

# 6. Port-forward to test the gateway locally
kubectl port-forward pod/krill-0 18789:18789 -n krill
```

---

## Nice-to-have (non-blocking)

- [ ] **Makefile** — wrap the build/deploy/exec commands above so they're
      one-liners (`make build`, `make deploy`, `make logs`, `make shell`)
- [ ] **Non-headless Service** — add a ClusterIP or NodePort service for
      reaching the gateway without `port-forward` during development
- [ ] **`krill-api-server` deployment** — LiteLLM proxy so pods don't hit
      provider APIs directly (see CLAUDE.md "things to do next")
- [ ] **Context export CronJob** — auto-snapshot workspaces to `.claw` files
      on a schedule (see CLAUDE.md "things to do next")
