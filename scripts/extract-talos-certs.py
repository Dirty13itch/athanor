"""Extract certs from talosconfig and upload to VAULT, then test TLS with openssl."""
import base64
import paramiko

HOST = "192.168.1.203"
USER = "root"
PASS = "Hockey1298"

# Certs from the kaizen talosconfig (base64-encoded PEM)
CA = "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUJQekNCOHFBREFnRUNBaEVBb1NNTklpdHRrdFVlTkw1RzBmU3VqekFGQmdNclpYQXdFREVPTUF3R0ExVUUKQ2hNRmRHRnNiM013SGhjTk1qWXdNakV6TWpJeU9ERXpXaGNOTXpZd01qRXhNakl5T0RFeldqQVFNUTR3REFZRApWUVFLRXdWMFlXeHZjekFxTUFVR0F5dGxjQU1oQUZzcXlWVjBuUmFRUGliYWlQVUdTMlZKRk1oZmJRczVmYkhWCmExajJpRU4rbzJFd1h6QU9CZ05WSFE4QkFmOEVCQU1DQW9Rd0hRWURWUjBsQkJZd0ZBWUlLd1lCQlFVSEF3RUcKQ0NzR0FRVUZCd01DTUE4R0ExVWRFd0VCL3dRRk1BTUJBZjh3SFFZRFZSME9CQllFRkdpb1IyUHN5TTAxZngzaApacUJST3lSNkJSWEpNQVVHQXl0bGNBTkJBRGtmUmQzNU4wSTc1YTFJMWt4UXd0ZGxEaDBsTFJkZ2IyR29ZenhuCittd3lGaFROZnk1UmVaK0JDejl3MmpKM2xzOHZ0Q2pvQ1pRMUFzY2NGekMvM0FnPQotLS0tLUVORCBDRVJUSUZJQ0FURS0tLS0tCg=="
CRT = "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUJLRENCMjZBREFnRUNBaEEwMngvV3l4NWZrazdaUmhLYjZMWTJNQVVHQXl0bGNEQVFNUTR3REFZRFZRUUsKRXdWMFlXeHZjekFlRncweU5qQXlNVE15TWpJNE1UTmFGdzB5TnpBeU1UTXlNakk0TVROYU1CTXhFVEFQQmdOVgpCQW9UQ0c5ek9tRmtiV2x1TUNvd0JRWURLMlZ3QXlFQSt6MUtjMUJsck9xSUFEbXExeDVvZEhDcmk4R1NUTmJHClZLU0FpaG52R2JxalNEQkdNQTRHQTFVZER3RUIvd1FFQXdJSGdEQVRCZ05WSFNVRUREQUtCZ2dyQmdFRkJRY0QKQWpBZkJnTlZIU01FR0RBV2dCUm9xRWRqN01qTk5YOGQ0V2FnVVRza2VnVVZ5VEFGQmdNclpYQURRUUNkSlUrMwpTYnBzYk50cXllS3F0T0hEZkxFcmlnbXh6L2U3V0dNMnN0RVJtU0NtbHJURnhrSU50NnpuQ0VCMVBNazVVcllKCi9sVCtLTk9yQ1NDL0Q0a0EKLS0tLS1FTkQgQ0VSVElGSUNBVEUtLS0tLQo="
KEY = "LS0tLS1CRUdJTiBFRDI1NTE5IFBSSVZBVEUgS0VZLS0tLS0KTUM0Q0FRQXdCUVlESzJWd0JDSUVJRTJLUTZtdkIyd1lYWnIwWWxSUmloT0lIeVJSS0F0MHgrREFVNnFlMTJkWQotLS0tLUVORCBFRDI1NTE5IFBSSVZBVEUgS0VZLS0tLS0K"

ca_pem = base64.b64decode(CA).decode()
crt_pem = base64.b64decode(CRT).decode()
key_pem = base64.b64decode(KEY).decode()

print("CA cert:")
print(ca_pem[:80] + "...")
print("Client cert:")
print(crt_pem[:80] + "...")
print("Client key:")
print(key_pem[:80] + "...")

# Upload to VAULT
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASS, timeout=10,
               look_for_keys=False, allow_agent=False)

client.exec_command("mkdir -p /root/.talos/certs")
import time; time.sleep(0.5)

sftp = client.open_sftp()
with sftp.open("/root/.talos/certs/ca.pem", "w") as f:
    f.write(ca_pem)
with sftp.open("/root/.talos/certs/client.pem", "w") as f:
    f.write(crt_pem)
with sftp.open("/root/.talos/certs/client-key.pem", "w") as f:
    f.write(key_pem)
sftp.close()
print("\nCerts uploaded to VAULT:/root/.talos/certs/")

# Test with openssl
stdin, stdout, stderr = client.exec_command(
    "echo | openssl s_client -connect 10.10.10.10:50000 "
    "-cert /root/.talos/certs/client.pem "
    "-key /root/.talos/certs/client-key.pem "
    "-CAfile /root/.talos/certs/ca.pem "
    "-brief 2>&1 | head -20",
    timeout=10
)
result = stdout.read().decode() + stderr.read().decode()
print("\nOpenSSL test:")
print(result)
client.close()
