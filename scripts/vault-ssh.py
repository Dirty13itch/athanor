"""SSH to VAULT and run commands via paramiko."""
import sys
import paramiko

HOST = "192.168.1.203"
USER = "root"
PASS = "Hockey1298"

def run(command):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(HOST, username=USER, password=PASS, timeout=10,
                       look_for_keys=False, allow_agent=False)
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
