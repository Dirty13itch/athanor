"""SSH to VAULT and run commands via paramiko."""
import os
import sys
import paramiko

HOST = os.environ.get("ATHANOR_VAULT_HOST", "192.168.1.203")
USER = os.environ.get("ATHANOR_VAULT_USER", "root")
PASSWORD = os.environ.get("ATHANOR_VAULT_PASSWORD") or os.environ.get("VAULT_SSH_PASSWORD", "")
KEY_PATH = os.environ.get("ATHANOR_VAULT_KEY_PATH") or os.environ.get("VAULT_SSH_KEY_PATH", "")

def run(command):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        connect_kwargs = {
            "hostname": HOST,
            "username": USER,
            "timeout": 10,
            "look_for_keys": not PASSWORD,
            "allow_agent": not PASSWORD,
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
