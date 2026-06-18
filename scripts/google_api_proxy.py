#!/usr/bin/env python3
"""Local Google API CONNECT proxy and remote AI Translation backend helper.

This helper is intentionally narrow: it proxies HTTPS CONNECT only for Google
API hosts needed by Google Translate, then can restart a remote AI Translation
backend with HTTP_PROXY/HTTPS_PROXY pointed at the local proxy.
"""

import argparse
import ipaddress
import os
import re
import select
import shlex
import socket
import socketserver
import subprocess
import sys
import threading
from datetime import datetime


DEFAULT_ALLOWED_SUFFIXES = (
    ".googleapis.com",
    ".google.com",
    "translation.googleapis.com",
    "oauth2.googleapis.com",
    "accounts.google.com",
)


def connect_upstream(host, port, timeout=5):
    errors = []
    infos = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
    for family, socktype, proto, _, sockaddr in infos:
        sock = socket.socket(family, socktype, proto)
        sock.settimeout(timeout)
        try:
            sock.connect(sockaddr)
            sock.settimeout(None)
            return sock
        except OSError as exc:
            errors.append(f"{sockaddr}: {exc}")
            sock.close()
    raise OSError("; ".join(errors) or f"could not connect to {host}:{port}")


def get_lan_ip(remote_hint="192.168.10.89"):
    candidates = get_local_ip_candidates(remote_hint)
    if candidates:
        return candidates[0]

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect((remote_hint, 80))
            return sock.getsockname()[0]
    except OSError:
        hostname = socket.gethostname()
        return socket.gethostbyname(hostname)


def get_local_ip_candidates(remote_hint="192.168.10.89"):
    ips = []

    try:
        output = subprocess.run(["ifconfig"], text=True, capture_output=True, check=False).stdout
        ips.extend(re.findall(r"\binet\s+(\d+\.\d+\.\d+\.\d+)\b", output))
    except OSError:
        pass

    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ips.append(info[4][0])
    except OSError:
        pass

    seen = set()
    unique = []
    for ip in ips:
        if ip in seen or ip.startswith("127."):
            continue
        seen.add(ip)
        unique.append(ip)

    try:
        remote = ipaddress.ip_address(remote_hint)
    except ValueError:
        remote = None

    def score(ip):
        addr = ipaddress.ip_address(ip)
        same_24 = bool(remote and ip.rsplit(".", 1)[0] == remote_hint.rsplit(".", 1)[0])
        same_16 = bool(remote and ip.split(".")[:2] == remote_hint.split(".")[:2])
        return (
            0 if same_24 else 1,
            0 if same_16 else 1,
            0 if addr.is_private else 1,
            ip,
        )

    return sorted(unique, key=score)


def is_allowed_host(host, allowed_suffixes):
    host = host.lower().rstrip(".")
    for suffix in allowed_suffixes:
        suffix = suffix.lower().rstrip(".")
        if suffix.startswith("."):
            if host.endswith(suffix):
                return True
        elif host == suffix:
            return True
    return False


class GoogleConnectProxy(socketserver.BaseRequestHandler):
    allowed_suffixes = DEFAULT_ALLOWED_SUFFIXES

    def handle(self):
        client = self.request
        header_bytes = b""
        while b"\r\n\r\n" not in header_bytes and b"\n\n" not in header_bytes:
            chunk = client.recv(65536)
            if not chunk:
                return
            header_bytes += chunk
            if len(header_bytes) > 262144:
                client.sendall(b"HTTP/1.1 431 Request Header Fields Too Large\r\n\r\n")
                return

        if b"\r\n\r\n" in header_bytes:
            raw_headers, leftover = header_bytes.split(b"\r\n\r\n", 1)
        else:
            raw_headers, leftover = header_bytes.split(b"\n\n", 1)

        lines = raw_headers.decode("iso-8859-1", errors="replace").splitlines()
        if not lines:
            return
        line = lines[0].strip()
        parts = line.split()
        if len(parts) < 3 or parts[0].upper() != "CONNECT":
            client.sendall(b"HTTP/1.1 405 Method Not Allowed\r\n\r\n")
            return

        target = parts[1]
        if ":" not in target:
            client.sendall(b"HTTP/1.1 400 Bad Request\r\n\r\n")
            return
        host, port_text = target.rsplit(":", 1)
        try:
            port = int(port_text)
        except ValueError:
            client.sendall(b"HTTP/1.1 400 Bad Request\r\n\r\n")
            return
        if port != 443 or not is_allowed_host(host, self.allowed_suffixes):
            client.sendall(b"HTTP/1.1 403 Forbidden\r\n\r\n")
            return

        try:
            upstream = connect_upstream(host, port)
        except OSError as exc:
            client.sendall(f"HTTP/1.1 502 Bad Gateway\r\n\r\n{exc}".encode())
            return

        peer = self.client_address[0]
        print(f"[{datetime.now().isoformat(timespec='seconds')}] CONNECT {peer} -> {host}:{port}", flush=True)
        client.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        if leftover:
            upstream.sendall(leftover)
        self._tunnel(client, upstream)

    def _tunnel(self, client, upstream):
        sockets = [client, upstream]
        try:
            while True:
                readable, _, errored = select.select(sockets, [], sockets, 300)
                if errored or not readable:
                    break
                for sock in readable:
                    other = upstream if sock is client else client
                    try:
                        data = sock.recv(65536)
                        if not data:
                            return
                        other.sendall(data)
                    except (ConnectionResetError, BrokenPipeError):
                        return
        finally:
            upstream.close()


class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def serve(args):
    GoogleConnectProxy.allowed_suffixes = tuple(args.allow_suffix)
    bind_ip = args.bind
    if bind_ip not in {"0.0.0.0", "127.0.0.1", "localhost"}:
        try:
            ipaddress.ip_address(bind_ip)
        except ValueError:
            raise SystemExit(f"Invalid bind address: {bind_ip}")

    with ThreadingTCPServer((bind_ip, args.port), GoogleConnectProxy) as server:
        lan_ip = get_lan_ip()
        print(f"Local Google API proxy listening on {bind_ip}:{args.port}", flush=True)
        print(f"Suggested proxy URL for 10.89: http://{lan_ip}:{args.port}", flush=True)
        print("Allowed hosts: " + ", ".join(args.allow_suffix), flush=True)
        server.serve_forever()


def ssh_prefix(ssh_command):
    return shlex.split(ssh_command)


def run_ssh(args, remote_command, check=True):
    cmd = ssh_prefix(args.ssh_command) + [args.remote, remote_command]
    return subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        check=check,
        timeout=getattr(args, "ssh_timeout", 45),
    )


def remote_probe(args):
    command = (
        "set -e; "
        f"export HTTPS_PROXY={shlex.quote(args.proxy_url)} HTTP_PROXY={shlex.quote(args.proxy_url)}; "
        "curl -fsS -I https://translation.googleapis.com/language/translate/v2 | head -5"
    )
    result = run_ssh(args, command)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)


def remote_status(args):
    root = shlex.quote(args.remote_root.rstrip("/"))
    command = (
        f"cd {root}; "
        "echo SYSTEMD; systemctl is-active ai_translator_backend.service 2>/dev/null || true; "
        "echo PIDS; ps aux | grep '/opt/Aitrans/backend/venv/bin/gunicorn' | grep -v grep || true; "
        "echo HEALTH; curl -fsS http://127.0.0.1:5001/api/health || true; "
        "echo ENV; tr '\\0' '\\n' </proc/$(pgrep -f 'backend/app.py' | head -1)/environ 2>/dev/null "
        "| grep -E '^(HTTP_PROXY|HTTPS_PROXY|NO_PROXY)=' || true; "
        "PID=$(lsof -ti:5001 | head -1); "
        "if [ -n \"$PID\" ]; then tr '\\0' '\\n' </proc/$PID/environ | grep -E '^(HTTP_PROXY|HTTPS_PROXY|NO_PROXY)=' || true; fi"
    )
    result = run_ssh(args, command, check=False)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode


def remote_restart(args, with_proxy):
    root = shlex.quote(args.remote_root.rstrip("/"))
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    proxy_exports = ""
    label = "direct"
    if with_proxy:
        proxy_exports = (
            f"export HTTPS_PROXY={shlex.quote(args.proxy_url)} "
            f"HTTP_PROXY={shlex.quote(args.proxy_url)} "
            "NO_PROXY=127.0.0.1,localhost,192.168.10.89; "
        )
        label = "proxy"
    command = (
        "set -e; "
        f"cd {root}; mkdir -p output/env-backup; "
        f"(pgrep -af 'backend/app.py|flask' || true) > output/env-backup/backend_processes_before_{label}_{stamp}.txt; "
        "pkill -f 'backend/app.py' || true; sleep 2; "
        f"cd {root}/backend; {proxy_exports}"
        f"nohup ./venv/bin/python app.py > backend_{label}_{stamp}.log 2>&1 < /dev/null & "
        "sleep 3; "
        "curl -fsS http://127.0.0.1:5002/api/health; "
        "echo; pgrep -af 'backend/app.py|flask' || true"
    )
    result = run_ssh(args, command)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)


def remote_tunnel(args):
    """Open a local SSH reverse tunnel so remote 127.0.0.1:<remote_port>
    forwards to local 127.0.0.1:<local_port>.
    """
    local_match = f"127.0.0.1:{args.remote_port}:127.0.0.1:{args.local_port}"
    subprocess.run(["pkill", "-f", local_match], check=False)

    cmd = (
        ssh_prefix(args.ssh_command)
        + [
            "-f",
            "-N",
            "-o",
            "ExitOnForwardFailure=yes",
            "-R",
            local_match,
            args.remote,
        ]
    )
    result = subprocess.run(cmd, text=True, capture_output=True, check=True, timeout=args.ssh_timeout)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    print(f"Reverse tunnel active: {args.remote} 127.0.0.1:{args.remote_port} -> local 127.0.0.1:{args.local_port}")


def remote_systemd_proxy(args, enable):
    service = shlex.quote(args.systemd_service)
    sudo_password = os.environ.get("SSHPASS", "")
    if not sudo_password:
        raise SystemExit("SSHPASS must be set so sudo can update the remote systemd service override.")

    if enable:
        conf = (
            "[Service]\n"
            f"Environment=\"HTTPS_PROXY={args.proxy_url}\"\n"
            f"Environment=\"HTTP_PROXY={args.proxy_url}\"\n"
            "Environment=\"NO_PROXY=127.0.0.1,localhost,192.168.10.89\"\n"
        )
        conf_q = shlex.quote(conf)
        remote_command = (
            "set -e; "
            f"printf '%s\\n' {shlex.quote(sudo_password)} | sudo -S -p '' mkdir -p /etc/systemd/system/{service}.d; "
            f"printf %s {conf_q} > /tmp/ai_translation_proxy.conf; "
            f"printf '%s\\n' {shlex.quote(sudo_password)} | sudo -S -p '' cp /tmp/ai_translation_proxy.conf /etc/systemd/system/{service}.d/proxy.conf; "
            f"printf '%s\\n' {shlex.quote(sudo_password)} | sudo -S -p '' systemctl daemon-reload; "
            f"printf '%s\\n' {shlex.quote(sudo_password)} | sudo -S -p '' systemctl restart {service}; "
            "sleep 5; "
            f"systemctl is-active {service}; "
            "PID=$(lsof -ti:5001 | head -1); echo PID=$PID; "
            "cat /proc/$PID/environ | tr '\\0' '\\n' | grep -E '^(HTTP_PROXY|HTTPS_PROXY|NO_PROXY)=' || true; "
            "curl -fsS http://127.0.0.1:5001/api/health"
        )
    else:
        remote_command = (
            "set -e; "
            f"printf '%s\\n' {shlex.quote(sudo_password)} | sudo -S -p '' rm -f /etc/systemd/system/{service}.d/proxy.conf; "
            f"printf '%s\\n' {shlex.quote(sudo_password)} | sudo -S -p '' systemctl daemon-reload; "
            f"printf '%s\\n' {shlex.quote(sudo_password)} | sudo -S -p '' systemctl restart {service}; "
            "sleep 5; "
            f"systemctl is-active {service}; "
            "PID=$(lsof -ti:5001 | head -1); echo PID=$PID; "
            "cat /proc/$PID/environ | tr '\\0' '\\n' | grep -E '^(HTTP_PROXY|HTTPS_PROXY|NO_PROXY)=' || true; "
            "curl -fsS http://127.0.0.1:5001/api/health"
        )

    result = run_ssh(args, remote_command)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)


def build_parser():
    parser = argparse.ArgumentParser(description="Google API local proxy helper for AI Translation Studio.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("lan-ip", help="Print the local LAN IP likely reachable from 10.89.")
    p.add_argument("--remote-hint", default="192.168.10.89")
    p.add_argument("--all", action="store_true", help="Print all non-loopback local IPv4 candidates in priority order.")

    p = sub.add_parser("serve", help="Run the local Google API CONNECT proxy.")
    p.add_argument("--bind", default="0.0.0.0")
    p.add_argument("--port", type=int, default=8899)
    p.add_argument("--allow-suffix", action="append", default=list(DEFAULT_ALLOWED_SUFFIXES))

    for name in ("remote-probe", "remote-status", "remote-enable", "remote-disable", "remote-enable-systemd", "remote-disable-systemd"):
        p = sub.add_parser(name, help=f"{name} for the remote AI Translation backend.")
        p.add_argument("--remote", default="dx@192.168.10.89")
        p.add_argument("--remote-root", default="/opt/Aitrans")
        p.add_argument("--ssh-command", default=os.environ.get("AI_TRANSLATION_SSH_COMMAND", "ssh"))
        p.add_argument("--ssh-timeout", type=int, default=45)
        if name in {"remote-probe", "remote-enable", "remote-enable-systemd"}:
            p.add_argument("--proxy-url", required=True)
        if name in {"remote-enable-systemd", "remote-disable-systemd"}:
            p.add_argument("--systemd-service", default="ai_translator_backend.service")

    p = sub.add_parser("remote-tunnel", help="Open SSH reverse tunnel from remote 127.0.0.1 to local proxy.")
    p.add_argument("--remote", default="dx@192.168.10.89")
    p.add_argument("--ssh-command", default=os.environ.get("AI_TRANSLATION_SSH_COMMAND", "ssh"))
    p.add_argument("--ssh-timeout", type=int, default=45)
    p.add_argument("--remote-port", type=int, default=18899)
    p.add_argument("--local-port", type=int, default=8899)

    return parser


def main():
    args = build_parser().parse_args()
    if args.cmd == "lan-ip":
        if args.all:
            print("\n".join(get_local_ip_candidates(args.remote_hint)))
        else:
            print(get_lan_ip(args.remote_hint))
    elif args.cmd == "serve":
        serve(args)
    elif args.cmd == "remote-probe":
        remote_probe(args)
    elif args.cmd == "remote-status":
        raise SystemExit(remote_status(args))
    elif args.cmd == "remote-enable":
        remote_restart(args, with_proxy=True)
    elif args.cmd == "remote-disable":
        remote_restart(args, with_proxy=False)
    elif args.cmd == "remote-tunnel":
        remote_tunnel(args)
    elif args.cmd == "remote-enable-systemd":
        remote_systemd_proxy(args, enable=True)
    elif args.cmd == "remote-disable-systemd":
        remote_systemd_proxy(args, enable=False)


if __name__ == "__main__":
    main()
