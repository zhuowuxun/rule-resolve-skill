#!/usr/bin/env python3
"""Preflight checks for rule-resolve workflows."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from typing import Any


DEFAULT_HOST = "192.168.10.89"
DEFAULT_API_BASES = (
    "http://127.0.0.1:5002",
    "http://192.168.10.89:5002",
)


def ping_host(host: str, timeout_ms: int) -> dict[str, Any]:
    cmd = ["ping", "-c", "1", "-W", str(timeout_ms), host]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=max(2, timeout_ms / 1000 + 1))
    except Exception as exc:  # pragma: no cover - defensive shell boundary
        return {"ok": False, "command": cmd, "error": str(exc)}
    return {
        "ok": proc.returncode == 0,
        "command": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def check_api_base(api_base: str, timeout: float) -> dict[str, Any]:
    base = api_base.rstrip("/")
    url = f"{base}/api/health"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(500).decode("utf-8", errors="replace")
            return {"ok": 200 <= resp.status < 300, "api_base": base, "url": url, "status": resp.status, "body": body}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "api_base": base, "url": url, "status": exc.code, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "api_base": base, "url": url, "error": str(exc)}


def request_json(base: str, path: str, timeout: float) -> dict[str, Any]:
    url = f"{base.rstrip('/')}{path}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return {
                "ok": 200 <= resp.status < 300,
                "url": url,
                "status": resp.status,
                "json": json.loads(body) if body else None,
            }
    except urllib.error.HTTPError as exc:
        return {"ok": False, "url": url, "status": exc.code, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "url": url, "error": str(exc)}


def check_translation_readiness(api_base: str, timeout: float, required_dicts: list[str]) -> dict[str, Any]:
    base = api_base.rstrip("/")
    model_result = request_json(base, "/api/settings/model", timeout)
    dict_result = request_json(base, "/api/dict/", timeout)

    configs = []
    active_id = None
    if model_result.get("ok") and isinstance(model_result.get("json"), dict):
        data = model_result["json"]
        configs = data.get("configs") or []
        active_id = data.get("active_id")

    google_configs = [cfg for cfg in configs if cfg.get("provider") == "google_translate"]
    active_config = next((cfg for cfg in configs if cfg.get("id") == active_id), None)

    dictionaries = dict_result.get("json") if dict_result.get("ok") else []
    dict_names = []
    if isinstance(dictionaries, list):
        dict_names = [str(item.get("name", "")) for item in dictionaries if isinstance(item, dict)]
    missing_dicts = [name for name in required_dicts if name not in dict_names]

    ok = bool(model_result.get("ok") and dict_result.get("ok") and google_configs and not missing_dicts)
    return {
        "ok": ok,
        "api_base": base,
        "model_endpoint_ok": bool(model_result.get("ok")),
        "dict_endpoint_ok": bool(dict_result.get("ok")),
        "google_config_available": bool(google_configs),
        "active_provider": active_config.get("provider") if active_config else "",
        "required_dicts": required_dicts,
        "missing_dicts": missing_dicts,
        "model_check": model_result if not model_result.get("ok") else {"url": model_result.get("url"), "status": model_result.get("status")},
        "dict_check": dict_result if not dict_result.get("ok") else {"url": dict_result.get("url"), "status": dict_result.get("status")},
    }


def candidate_api_bases(explicit: list[str]) -> list[str]:
    values: list[str] = []
    for item in explicit:
        if item and item not in values:
            values.append(item)
    for env_name in ("AI_TRANSLATION_API_BASE", "TRANSLATION_API_BASE"):
        item = os.environ.get(env_name, "").strip()
        if item and item not in values:
            values.append(item)
    for item in DEFAULT_API_BASES:
        if item not in values:
            values.append(item)
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description="Check rule-resolve network and translation-platform readiness.")
    parser.add_argument("--host", default=DEFAULT_HOST, help="10.89 host to verify before rule work.")
    parser.add_argument("--ping-timeout-ms", type=int, default=1000)
    parser.add_argument("--api-base", action="append", default=[], help="AI Translation Studio API base URL; can be repeated.")
    parser.add_argument("--require-translation-api", action="store_true", help="Fail if no AI Translation Studio API responds.")
    parser.add_argument(
        "--required-dict",
        action="append",
        default=[],
        help="Dictionary name that must exist for translation readiness; can be repeated.",
    )
    parser.add_argument("--api-timeout", type=float, default=3.0)
    args = parser.parse_args()

    host_result = ping_host(args.host, args.ping_timeout_ms)
    api_results = [check_api_base(base, args.api_timeout) for base in candidate_api_bases(args.api_base)]
    readiness_results = [
        check_translation_readiness(item["api_base"], args.api_timeout, args.required_dict)
        if item.get("ok") else None
        for item in api_results
    ]
    ready_api = next((item for item in readiness_results if item and item.get("ok")), None)
    reachable_api = next((item for item in api_results if item.get("ok")), None)

    result = {
        "host": args.host,
        "host_reachable": bool(host_result.get("ok")),
        "host_check": host_result,
        "translation_api_required": args.require_translation_api,
        "translation_api_reachable": bool(reachable_api),
        "translation_api_ready": bool(ready_api),
        "translation_api_base": ready_api.get("api_base") if ready_api else (reachable_api.get("api_base") if reachable_api else ""),
        "api_checks": api_results,
        "translation_readiness_checks": [item for item in readiness_results if item],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if not result["host_reachable"]:
        return 10
    if args.require_translation_api and not result["translation_api_ready"]:
        return 20
    return 0


if __name__ == "__main__":
    sys.exit(main())
