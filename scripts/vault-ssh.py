"""SSH to VAULT via Paramiko first, then native OpenSSH fallbacks."""
import os
import shlex
import shutil
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


def _windows_path_to_wsl_path(raw_path: str) -> Path | None:
    normalized = str(raw_path or "").strip().replace('\\', '/')
    if len(normalized) >= 3 and normalized[1] == ':' and normalized[2] == '/':
        return Path('/mnt') / normalized[0].lower() / normalized[3:]
    return None


def _wsl_path_to_windows_path(path: Path) -> str | None:
    parts = path.parts
    if len(parts) >= 4 and parts[1] == 'mnt' and len(parts[2]) == 1:
        return f"{parts[2].upper()}:\\{'\\'.join(parts[3:])}"
    return None


def _iter_existing_key_paths() -> list[Path]:
    candidates: list[Path] = []

    for value in (
        os.environ.get('ATHANOR_VAULT_KEY_PATH'),
        os.environ.get('VAULT_SSH_KEY_PATH'),
    ):
        if value:
            candidates.append(Path(value).expanduser())
            maybe_wsl = _windows_path_to_wsl_path(value)
            if maybe_wsl is not None:
                candidates.append(maybe_wsl)

    home_ssh = Path.home() / '.ssh'
    candidates.extend([
        home_ssh / 'id_ed25519',
        home_ssh / 'athanor_mgmt',
    ])

    windows_home_candidates: list[Path] = []
    userprofile = os.environ.get('USERPROFILE')
    if userprofile:
        maybe_wsl = _windows_path_to_wsl_path(userprofile)
        if maybe_wsl is not None:
            windows_home_candidates.append(maybe_wsl)
    base_users = Path('/mnt/c/Users')
    if base_users.is_dir():
        for name in (
            os.environ.get('USERNAME'),
            Path.home().name,
            Path.home().name.capitalize(),
            Path.home().name.title(),
        ):
            if name:
                windows_home_candidates.append(base_users / name)

    for home in windows_home_candidates:
        candidates.extend([
            home / '.ssh' / 'id_ed25519',
            home / '.ssh' / 'athanor_mgmt',
        ])

    existing: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = str(candidate)
        if normalized in seen:
            continue
        seen.add(normalized)
        if candidate.exists():
            existing.append(candidate)
    return existing


def _resolve_key_path() -> str:
    for candidate in _iter_existing_key_paths():
        return str(candidate)
    return ''


KEY_PATH = _resolve_key_path()


def _native_ssh_variants(command: str) -> list[tuple[str, str | None]]:
    binaries: list[str] = []
    for candidate in (
        '/mnt/c/Windows/System32/OpenSSH/ssh.exe',
        '/mnt/c/Windows/Sysnative/OpenSSH/ssh.exe',
    ):
        if Path(candidate).exists():
            binaries.append(candidate)
    ssh_bin = shutil.which('ssh')
    if ssh_bin:
        binaries.append(ssh_bin)

    ordered_binaries: list[str] = []
    seen_binaries: set[str] = set()
    for binary in binaries:
        if binary not in seen_binaries:
            ordered_binaries.append(binary)
            seen_binaries.add(binary)

    variants: list[tuple[str, str | None]] = []
    key_paths = _iter_existing_key_paths()
    for binary in ordered_binaries:
        is_windows_ssh = binary.lower().endswith('ssh.exe')
        ordered_key_paths = sorted(
            key_paths,
            key=lambda path: (
                0 if ('/mnt/c/Users/' in str(path) and path.name == 'id_ed25519') else
                1 if ('/mnt/c/Users/' in str(path)) else
                2 if path.name == 'id_ed25519' else
                3,
                str(path),
            ),
        )
        seen_keys: set[str | None] = set()
        for key_path in ordered_key_paths:
            formatted = _wsl_path_to_windows_path(key_path) if is_windows_ssh else str(key_path)
            if formatted and formatted not in seen_keys:
                variants.append((binary, formatted))
                seen_keys.add(formatted)
        variants.append((binary, None))
    return variants


def _native_ssh_run(command: str) -> int:
    last_stderr = ''
    last_stdout = ''
    last_rc = 1
    for binary, key_path in _native_ssh_variants(command):
        if binary.lower().endswith('ssh.exe'):
            ssh_command = [
                binary,
                '-o',
                'BatchMode=yes',
                '-o',
                'ConnectTimeout=10',
            ]
            if key_path:
                ssh_command.extend(['-i', key_path])
        else:
            ssh_command = [
                binary,
                '-o',
                'BatchMode=yes',
                '-o',
                'ConnectTimeout=10',
                '-o',
                'StrictHostKeyChecking=no',
            ]
            if key_path:
                ssh_command.extend(['-i', key_path, '-o', 'IdentitiesOnly=yes'])
        ssh_command.append(f'{USER}@{HOST}')
        ssh_command.append(command)

        if binary.lower().endswith('ssh.exe'):
            shell_command = ' '.join(shlex.quote(part) for part in ssh_command)
            completed = subprocess.run(
                ['/bin/bash', '-lc', shell_command],
                text=True,
                check=False,
            )
        else:
            completed = subprocess.run(
                ssh_command,
                capture_output=True,
                text=True,
                check=False,
            )
        if completed.returncode == 0:
            if not binary.lower().endswith('ssh.exe'):
                if completed.stdout:
                    print(completed.stdout, end='')
                if completed.stderr:
                    print(completed.stderr, end='', file=sys.stderr)
            return 0
        last_rc = completed.returncode or last_rc
        if not binary.lower().endswith('ssh.exe'):
            last_stdout = completed.stdout or last_stdout
            last_stderr = completed.stderr or last_stderr

    if last_stdout:
        print(last_stdout, end='')
    if last_stderr:
        print(last_stderr, end='', file=sys.stderr)
    return last_rc or 1


def run(command):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        connect_kwargs = {
            'hostname': HOST,
            'username': USER,
            'timeout': 10,
            'look_for_keys': not PASSWORD and not KEY_PATH,
            'allow_agent': not PASSWORD and not KEY_PATH,
        }
        if PASSWORD:
            connect_kwargs['password'] = PASSWORD
        if KEY_PATH:
            connect_kwargs['key_filename'] = KEY_PATH

        client.connect(**connect_kwargs)
        stdin, stdout, stderr = client.exec_command(command, timeout=30)
        out = stdout.read().decode('utf-8', errors='replace')
        err = stderr.read().decode('utf-8', errors='replace')
        rc = stdout.channel.recv_exit_status()
        if out:
            print(out, end='')
        if err:
            print(err, end='', file=sys.stderr)
        return rc
    except Exception as e:
        paramiko_error = str(e).strip() or e.__class__.__name__
        native_rc = _native_ssh_run(command)
        if native_rc == 0:
            return 0
        print(f'SSH error: {paramiko_error}', file=sys.stderr)
        return native_rc or 1
    finally:
        client.close()


if __name__ == '__main__':
    cmd = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else 'echo CONNECTED && hostname && uname -a'
    sys.exit(run(cmd))
