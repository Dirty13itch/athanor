"""SSH to VAULT and run commands via paramiko."""
import os
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
        print(f"SSH error: {e}", file=sys.stderr)
        return 1
    finally:
        client.close()

if __name__ == "__main__":
    cmd = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "echo CONNECTED && hostname && uname -a"
    sys.exit(run(cmd))
