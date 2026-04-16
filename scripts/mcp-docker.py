#!/usr/bin/env python3
"""MCP server: multi-node Docker management via SSH.

Manages containers across Foundry (Node 1), Workshop (Node 2), and VAULT.
Uses SSH to run docker commands on remote hosts since DEV has no local Docker.

Usage in .mcp.json:
  "docker": {
    "type": "stdio",
    "command": "python3",
    "args": ["scripts/mcp-docker.py"],
    "env": {}
  }
"""

import json
import os
import subprocess
import sys

from mcp.server.fastmcp import FastMCP
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cluster_config import NODES

NODES = {
    "foundry": {"ssh": "node1", "ip": NODES["foundry"], "role": "AI inference + agents"},
    "workshop": {"ssh": "node2", "ip": NODES["workshop"], "role": "Creative + interface"},
    "vault": {"ssh": None, "ip": NODES["vault"], "role": "Storage + media + monitoring"},
}

VAULT_SSH_SCRIPT = os.path.join(os.path.dirname(__file__), "vault-ssh.py")

mcp = FastMCP("docker")


def _ssh(node: str, cmd: str, timeout: int = 30) -> str:
    """Run a command on a node via SSH. Returns stdout or error string."""
    info = NODES.get(node.lower())
    if not info:
        return f"Unknown node: {node}. Valid: {', '.join(NODES)}"

    try:
        if node.lower() == "vault":
            result = subprocess.run(
                ["python3", VAULT_SSH_SCRIPT, cmd],
                capture_output=True, text=True, timeout=timeout,
            )
        else:
            result = subprocess.run(
                ["ssh", "-o", "ConnectTimeout=5", info["ssh"], cmd],
                capture_output=True, text=True, timeout=timeout,
            )

        output = result.stdout.strip()
        if result.returncode != 0 and result.stderr.strip():
            output += f"\nSTDERR: {result.stderr.strip()}"
        return output or "(no output)"
    except subprocess.TimeoutExpired:
        return f"Timeout ({timeout}s) running command on {node}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def list_containers(node: str = "all", all_containers: bool = False) -> str:
    """List Docker containers on one or all nodes.

    Args:
        node: Node name (foundry, workshop, vault) or "all" for every node.
        all_containers: Include stopped containers (default: only running).
    """
    flag = "-a" if all_containers else ""
    fmt = '{{.Names}}\t{{.Status}}\t{{.Image}}\t{{.Ports}}'
    cmd = f'docker ps {flag} --format "table {fmt}"'

    if node.lower() == "all":
        parts = []
        for n in NODES:
            result = _ssh(n, cmd)
            parts.append(f"=== {n.upper()} ({NODES[n]['role']}) ===\n{result}")
        return "\n\n".join(parts)
    return _ssh(node, cmd)


@mcp.tool()
def container_logs(node: str, container: str, lines: int = 50) -> str:
    """Get recent logs from a Docker container.

    Args:
        node: Node name (foundry, workshop, vault).
        container: Container name or ID.
        lines: Number of log lines to return (default: 50).
    """
    return _ssh(node, f"docker logs --tail {lines} {container}", timeout=15)


@mcp.tool()
def container_inspect(node: str, container: str) -> str:
    """Get detailed info about a container (image, env, mounts, ports, health).

    Args:
        node: Node name (foundry, workshop, vault).
        container: Container name or ID.
    """
    fmt = json.dumps({
        "Name": "{{.Name}}",
        "Image": "{{.Config.Image}}",
        "Status": "{{.State.Status}}",
        "Health": "{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}",
        "StartedAt": "{{.State.StartedAt}}",
        "RestartCount": "{{.RestartCount}}",
        "Ports": "{{range $k, $v := .NetworkSettings.Ports}}{{$k}}->{{range $v}}{{.HostPort}}{{end}} {{end}}",
    })
    return _ssh(node, f"docker inspect --format '{fmt}' {container}")


@mcp.tool()
def restart_container(node: str, container: str) -> str:
    """Restart a Docker container.

    Args:
        node: Node name (foundry, workshop, vault).
        container: Container name or ID.
    """
    return _ssh(node, f"docker restart {container}", timeout=60)


@mcp.tool()
def container_stats(node: str = "all") -> str:
    """Get CPU/memory usage for running containers on a node.

    Args:
        node: Node name (foundry, workshop, vault) or "all".
    """
    cmd = 'docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"'

    if node.lower() == "all":
        parts = []
        for n in NODES:
            result = _ssh(n, cmd, timeout=15)
            parts.append(f"=== {n.upper()} ===\n{result}")
        return "\n\n".join(parts)
    return _ssh(node, cmd, timeout=15)


@mcp.tool()
def compose_status(node: str, project_dir: str = "") -> str:
    """Show docker compose service status on a node.

    Args:
        node: Node name (foundry, workshop, vault).
        project_dir: Optional project directory. If empty, shows all compose projects.
    """
    if project_dir:
        return _ssh(node, f"cd {project_dir} && docker compose ps")
    return _ssh(node, "docker compose ls && echo '---' && docker ps --format '{{.Names}}\t{{.Status}}'")


@mcp.tool()
def compose_restart(node: str, project_dir: str, service: str = "") -> str:
    """Restart docker compose services.

    Args:
        node: Node name (foundry, workshop, vault).
        project_dir: Path to the docker compose project directory.
        service: Specific service to restart (empty = all services).
    """
    svc = service if service else ""
    return _ssh(node, f"cd {project_dir} && docker compose restart {svc}", timeout=120)


@mcp.tool()
def compose_pull_rebuild(node: str, project_dir: str, service: str = "") -> str:
    """Pull latest images and rebuild/restart docker compose services.

    Args:
        node: Node name (foundry, workshop, vault).
        project_dir: Path to the docker compose project directory.
        service: Specific service (empty = all).
    """
    svc = service if service else ""
    return _ssh(
        node,
        f"cd {project_dir} && docker compose pull {svc} && docker compose up -d --build {svc}",
        timeout=300,
    )


@mcp.tool()
def docker_disk_usage(node: str) -> str:
    """Show Docker disk usage (images, containers, volumes, build cache).

    Args:
        node: Node name (foundry, workshop, vault).
    """
    return _ssh(node, "docker system df")


@mcp.tool()
def docker_prune(node: str, what: str = "system") -> str:
    """Prune unused Docker resources to free disk space.

    Args:
        node: Node name (foundry, workshop, vault).
        what: What to prune — "system" (all unused), "images", "containers", "volumes".
    """
    valid = {"system", "images", "containers", "volumes"}
    if what not in valid:
        return f"Invalid target: {what}. Valid: {', '.join(valid)}"
    return _ssh(node, f"docker {what} prune -f", timeout=120)


if __name__ == "__main__":
    mcp.run()
