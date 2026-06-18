#!/usr/bin/env python3
"""Preflight checks for rule-resolve workflows."""

from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
import zipfile
from typing import Any


DEFAULT_HOST = "192.168.10.89"
DEFAULT_API_BASES = (
    "http://192.168.10.89",
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


def post_json(base: str, path: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    url = f"{base.rstrip('/')}{path}"
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return {
                "ok": 200 <= resp.status < 300,
                "url": url,
                "status": resp.status,
                "json": json.loads(raw) if raw else None,
            }
    except urllib.error.HTTPError as exc:
        raw = exc.read(1000).decode("utf-8", errors="replace")
        return {"ok": False, "url": url, "status": exc.code, "error": str(exc), "body": raw}
    except Exception as exc:
        return {"ok": False, "url": url, "error": str(exc)}


def delete_json(base: str, path: str, timeout: float) -> dict[str, Any]:
    url = f"{base.rstrip('/')}{path}"
    req = urllib.request.Request(url, method="DELETE")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return {
                "ok": 200 <= resp.status < 300,
                "url": url,
                "status": resp.status,
                "json": json.loads(raw) if raw else None,
            }
    except urllib.error.HTTPError as exc:
        raw = exc.read(1000).decode("utf-8", errors="replace")
        return {"ok": False, "url": url, "status": exc.code, "error": str(exc), "body": raw}
    except Exception as exc:
        return {"ok": False, "url": url, "error": str(exc)}


def minimal_xlsx_bytes() -> bytes:
    """Build a tiny valid XLSX in-memory for platform smoke tests."""
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>""",
        )
        zf.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""",
        )
        zf.writestr(
            "xl/workbook.xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
          xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="Smoke" sheetId="1" r:id="rId1"/></sheets>
</workbook>""",
        )
        zf.writestr(
            "xl/_rels/workbook.xml.rels",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>""",
        )
        zf.writestr(
            "xl/worksheets/sheet1.xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    <row r="1"><c r="A1" t="inlineStr"><is><t>cn_name</t></is></c></row>
    <row r="2"><c r="A2" t="inlineStr"><is><t>测试</t></is></c></row>
  </sheetData>
</worksheet>""",
        )
    return out.getvalue()


def multipart_create_project(base: str, project_name: str, timeout: float) -> dict[str, Any]:
    boundary = f"----rule-resolve-{uuid.uuid4().hex}"
    fields = {
        "name": project_name,
        "target_lang": "EN",
        "source_type": "xlsx",
        "workflow": "translate",
        "source_col": "0",
    }
    chunks: list[bytes] = []
    for key, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"),
                str(value).encode("utf-8"),
                b"\r\n",
            ]
        )
    chunks.extend(
        [
            f"--{boundary}\r\n".encode("utf-8"),
            b'Content-Disposition: form-data; name="file"; filename="rule-resolve-smoke.xlsx"\r\n',
            b"Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n",
            minimal_xlsx_bytes(),
            b"\r\n",
            f"--{boundary}--\r\n".encode("utf-8"),
        ]
    )
    body = b"".join(chunks)
    url = f"{base.rstrip('/')}/api/project/"
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "Content-Length": str(len(body))},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return {
                "ok": 200 <= resp.status < 300,
                "url": url,
                "status": resp.status,
                "json": json.loads(raw) if raw else None,
            }
    except urllib.error.HTTPError as exc:
        raw = exc.read(1000).decode("utf-8", errors="replace")
        return {"ok": False, "url": url, "status": exc.code, "error": str(exc), "body": raw}
    except Exception as exc:
        return {"ok": False, "url": url, "error": str(exc)}


def google_translate_smoke(api_base: str, timeout: float) -> dict[str, Any]:
    """Create, translate, and delete a one-row project to verify provider egress."""
    base = api_base.rstrip("/")
    project_name = f"rule-resolve-smoke-{int(time.time())}-{uuid.uuid4().hex[:8]}"
    project_id = None
    result: dict[str, Any] = {"ok": False, "project_name": project_name}
    create_result = multipart_create_project(base, project_name, timeout)

    try:
        if not create_result.get("ok") or not isinstance(create_result.get("json"), dict):
            result.update({"create": create_result})
            return result

        project_id = create_result["json"].get("id")
        if not project_id:
            result.update({"create": create_result})
            return result

        translate_result = post_json(base, f"/api/translate/{project_id}/translate-all", {}, timeout)
        translated = 0
        errors = []
        if isinstance(translate_result.get("json"), dict):
            translated = int(translate_result["json"].get("translated") or 0)
            errors = translate_result["json"].get("errors") or []
        ok = bool(translate_result.get("ok") and translated > 0 and not errors)
        result.update({
            "ok": ok,
            "project_id": project_id,
            "create_status": create_result.get("status"),
            "translate": translate_result,
        })
        return result
    finally:
        if project_id:
            result["delete"] = delete_json(base, f"/api/project/{project_id}", min(timeout, 10))


def check_translation_readiness(
    api_base: str,
    timeout: float,
    required_dicts: list[str],
    google_smoke: bool = False,
) -> dict[str, Any]:
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

    active_google = bool(active_config and active_config.get("provider") == "google_translate")
    smoke_result = None
    config_ready = bool(model_result.get("ok") and dict_result.get("ok") and google_configs and active_google and not missing_dicts)
    if google_smoke and config_ready:
        smoke_result = google_translate_smoke(base, max(timeout, 30))

    ok = bool(config_ready and (not google_smoke or (smoke_result and smoke_result.get("ok"))))
    return {
        "ok": ok,
        "api_base": base,
        "model_endpoint_ok": bool(model_result.get("ok")),
        "dict_endpoint_ok": bool(dict_result.get("ok")),
        "google_config_available": bool(google_configs),
        "active_google": active_google,
        "active_provider": active_config.get("provider") if active_config else "",
        "required_dicts": required_dicts,
        "missing_dicts": missing_dicts,
        "google_smoke_required": google_smoke,
        "google_smoke_ok": bool(smoke_result and smoke_result.get("ok")) if google_smoke else None,
        "google_smoke_check": smoke_result,
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
        "--google-smoke",
        action="store_true",
        help="For Google Translate workflows, create/delete a one-row temporary project to verify real provider connectivity.",
    )
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
        check_translation_readiness(item["api_base"], args.api_timeout, args.required_dict, args.google_smoke)
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
