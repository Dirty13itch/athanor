"""Probes + remediation actions for the Athanor Watchdog MVW.

- http_check: GET probe via httpx, optionally requires substring in body
- tcp_check: socket connect (for Redis-style checks)
- ssh_check: invoke a command via SSH and check exit code + stdout
- restart_container: SSH to node, run docker restart {name}
- page_ntfy: POST to ntfy with title/priority headers, never raises
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass

import httpx

logger = logging.getLogger("athanor.watchdog")

NTFY_URL = os.environ.get("WATCHDOG_NTFY_URL", "http://192.168.1.203:8880")
NTFY_TOPIC_DEFAULT = os.environ.get("WATCHDOG_NTFY_TOPIC", "athanor-infra")

# Per-node SSH user mapping (matches FOUNDRY athanor's ~/.ssh/config Host entries)
NODE_USERS = {
    "foundry": "athanor",
    "workshop": "athanor",
    "dev": "shaun",
    "vault": "root",
}
NODE_HOSTS = {
    "foundry": "192.168.1.244",
    "workshop": "192.168.1.225",
    "dev": "192.168.1.189",
    "vault": "192.168.1.203",
}
SSH_KEY_PATH = os.environ.get("WATCHDOG_SSH_KEY", "/ssh-keys/watchdog_key")


@dataclass
class CheckResult:
    ok: bool
    latency_ms: int
    msg: str


@dataclass
class RemediationResult:
    success: bool
    error: str
    duration_ms: int


# --- Probes ---


async def http_check(
    url: str,
    accept_codes: tuple = (200,),
    body_must_contain: str = None,
    timeout: float = 10.0,
) -> CheckResult:
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            resp = await client.get(url)
        latency = int((time.monotonic() - start) * 1000)
        if resp.status_code not in accept_codes:
            return CheckResult(False, latency, f"http {resp.status_code} not in {accept_codes}")
        if body_must_contain and body_must_contain not in resp.text:
            return CheckResult(False, latency, f"body missing '{body_must_contain}'")
        return CheckResult(True, latency, f"http {resp.status_code}")
    except httpx.TimeoutException:
        latency = int((time.monotonic() - start) * 1000)
        return CheckResult(False, latency, f"timeout after {timeout}s")
    except Exception as e:
        latency = int((time.monotonic() - start) * 1000)
        return CheckResult(False, latency, f"{type(e).__name__}: {str(e)[:120]}")


async def tcp_check(url: str, timeout: float = 5.0) -> CheckResult:
    start = time.monotonic()
    try:
        target = url.removeprefix("tcp://")
        host, port_s = target.rsplit(":", 1)
        port = int(port_s)
        fut = asyncio.open_connection(host, port)
        reader, writer = await asyncio.wait_for(fut, timeout=timeout)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        latency = int((time.monotonic() - start) * 1000)
        return CheckResult(True, latency, "tcp connect ok")
    except Exception as e:
        latency = int((time.monotonic() - start) * 1000)
        return CheckResult(False, latency, f"{type(e).__name__}: {str(e)[:120]}")


async def ssh_check(url: str, timeout: float = 8.0) -> CheckResult:
    start = time.monotonic()
    try:
        rest = url.removeprefix("ssh://")
        node, _, cmd = rest.partition("/")
        if not node or not cmd:
            return CheckResult(False, 0, f"bad ssh url: {url}")
        user = NODE_USERS.get(node, "athanor")
        host = NODE_HOSTS.get(node, node)
        proc = await asyncio.create_subprocess_exec(
            "ssh",
            "-i", SSH_KEY_PATH,
            "-F", "/dev/null",
            "-o", "ConnectTimeout=5",
            "-o", "BatchMode=yes",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "LogLevel=ERROR",
            "-l", user,
            host,
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        latency = int((time.monotonic() - start) * 1000)
        if proc.returncode != 0:
            return CheckResult(False, latency, f"ssh exit {proc.returncode}: {stderr[:120].decode(errors='replace')}")
        out = stdout.decode(errors="replace").strip()
        if out and out.isdigit() and not out.startswith("2"):
            return CheckResult(False, latency, f"http {out}")
        return CheckResult(True, latency, f"ssh ok ({out[:60]})")
    except asyncio.TimeoutError:
        return CheckResult(False, int(timeout * 1000), f"ssh timeout after {timeout}s")
    except Exception as e:
        latency = int((time.monotonic() - start) * 1000)
        return CheckResult(False, latency, f"{type(e).__name__}: {str(e)[:120]}")


# --- Remediation ---


async def restart_container(node: str, container: str, timeout: float = 30.0) -> RemediationResult:
    start = time.monotonic()
    try:
        user = NODE_USERS.get(node, "athanor")
        host = NODE_HOSTS.get(node, node)
        proc = await asyncio.create_subprocess_exec(
            "ssh",
            "-i", SSH_KEY_PATH,
            "-F", "/dev/null",
            "-o", "ConnectTimeout=5",
            "-o", "BatchMode=yes",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "LogLevel=ERROR",
            "-l", user,
            host,
            f"docker restart {container}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        duration = int((time.monotonic() - start) * 1000)
        if proc.returncode == 0:
            return RemediationResult(True, "", duration)
        return RemediationResult(False, stderr[:200].decode(errors="replace"), duration)
    except asyncio.TimeoutError:
        return RemediationResult(False, f"timeout after {timeout}s", int(timeout * 1000))
    except Exception as e:
        duration = int((time.monotonic() - start) * 1000)
        return RemediationResult(False, f"{type(e).__name__}: {str(e)[:200]}", duration)


# --- Notification ---


async def page_ntfy(
    title: str,
    message: str,
    topic: str = NTFY_TOPIC_DEFAULT,
    priority: str = "default",
    tags: str = None,
) -> None:
    """Send an ntfy notification. Never raises — failure is logged only."""
    try:
        url = f"{NTFY_URL}/{topic}"
        headers = {
            "Title": title[:200],
            "Priority": priority,
        }
        if tags:
            headers["Tags"] = tags
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, content=message[:2000], headers=headers)
        if resp.status_code >= 400:
            logger.warning("ntfy failed (%s) for topic=%s title=%s", resp.status_code, topic, title)
    except Exception as e:
        logger.warning("ntfy exception: %s", e)
