"""Try the new talosctl v1.12.4 binary against Node 2."""
import paramiko
import sys

HOST = "192.168.1.203"
USER = "root"
PASS = "Hockey1298"

cmd = sys.argv[1] if len(sys.argv) > 1 else "/tmp/talosctl version -n 10.10.10.10 -e 10.10.10.10"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASS, timeout=10,
               look_for_keys=False, allow_agent=False)

stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
out = stdout.read().decode("utf-8", errors="replace")
err = stderr.read().decode("utf-8", errors="replace")
rc = stdout.channel.recv_exit_status()

if out:
    print(out, end="")
if err:
    print(err, end="", file=sys.stderr)

client.close()
sys.exit(rc)
