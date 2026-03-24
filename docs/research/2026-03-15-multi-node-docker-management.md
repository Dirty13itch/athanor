# Multi-Node Docker Container Management from Dashboard

**Date:** 2026-03-15
**Status:** Research Complete
**Author:** Research Agent
**Context:** Dashboard on WORKSHOP (.225) needs to manage Docker containers on FOUNDRY (.244) and VAULT (.203) in addition to local WORKSHOP containers.

---

## Current Implementation

The dashboard (`projects/dashboard/src/lib/docker.ts`) uses raw `node:http` requests against the local Docker Unix socket (`/var/run/docker.sock`), mounted read-only into the dashboard container. Three API operations are used:

| Operation | Docker API Endpoint | Method |
|-----------|-------------------|--------|
| List containers | `GET /containers/json?all=true` | Read |
| Restart container | `POST /containers/{id}/restart?t=10` | Write |
| Get logs | `GET /containers/{id}/logs?stdout=true&stderr=true&tail={n}&timestamps=true` | Read |

The dashboard container joins the `docker` group (GID 988) for socket access. The `isDockerAvailable()` function checks socket existence via `fs.accessSync`. A `PROTECTED_CONTAINERS` set prevents restarting the dashboard itself.

The implementation is notably lightweight -- no `dockerode` dependency, just raw HTTP over Unix socket. This is a strength worth preserving.

---

## Requirements

1. Manage containers on 3 nodes: WORKSHOP (local), FOUNDRY (.244), VAULT (.203)
2. Read operations (list, logs) on all nodes; write operations (restart) on WORKSHOP and VAULT; FOUNDRY writes require extra protection per deployment safety rules
3. Must work from inside a Docker container (the dashboard runs in Docker)
4. Ansible-deployable across all nodes
5. Reasonable security on trusted 10GbE LAN (no internet exposure)
6. Reliable -- should not require manual intervention after node reboots

---

## Option 1: SSH Tunnels (autossh/systemd)

**Concept:** Create persistent SSH tunnels from WORKSHOP to FOUNDRY/VAULT that forward the remote Docker socket to a local Unix socket or TCP port. The dashboard container accesses multiple socket paths.

### How It Would Work

On WORKSHOP host (or in a sidecar container):
```bash
# Tunnel FOUNDRY Docker socket to local socket
autossh -M 0 -N -o "ServerAliveInterval=15" -o "ServerAliveCountMax=3" \
  -L /tmp/docker-foundry.sock:/var/run/docker.sock athanor@foundry

# Tunnel VAULT Docker socket to local socket
autossh -M 0 -N -o "ServerAliveInterval=15" -o "ServerAliveCountMax=3" \
  -L /tmp/docker-vault.sock:/var/run/docker.sock athanor@vault
```

Mount all three sockets into the dashboard container:
```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock:ro          # WORKSHOP
  - /tmp/docker-foundry.sock:/var/run/docker-foundry.sock:ro  # FOUNDRY
  - /tmp/docker-vault.sock:/var/run/docker-vault.sock:ro      # VAULT
```

### Evaluation

| Criterion | Rating | Notes |
|-----------|--------|-------|
| Security | Good | Reuses existing SSH keys; no new attack surface; encrypted tunnel |
| Setup Complexity | Medium | autossh + systemd units on WORKSHOP; SSH keys already configured |
| Works in Docker | Yes, with caveats | Sockets must be created on host before container starts; race condition on boot |
| Reliability | Fair | SSH tunnels drop on network blips; autossh reconnects but socket path may become stale; Unix socket forwarding is less reliable than TCP forwarding |
| Ansible Deployable | Yes | systemd unit template + autossh package |
| Code Changes | Minimal | Parameterize socket path per node |

### Risks
- **Boot ordering:** If the dashboard container starts before autossh establishes the tunnel, the socket path won't exist. Requires `depends_on` or health checks.
- **Stale sockets:** If autossh dies and restarts, the old Unix socket file may linger. Needs cleanup logic.
- **SSH from Docker container:** If running autossh inside a sidecar container instead of on the host, SSH key management gets messy.
- **Unix socket forwarding quirks:** SSH's `-L` with Unix sockets is less battle-tested than TCP port forwarding. Some SSH versions have bugs with this.

---

## Option 2: Docker TCP Socket (daemon-level)

**Concept:** Configure the Docker daemon on FOUNDRY and VAULT to listen on a TCP port (2376 with TLS, or 2375 without) in addition to the Unix socket.

### How It Would Work

On FOUNDRY/VAULT, add to `/etc/docker/daemon.json`:
```json
{
  "hosts": ["unix:///var/run/docker.sock", "tcp://0.0.0.0:2376"],
  "tls": true,
  "tlscacert": "/etc/docker/tls/ca.pem",
  "tlscert": "/etc/docker/tls/server-cert.pem",
  "tlskey": "/etc/docker/tls/server-key.pem",
  "tlsverify": true
}
```

Dashboard would connect via HTTPS:
```typescript
const req = https.request({
  host: '192.168.1.244', port: 2376,
  path: '/containers/json?all=true',
  cert: clientCert, key: clientKey, ca: caCert
});
```

### Evaluation

| Criterion | Rating | Notes |
|-----------|--------|-------|
| Security | Requires TLS | Without TLS, this is root access to the host for anyone on the LAN. With mutual TLS, it's well-secured but complex to manage certs. |
| Setup Complexity | High | PKI setup (CA + server certs + client certs), daemon config changes, systemd override for `-H` flag conflicts, cert rotation |
| Works in Docker | Yes | TCP connections work natively from containers; mount client certs as volumes |
| Reliability | Excellent | No tunnels to maintain; direct TCP connection; Docker daemon handles it natively |
| Ansible Deployable | Yes but fragile | Daemon config changes require Docker restart, which restarts all containers |
| Code Changes | Small | Switch from `socketPath` to `host`/`port` + TLS options |

### Risks
- **FOUNDRY daemon restart:** Changing daemon config on FOUNDRY requires restarting dockerd, which restarts ALL running containers including vLLM coordinator, agents, etc. This is a production-impacting change.
- **VAULT (Unraid):** Unraid manages Docker differently. Modifying daemon.json may conflict with Unraid's Docker management UI.
- **TLS cert management:** Need a CA, server certs per node, client cert for dashboard. Cert rotation is ongoing overhead.
- **Without TLS:** Anyone on the LAN gets root access to the host. Unacceptable even on a trusted network -- a single compromised IoT device could own the cluster.

---

## Option 3: Docker Context / Dockerode SSH

**Concept:** Use `dockerode` (Node.js Docker client library) with its built-in SSH transport (`protocol: 'ssh'`) to connect directly to remote Docker daemons.

### How It Would Work

```typescript
import Docker from 'dockerode';

const foundry = new Docker({
  protocol: 'ssh',
  host: '192.168.1.244',
  port: 22,
  username: 'athanor',
  sshOptions: {
    privateKey: fs.readFileSync('/home/node/.ssh/id_ed25519'),
  },
});

const containers = await foundry.listContainers({ all: true });
```

### Evaluation

| Criterion | Rating | Notes |
|-----------|--------|-------|
| Security | Good | Reuses existing SSH infrastructure; no new ports or daemons |
| Setup Complexity | Low | Just add `dockerode` dependency and SSH key mount |
| Works in Docker | Yes | Mount SSH keys into container (already done for ws-pty-bridge) |
| Reliability | Poor | dockerode's SSH transport uses `ssh2` library which has known issues with uncaught exceptions on timeouts/disconnects (GitHub issue #621). Errors bypass normal error handling and crash the Node.js process. |
| Ansible Deployable | N/A | No server-side changes needed |
| Code Changes | Large | Would need to replace the current raw `node:http` approach with dockerode, or maintain two code paths |

### Risks
- **Process crashes:** The `ssh2` library used by `docker-modem` throws uncaught exceptions on SSH handshake timeouts rather than propagating errors through callbacks/promises. This would crash the Next.js server process.
- **Dependency bloat:** Adding `dockerode` + `docker-modem` + `ssh2` is a significant dependency chain for 3 simple API calls.
- **Architectural mismatch:** The current implementation is elegantly minimal (raw HTTP). Switching to dockerode changes the entire approach.
- **SSH key in container:** Need to mount SSH private key into the dashboard container. The ws-pty-bridge already does this, but it's another secret to manage.

---

## Option 4: Docker Socket Proxy Sidecar (Recommended)

**Concept:** Deploy a lightweight Docker socket proxy container (Tecnativa/docker-socket-proxy or LinuxServer equivalent) on each remote node. The proxy exposes the Docker API over HTTP on a configurable port, with granular API filtering via environment variables.

### How It Would Work

On FOUNDRY and VAULT, deploy a socket proxy container:

```yaml
# docker-compose.socket-proxy.yml (deployed to each node)
services:
  docker-proxy:
    image: lscr.io/linuxserver/socket-proxy:latest
    container_name: docker-socket-proxy
    restart: unless-stopped
    environment:
      - CONTAINERS=1    # Allow container list/inspect
      - POST=1          # Allow restart operations
      - LOG_LEVEL=info
      # Everything else defaults to 0 (blocked)
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    ports:
      - "127.0.0.1:2375:2375"  # Listen only on localhost by default
    # For remote access, bind to LAN IP:
    # - "192.168.1.244:2375:2375"
```

For FOUNDRY (read-only to enforce deployment safety):
```yaml
environment:
  - CONTAINERS=1
  - POST=0          # No restart from dashboard -- FOUNDRY is production
  - LOG_LEVEL=info
```

Dashboard `docker.ts` would become multi-node aware:

```typescript
import http from "node:http";

interface DockerHost {
  name: string;
  /** Unix socket path for local, or undefined for remote */
  socketPath?: string;
  /** HTTP host:port for remote nodes */
  host?: string;
  port?: number;
  /** Whether restart is allowed (FOUNDRY = false) */
  allowRestart: boolean;
}

const DOCKER_HOSTS: DockerHost[] = [
  { name: "workshop", socketPath: "/var/run/docker.sock", allowRestart: true },
  { name: "foundry",  host: "192.168.1.244", port: 2375, allowRestart: false },
  { name: "vault",    host: "192.168.1.203", port: 2375, allowRestart: true },
];

function dockerRequest<T>(host: DockerHost, method: string, path: string): Promise<T> {
  return new Promise((resolve, reject) => {
    const options = host.socketPath
      ? { socketPath: host.socketPath, path, method, headers: { "Content-Type": "application/json" } }
      : { host: host.host, port: host.port, path, method, headers: { "Content-Type": "application/json" } };

    const req = http.request(options, (res) => {
      let data = "";
      res.on("data", (chunk) => (data += chunk));
      res.on("end", () => {
        if (res.statusCode && res.statusCode >= 200 && res.statusCode < 300) {
          resolve(data ? (JSON.parse(data) as T) : (undefined as T));
        } else {
          reject(new Error(`Docker API [${host.name}] ${method} ${path}: ${res.statusCode} ${data}`));
        }
      });
    });
    req.on("error", reject);
    req.setTimeout(15_000, () => {
      req.destroy();
      reject(new Error(`Docker API timeout [${host.name}]: ${method} ${path}`));
    });
    req.end();
  });
}
```

### Evaluation

| Criterion | Rating | Notes |
|-----------|--------|-------|
| Security | Good | API filtering at the proxy level (granular per-endpoint); can set FOUNDRY to read-only; no daemon changes; bind to LAN IP only (not 0.0.0.0); plain HTTP is acceptable on trusted LAN with no internet exposure |
| Setup Complexity | Low | One container per remote node; standard docker-compose; no certs, no tunnels, no daemon changes |
| Works in Docker | Yes | Plain HTTP from dashboard container to remote host:port -- no socket mounting needed for remote nodes |
| Reliability | Excellent | No tunnels to maintain; proxy container restarts with Docker; standard HTTP connections with timeouts |
| Ansible Deployable | Easy | Ansible role deploys compose file + starts service; no daemon restarts needed |
| Code Changes | Minimal | Extend existing `dockerRequest` to accept host/port in addition to socketPath; same HTTP library, same response parsing |

### Risks
- **Plain HTTP on LAN:** The proxy exposes an unauthenticated HTTP API on the LAN. Mitigated by: (a) binding to specific LAN IP not 0.0.0.0, (b) API filtering blocks dangerous operations, (c) trusted LAN with no internet exposure, (d) FOUNDRY proxy is read-only.
- **Port exposure:** Port 2375 on each node. Could use a non-standard port to reduce accidental discovery, but security-through-obscurity is not a real mitigation.
- **Container overhead:** One additional container per node. Minimal -- HAProxy-based proxy uses ~5MB RAM.

---

## Comparative Summary

| Criterion | SSH Tunnel | TCP Socket | Dockerode SSH | Socket Proxy |
|-----------|-----------|------------|---------------|--------------|
| Security | Good (encrypted) | Good (with TLS) | Good (SSH) | Acceptable (LAN-only HTTP + API filtering) |
| Setup Complexity | Medium | High | Low | **Low** |
| Docker-compatible | Fair (race conditions) | **Yes** | Yes (but crashes) | **Yes** |
| Reliability | Fair (tunnel drops) | **Excellent** | **Poor** (crashes) | **Excellent** |
| Ansible Deploy | Medium | Fragile (daemon restart) | None needed | **Easy** |
| Code Changes | Minimal | Small | Large (new dep) | **Minimal** |
| FOUNDRY Safety | Manual enforcement | Manual enforcement | Manual enforcement | **Enforced at proxy level** |
| Daemon Changes | None | Required | None | **None** |
| Dependencies | autossh on host | TLS PKI | dockerode + ssh2 | 1 container per node |

---

## Recommendation: Option 4 -- Docker Socket Proxy

The socket proxy approach wins on nearly every axis for this use case:

1. **Minimal code change.** The current `docker.ts` uses raw `node:http` -- the proxy speaks the same Docker API over HTTP. The only change is adding `host`/`port` as an alternative to `socketPath`. No new dependencies.

2. **FOUNDRY safety built-in.** Setting `POST=0` on FOUNDRY's proxy enforces the deployment safety rule at the infrastructure level, not just in application code. Even if a bug in the dashboard tries to restart a FOUNDRY container, the proxy returns 403.

3. **No daemon changes.** Unlike TCP socket, this requires zero changes to Docker daemon configuration. No daemon restarts, no FOUNDRY production disruption, no Unraid conflicts on VAULT.

4. **Excellent reliability.** No SSH tunnels to drop. The proxy is a container that restarts with Docker. HTTP connections are stateless with built-in timeouts.

5. **Trivially Ansible-deployable.** One role that drops a compose file and starts the service. No PKI, no key distribution, no systemd tunnel units.

6. **Acceptable security for trusted LAN.** The proxy filters API access (only containers endpoint + logs). FOUNDRY is read-only. The HTTP endpoint is bound to the LAN IP only. On a network with no internet ingress and 5 known hosts, this is proportionate security.

### Implementation Plan

**Phase 1 -- Infrastructure (Ansible)**
- Create `ansible/roles/docker-socket-proxy/` role
- Deploy to FOUNDRY (read-only: `POST=0, CONTAINERS=1`) and VAULT (read-write: `POST=1, CONTAINERS=1`)
- Use port 2375 (standard Docker API port)
- Bind to specific LAN IPs, not 0.0.0.0

**Phase 2 -- Dashboard Code**
- Extend `docker.ts` with multi-host support (host config from env vars)
- Add `node` field to container API responses so the UI knows which node each container is on
- Update `PROTECTED_CONTAINERS` to be node-aware
- FOUNDRY containers should show "restart disabled (production)" in UI
- Add env vars: `ATHANOR_FOUNDRY_DOCKER_URL`, `ATHANOR_VAULT_DOCKER_URL`

**Phase 3 -- Dashboard UI**
- Add node selector/filter to container management view
- Color-code or group containers by node
- Show node health status alongside container list

### Estimated Effort
- Ansible role: ~1 hour
- docker.ts refactor: ~1 hour
- API route updates: ~30 min
- UI updates: ~2 hours
- Total: ~4.5 hours

---

## Sources

- [Docker Docs: Protect the Docker daemon socket](https://docs.docker.com/engine/security/protect-access/)
- [Docker Docs: Configure remote access](https://docs.docker.com/engine/daemon/remote-access/)
- [Tecnativa/docker-socket-proxy (GitHub)](https://github.com/Tecnativa/docker-socket-proxy)
- [LinuxServer.io socket-proxy docs](https://docs.linuxserver.io/images/docker-socket-proxy/)
- [dockerode (GitHub)](https://github.com/apocas/dockerode)
- [dockerode SSH uncaughtException issue #621](https://github.com/apocas/dockerode/issues/621)
- [Autossh persistent tunnels](https://trangelier.dev/autossh-for-persistent-tunnels/)
- [Persistent SSH tunnel with systemd (GitHub Gist)](https://gist.github.com/MohamedElashri/8cbb2ba8d04d6351a4ead02dcc258339)
- [How to Secure Docker's TCP Socket With TLS](https://www.howtogeek.com/devops/how-to-secure-dockers-tcp-socket-with-tls/)
- [Docker Security Best Practices 2026 (TheLinuxCode)](https://thelinuxcode.com/docker-security-best-practices-2026-hardening-the-host-images-and-runtime-without-slowing-teams-down/)
- [FoxxMD: Restricting Docker Socket Proxy by Container](https://blog.foxxmd.dev/posts/restricting-socket-proxy-by-container/)
