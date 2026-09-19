#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Windows-only offline proof; requires elevated x64 MSVC shell and active firewall.

Temporarily block outbound traffic only for a fresh C test executable. Verify a
reachable TCP endpoint before, during, and after the rule; run inference with
the rule active. Never alter firewall profiles, SSH rules, or other programs.
"""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
C_SOURCE = r'''
#include <winsock2.h>
#include <ws2tcpip.h>
#define main inference_main
#include "c_smoke.c"
#undef main
int main(int argc, char **argv) {
    if (argc != 4 || strcmp(argv[1], "--probe") != 0)
        return inference_main(argc, argv);
    WSADATA data;
    if (WSAStartup(MAKEWORD(2, 2), &data) != 0) return 3;
    SOCKET sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (sock == INVALID_SOCKET) { WSACleanup(); return 3; }
    struct sockaddr_in address = {0};
    address.sin_family = AF_INET;
    address.sin_port = htons((u_short)atoi(argv[3]));
    if (InetPtonA(AF_INET, argv[2], &address.sin_addr) != 1) return 3;
    u_long mode = 1;
    if (ioctlsocket(sock, FIONBIO, &mode) != 0) return 3;
    int error = 0;
    if (connect(sock, (const struct sockaddr *)&address, (int)sizeof(address)) != 0) {
        error = WSAGetLastError();
        if (error == WSAEWOULDBLOCK) {
            fd_set writable, failed;
            FD_ZERO(&writable); FD_SET(sock, &writable);
            FD_ZERO(&failed); FD_SET(sock, &failed);
            struct timeval timeout = {5, 0};
            int ready = select(0, NULL, &writable, &failed, &timeout);
            int bytes = (int)sizeof(error);
            if (ready == 0) error = WSAETIMEDOUT;
            else if (ready < 0) error = WSAGetLastError();
            else if (getsockopt(sock, SOL_SOCKET, SO_ERROR, (char *)&error, &bytes) != 0)
                error = WSAGetLastError();
        }
    }
    printf("connect_error=%d\n", error);
    closesocket(sock); WSACleanup();
    return error == 0 ? 0 : 4;
}
'''


def quoted(value):
    return "'" + str(value).replace("'", "''") + "'"


def powershell(command):
    executable = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    return subprocess.run([str(executable), '-NoProfile', '-NonInteractive', '-Command',
                           "$ErrorActionPreference='Stop'; " + command],
                          text=True, capture_output=True, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--probe-host', default='172.30.0.1')
    parser.add_argument('--probe-port', type=int, default=445)
    args = parser.parse_args()
    if platform.system() != 'Windows':
        raise SystemExit('This check requires Windows.')
    ipaddress.IPv4Address(args.probe_host)
    if not 1 <= args.probe_port <= 65535:
        raise SystemExit('Invalid probe port.')
    result = {'status': 'failed', 'network_denial_verified': False,
              'probe_endpoint': f'{args.probe_host}:{args.probe_port}'}
    try:
        with tempfile.TemporaryDirectory(prefix='decisiongate-offline-') as directory:
            temporary = Path(directory)
            bundle = temporary / 'bundle'
            shutil.copytree(args.bundle.resolve(), bundle)
            source, executable = temporary / 'host.c', bundle / 'offline-host.exe'
            source.write_text(C_SOURCE, encoding="utf-8")
            subprocess.run(['cl.exe', '/nologo', '/W4', '/WX', str(source),
                            '/I' + str(bundle), '/I' + str(ROOT / 'examples'),
                            '/Fe:' + str(executable), '/Fo:' + str(temporary / 'host.obj'),
                            '/link', str(bundle / 'decisiongate.lib'), 'ws2_32.lib'], check=True)
            windows = Path(os.environ['SystemRoot'])
            environment = {'SystemRoot': str(windows), 'WINDIR': str(windows),
                           'PATH': str(windows / 'System32'), 'TEMP': directory, 'TMP': directory}
            work = temporary / 'empty-cwd'
            work.mkdir()

            def run(*arguments):
                return subprocess.run([str(executable), *arguments], cwd=work,
                                      env=environment, text=True, capture_output=True, timeout=120)

            probe = ('--probe', args.probe_host, str(args.probe_port))
            before = run(*probe)
            result['before'] = {'exit_code': before.returncode, 'stdout': before.stdout.strip()}
            if before.returncode != 0:
                raise RuntimeError('Baseline TCP connection failed; no firewall rule was added.')
            rule = 'DecisionGate-offline-test-' + uuid.uuid4().hex
            # Always remove our exact rule, even if rule creation partly succeeds.
            try:
                powershell(f'New-NetFirewallRule -Name {quoted(rule)} -DisplayName {quoted(rule)} '
                           f'-Direction Outbound -Action Block -Program {quoted(executable)} '
                           '-Profile Any -Enabled True | Out-Null')
                blocked = run(*probe)
                result['blocked'] = {'exit_code': blocked.returncode, 'stdout': blocked.stdout.strip()}
                if blocked.returncode != 4 or blocked.stdout.strip() not in ('connect_error=10013', 'connect_error=10060'):
                    raise RuntimeError('TCP denial was not verified; refusal/crash is not proof.')
                inference = run()
                result['inference'] = {'exit_code': inference.returncode, 'stdout': inference.stdout.strip()}
                if inference.returncode != 0 or not inference.stdout.startswith('p_yes='):
                    raise RuntimeError('Inference failed while the outbound rule was active.')
            finally:
                powershell(f'Get-NetFirewallRule -Name {quoted(rule)} -ErrorAction SilentlyContinue '
                           '| Remove-NetFirewallRule')
                result['rule_removed'] = True
            after = run(*probe)
            result['after'] = {'exit_code': after.returncode, 'stdout': after.stdout.strip()}
            if after.returncode != 0:
                raise RuntimeError('TCP endpoint did not recover after rule removal; result is inconclusive.')
            result.update(status='passed', network_denial_verified=True,
                          scope='Outbound block for the temporary C executable only')
    except Exception as error:
        result['error'] = str(error)
        raise
    finally:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
