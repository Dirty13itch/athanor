---
paths:
  - "**/docker-compose.yml*"
  - "**/docker-compose.*.yml"
  - "**/Dockerfile*"
---

# Docker & Container Conventions

## Compose Standards
- Always include `restart: unless-stopped`
- Always include explicit `container_name:`
- Always include log rotation:
  ```yaml
  logging:
    driver: json-file
    options:
      max-size: "50m"
      max-file: "3"
  ```
- Set `TZ=America/Chicago` for all containers
- Add health checks for services with HTTP endpoints
- Pin image tags in production (`:latest` only when intentionally tracking upstream)

## GPU Services
- Include `ipc: host` and `ulimits: memlock: -1`
- Set `CUDA_DEVICE_ORDER=PCI_BUS_ID` for mixed GPU configurations
- Use `deploy.resources.reservations.devices` for GPU assignment

## Build Standards
- Multi-stage builds to reduce image size
- `--no-install-recommends` for apt packages
- Clean apt cache in same RUN layer: `&& rm -rf /var/lib/apt/lists/*`
- Copy package manifests before source code (layer caching)
- Run as non-root user where possible

## Gotchas
- `docker_compose_v2` Ansible module: add "stop before rebuild" tasks when Dockerfile changes
- CRLF drift from WSL: first convergence run fixes, second is clean
- Container name conflicts: `docker rm -f <name>` before `up -d` if stuck
