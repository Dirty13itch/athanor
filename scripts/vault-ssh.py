"""SSH to VAULT via Paramiko first, then native OpenSSH as a fallback."""
import os
import subprocess
import sys
from pathlib import Path

import paramiko
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cluster_config import NODES
from runtime_env import load_optional_runtime_env

load_optional_runtime_env(
    env_names=[
        "ATHANOR_VAULT_USER",
        "ATHANOR_VAULT_PASSWORD",
        "VAULT_SSH_PASSWORD",
        "ATHANOR_VAULT_KEY_PATH",
        "VAULT_SSH_KEY_PATH",
    ]
)

HOST = NODES["vault"]
USER = os.environ.get("ATHANOR_VAULT_USER", "root")
PASSWORD = os.environ.get("ATHANOR_VAULT_PASSWORD") or os.environ.get("VAULT_SSH_PASSWORD", "")


def _resolve_key_path() -> str:
    candidates = [
        os.environ.get("ATHANOR_VAULT_KEY_PATH"),
        os.environ.get("VAULT_SSH_KEY_PATH"),
        str(Path.home() / ".ssh" / "id_ed25519"),
        str(Path.home() / ".ssh" / "athanor_mgmt"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return ""


KEY_PATH = _resolve_key_path()


def _native_ssh_run(command: str) -> int:
    ssh_command = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=10",
    ]
    if KEY_PATH:
        ssh_command.extend(["-i", KEY_PATH])
    ssh_command.append(f"{USER}@{HOST}")
    ssh_command.append(command)

    completed = subprocess.run(
        ssh_command,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    return completed.returncode


def run(command):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        connect_kwargs = {
            "hostname": HOST,
            "username": USER,
            "timeout": 10,
            "look_for_keys": not PASSWORD and not KEY_PATH,
            "allow_agent": not PASSWORD and not KEY_PATH,
        }
        if PASSWORD:
            connect_kwargs["password"] = PASSWORD
        if KEY_PATH:
            connect_kwargs["key_filename"] = KEY_PATH

        client.connect(**connect_kwargs)
        stdin, stdout, stderr = client.exec_command(command, timeout=30)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        rc = stdout.channel.recv_exit_status()
        if out:
            print(out, end="")
        if err:
            print(err, end="", file=sys.stderr)
        return rc
    except Exception as e:
        paramiko_error = str(e).strip() or e.__class__.__name__
        if PASSWORD:
            print(f"SSH error: {paramiko_error}", file=sys.stderr)
            return 1

        native_rc = _native_ssh_run(command)
        if native_rc == 0:
            return 0

        print(f"SSH error: {paramiko_error}", file=sys.stderr)
        return native_rc or 1
    finally:
        client.close()

if __name__ == "__main__":
    cmd = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "echo CONNECTED && hostname && uname -a"
    sys.exit(run(cmd))
