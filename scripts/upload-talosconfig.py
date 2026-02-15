"""Upload talosconfig to VAULT and set endpoints."""
import paramiko
import os

HOST = "192.168.1.203"
USER = "root"
PASS = "Hockey1298"

# Read the local talosconfig
with open(r"C:\Users\Shaun\kaizen-core\talosconfig", "r") as f:
    config = f.read()

# Replace empty endpoints with both node IPs
config = config.replace("endpoints: []", "endpoints:\n            - 192.168.1.244\n            - 192.168.1.10")

print("Modified talosconfig:")
print(config)
print("---")

# Upload via SFTP
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASS, timeout=10,
               look_for_keys=False, allow_agent=False)

# Create .talos directory
stdin, stdout, stderr = client.exec_command("mkdir -p /root/.talos")
stdout.channel.recv_exit_status()

sftp = client.open_sftp()
with sftp.open("/root/.talos/config", "w") as f:
    f.write(config)
sftp.close()

# Verify
stdin, stdout, stderr = client.exec_command("cat /root/.talos/config")
print("Uploaded config:")
print(stdout.read().decode())
client.close()
print("Done!")
