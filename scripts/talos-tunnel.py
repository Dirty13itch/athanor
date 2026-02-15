"""Create SSH tunnel through VAULT to Node 2 Talos API and query hardware info."""
import base64
import os
import ssl
import tempfile
import threading
import time

import paramiko
import grpc

# Connection details
VAULT_HOST = "192.168.1.203"
VAULT_USER = "root"
VAULT_PASS = "Hockey1298"
NODE2_IP = "10.10.10.10"
NODE2_PORT = 50000
LOCAL_PORT = 50099

# Certs from talosconfig
CA_B64 = "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUJQekNCOHFBREFnRUNBaEVBb1NNTklpdHRrdFVlTkw1RzBmU3VqekFGQmdNclpYQXdFREVPTUF3R0ExVUUKQ2hNRmRHRnNiM013SGhjTk1qWXdNakV6TWpJeU9ERXpXaGNOTXpZd01qRXhNakl5T0RFeldqQVFNUTR3REFZRApWUVFLRXdWMFlXeHZjekFxTUFVR0F5dGxjQU1oQUZzcXlWVjBuUmFRUGliYWlQVUdTMlZKRk1oZmJRczVmYkhWCmExajJpRU4rbzJFd1h6QU9CZ05WSFE4QkFmOEVCQU1DQW9Rd0hRWURWUjBsQkJZd0ZBWUlLd1lCQlFVSEF3RUcKQ0NzR0FRVUZCd01DTUE4R0ExVWRFd0VCL3dRRk1BTUJBZjh3SFFZRFZSME9CQllFRkdpb1IyUHN5TTAxZngzaApacUJST3lSNkJSWEpNQVVHQXl0bGNBTkJBRGtmUmQzNU4wSTc1YTFJMWt4UXd0ZGxEaDBsTFJkZ2IyR29ZenhuCittd3lGaFROZnk1UmVaK0JDejl3MmpKM2xzOHZ0Q2pvQ1pRMUFzY2NGekMvM0FnPQotLS0tLUVORCBDRVJUSUZJQ0FURS0tLS0tCg=="
CRT_B64 = "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUJLRENCMjZBREFnRUNBaEEwMngvV3l4NWZrazdaUmhLYjZMWTJNQVVHQXl0bGNEQVFNUTR3REFZRFZRUUsKRXdWMFlXeHZjekFlRncweU5qQXlNVE15TWpJNE1UTmFGdzB5TnpBeU1UTXlNakk0TVROYU1CTXhFVEFQQmdOVgpCQW9UQ0c5ek9tRmtiV2x1TUNvd0JRWURLMlZ3QXlFQSt6MUtjMUJsck9xSUFEbXExeDVvZEhDcmk4R1NUTmJHClZLU0FpaG52R2JxalNEQkdNQTRHQTFVZER3RUIvd1FFQXdJSGdEQVRCZ05WSFNVRUREQUtCZ2dyQmdFRkJRY0QKQWpBZkJnTlZIU01FR0RBV2dCUm9xRWRqN01qTk5YOGQ0V2FnVVRza2VnVVZ5VEFGQmdNclpYQURRUUNkSlUrMwpTYnBzYk50cXllS3F0T0hEZkxFcmlnbXh6L2U3V0dNMnN0RVJtU0NtbHJURnhrSU50NnpuQ0VCMVBNazVVcllKCi9sVCtLTk9yQ1NDL0Q0a0EKLS0tLS1FTkQgQ0VSVElGSUNBVEUtLS0tLQo="
KEY_B64 = "LS0tLS1CRUdJTiBFRDI1NTE5IFBSSVZBVEUgS0VZLS0tLS0KTUM0Q0FRQXdCUVlESzJWd0JDSUVJRTJLUTZtdkIyd1lYWnIwWWxSUmloT0lIeVJSS0F0MHgrREFVNnFlMTJkWQotLS0tLUVORCBFRDI1NTE5IFBSSVZBVEUgS0VZLS0tLS0K"

def write_temp_pem(data_b64, suffix=".pem"):
    data = base64.b64decode(data_b64)
    f = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, mode='wb')
    f.write(data)
    f.close()
    return f.name

def main():
    # Write certs to temp files
    ca_file = write_temp_pem(CA_B64)
    crt_file = write_temp_pem(CRT_B64)
    key_file = write_temp_pem(KEY_B64)

    print(f"CA: {ca_file}")
    print(f"CRT: {crt_file}")
    print(f"KEY: {key_file}")

    # Set up SSH tunnel
    print(f"\nSetting up SSH tunnel: localhost:{LOCAL_PORT} -> {NODE2_IP}:{NODE2_PORT} via VAULT...")
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(VAULT_HOST, username=VAULT_USER, password=VAULT_PASS,
                       timeout=10, look_for_keys=False, allow_agent=False)

    transport = ssh_client.get_transport()
    # Forward local port to remote destination
    import socket
    import select

    # Create local server socket
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('127.0.0.1', LOCAL_PORT))
    server.listen(1)
    server.settimeout(30)
    print(f"Tunnel listening on 127.0.0.1:{LOCAL_PORT}")

    def tunnel_handler():
        while True:
            try:
                client_sock, addr = server.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            try:
                channel = transport.open_channel('direct-tcpip',
                                                 (NODE2_IP, NODE2_PORT),
                                                 addr)
            except Exception as e:
                print(f"Tunnel channel failed: {e}")
                client_sock.close()
                continue

            # Bidirectional forwarding
            def forward(src, dst):
                try:
                    while True:
                        data = src.recv(4096)
                        if not data:
                            break
                        dst.sendall(data)
                except:
                    pass
                finally:
                    try: src.close()
                    except: pass
                    try: dst.close()
                    except: pass

            t1 = threading.Thread(target=forward, args=(client_sock, channel), daemon=True)
            t2 = threading.Thread(target=forward, args=(channel, client_sock), daemon=True)
            t1.start()
            t2.start()

    tunnel_thread = threading.Thread(target=tunnel_handler, daemon=True)
    tunnel_thread.start()
    time.sleep(1)

    # Now try gRPC connection through tunnel
    print("\nTesting gRPC connection...")
    try:
        ca_pem = base64.b64decode(CA_B64)
        crt_pem = base64.b64decode(CRT_B64)
        key_pem = base64.b64decode(KEY_B64)

        credentials = grpc.ssl_channel_credentials(
            root_certificates=ca_pem,
            private_key=key_pem,
            certificate_chain=crt_pem
        )

        channel = grpc.secure_channel(
            f'127.0.0.1:{LOCAL_PORT}',
            credentials,
            options=[
                ('grpc.ssl_target_name_override', 'talos'),
                ('grpc.default_authority', 'talos'),
            ]
        )

        # Try to connect with a short timeout
        try:
            grpc.channel_ready_future(channel).result(timeout=10)
            print("gRPC channel CONNECTED!")
        except grpc.FutureTimeoutError:
            print("gRPC channel connection timed out")
        except Exception as e:
            print(f"gRPC connection error: {e}")

        channel.close()
    except Exception as e:
        print(f"gRPC setup error: {e}")

    # Cleanup
    server.close()
    ssh_client.close()
    os.unlink(ca_file)
    os.unlink(crt_file)
    os.unlink(key_file)

if __name__ == "__main__":
    main()
