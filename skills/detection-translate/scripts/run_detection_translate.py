#!/usr/bin/env python3
import argparse
import json
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import requests
from openpyxl import load_workbook


DEFAULT_REPO_ROOT = Path.home() / "Documents/翻译软件"
DEFAULT_API_BASE = "http://192.168.10.89"
DEFAULT_TRANSLATION_DICTS = ["专业名称翻译", "software翻译"]
DEFAULT_REPLACEMENT_DICTS = ["基础字符校对", "detection校对"]
DEFAULT_SOURCE_HEADERS = ["name.1", "desc", "notes"]
CN_RE = re.compile(r"[\u4e00-\u9fff]")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create and run a detection translation project through AI Translation Studio."
    )
    parser.add_argument("--input", required=True, help="Source detection workbook (.xlsx)")
    parser.add_argument("--project-name", help="Platform project name. Defaults to the workbook stem.")
    parser.add_argument("--output", help="Exported bilingual workbook path.")
    parser.add_argument("--report", help="JSON summary report path.")
    parser.add_argument("--api-base", default=DEFAULT_API_BASE, help="AI Translation Studio backend URL.")
    parser.add_argument("--repo-root", default=str(DEFAULT_REPO_ROOT), help="Repo root path.")
    parser.add_argument(
        "--source-headers",
        nargs="+",
        default=DEFAULT_SOURCE_HEADERS,
        help="Workbook headers to translate. Defaults to detection fields.",
    )
    parser.add_argument(
        "--translation-dicts",
        nargs="+",
        default=DEFAULT_TRANSLATION_DICTS,
        help="Translation dictionary names.",
    )
    parser.add_argument(
        "--replacement-dicts",
        nargs="+",
        default=DEFAULT_REPLACEMENT_DICTS,
        help="Replacement dictionary names.",
    )
    parser.add_argument("--skip-export", action="store_true", help="Skip bilingual Excel export.")
    parser.add_argument(
        "--keep-failed-project",
        action="store_true",
        help="Keep the platform project if translation fails before replacement/export.",
    )
    parser.add_argument(
        "--activate-google",
        action="store_true",
        help="Explicitly activate the Google Translate config. This changes platform-global model settings.",
    )
    parser.add_argument(
        "--manual-review-limit",
        type=int,
        default=15,
        help="Number of warnings to keep in the report.",
    )
    return parser.parse_args()


def ensure_ok(resp, context):
    try:
        resp.raise_for_status()
    except Exception as exc:
        body = resp.text[:1000] if resp is not None else ""
        raise RuntimeError(f"{context} failed: {exc}\n{body}") from exc
    return resp


def perform_request(session, method, url, context, **kwargs):
    try:
        resp = session.request(method, url, **kwargs)
    except requests.RequestException as exc:
        raise RuntimeError(
            f"{context} failed: could not reach {url}. Confirm the AI Translation Studio API base URL first."
        ) from exc
    return ensure_ok(resp, context)


def sanitize_project_name(name):
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", name.strip())
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
    return cleaned or "detection-translate"


def detect_source_columns(xlsx_path, headers_needed):
    wb = load_workbook(xlsx_path, read_only=True, data_only=True)
    found = {header: set() for header in headers_needed}
    sheets = {}

    for ws in wb.worksheets:
        first_row = next(ws.iter_rows(min_row=1, max_row=1), None)
        headers = []
        if first_row:
            for cell in first_row:
                headers.append(str(cell.value).strip() if cell.value is not None else "")
        sheets[ws.title] = headers
        for idx, header in enumerate(headers):
            if header in found:
                found[header].add(idx)

    wb.close()

    missing = [header for header, indexes in found.items() if not indexes]
    if missing:
        raise RuntimeError(f"Missing required headers: {', '.join(missing)}")

    result = []
    for header in headers_needed:
        indexes = sorted(found[header])
        if len(indexes) != 1:
            raise RuntimeError(
                f"Header '{header}' appears in multiple different columns: {indexes}. "
                "Pass a workbook with stable detection columns."
            )
        result.append(indexes[0])

    return result, sheets


def get_json(session, url, context):
    resp = perform_request(session, "GET", url, context, timeout=60)
    return resp.json()


def post_json(session, url, payload, context):
    resp = perform_request(session, "POST", url, context, json=payload, timeout=300)
    return resp.json()


def put_json(session, url, payload, context):
    resp = perform_request(session, "PUT", url, context, json=payload, timeout=120)
    return resp.json()


def delete_project(session, api_base, project_id):
    try:
        perform_request(
            session,
            "DELETE",
            f"{api_base}/api/project/{project_id}",
            "Delete failed project",
            timeout=60,
        )
        return True
    except Exception:
        return False


def count_project_chunks(project):
    chunks = project.get("chunks")
    if isinstance(chunks, list):
        return len(chunks)
    try:
        return int(project.get("chunk_count") or 0)
    except (TypeError, ValueError):
        return 0


def ensure_translation_completed(result, expected_count, context):
    errors = result.get("errors") or []
    translated = int(result.get("translated") or 0)
    if expected_count <= 0:
        raise RuntimeError(f"{context} did not create any chunks. Check source headers/source_col before translating.")
    if errors or translated < expected_count:
        error_preview = json.dumps(errors[:5], ensure_ascii=False) if isinstance(errors, list) else str(errors)
        raise RuntimeError(
            f"{context} incomplete: translated {translated}/{expected_count}; errors={error_preview}. "
            "Stop here and check AI Translation Studio / Google Translate server configuration before replacement/export."
        )


def resolve_google_translate_config(session, api_base, activate=False):
    settings = get_json(session, f"{api_base}/api/settings/model", "Fetch model configs")
    configs = settings.get("configs", [])
    google_configs = [cfg for cfg in configs if cfg.get("provider") == "google_translate"]
    if not google_configs:
        raise RuntimeError("No Google Translate model config found. Configure one first in the platform.")

    active_id = settings.get("active_id")
    active = next((cfg for cfg in configs if cfg.get("id") == active_id), None)
    if active and active.get("provider") == "google_translate":
        return active

    selected = google_configs[0]
    if not activate:
        active_desc = f"{active.get('name')} ({active.get('provider')})" if active else "none"
        raise RuntimeError(
            "Active platform model is not Google Translate "
            f"(current: {active_desc}). Refusing to change global model settings silently. "
            "Activate Google Translate in the platform first, or rerun with --activate-google after user confirmation."
        )

    post_json(
        session,
        f"{api_base}/api/settings/model/{selected['id']}/activate",
        {},
        "Activate Google Translate config",
    )
    return selected


def resolve_dictionary_ids(session, api_base, names):
    dictionaries = get_json(session, f"{api_base}/api/dict/", "Fetch dictionaries")
    by_name = {item["name"]: item["id"] for item in dictionaries}
    missing = [name for name in names if name not in by_name]
    if missing:
        raise RuntimeError(f"Missing dictionaries: {', '.join(missing)}")
    return [by_name[name] for name in names]


def create_project(session, api_base, input_path, project_name, source_cols, translation_ids, replacement_ids):
    data = {
        "name": project_name,
        "target_lang": "EN",
        "source_type": "xlsx",
        "workflow": "translate",
        "translation_dict_ids": ",".join(str(i) for i in translation_ids),
        "replacement_dict_ids": ",".join(str(i) for i in replacement_ids),
        "source_col": ",".join(str(i) for i in source_cols),
    }
    with input_path.open("rb") as f:
        files = {
            "file": (
                input_path.name,
                f,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        }
        resp = perform_request(
            session,
            "POST",
            f"{api_base}/api/project/",
            "Create project",
            data=data,
            files=files,
            timeout=300,
        )
    return resp.json()


def backup_database(repo_root, project_name):
    db_path = repo_root / "backend/instance/translator.db"
    if not db_path.exists():
        raise RuntimeError(f"Translator DB not found: {db_path}")
    backup_dir = repo_root / "output/env-backup"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    backup_path = backup_dir / f"translator_before_{project_name}_detection_translate_{stamp}.db"
    shutil.copy2(db_path, backup_path)
    return backup_path


def run_detection_proofread(repo_root, project_id):
    proofread_py = repo_root / "backend/venv/bin/python"
    proofread_script = repo_root / "tools/detection/check_and_fix.py"
    if not proofread_py.exists():
        raise RuntimeError(f"Backend venv Python not found: {proofread_py}")

    repair = subprocess.run(
        [str(proofread_py), str(proofread_script), str(project_id), "--repair"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    verify = subprocess.run(
        [str(proofread_py), str(proofread_script), str(project_id)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    return {
        "repair_stdout": repair.stdout,
        "verify_stdout": verify.stdout,
        "verify_clean": "没有发现任何问题" in verify.stdout,
    }


def audit_project(project, manual_review_limit):
    warnings = []
    rows = defaultdict(dict)

    for chunk in project.get("chunks", []):
        fmt = chunk.get("format_data")
        if not fmt:
            continue
        try:
            meta = json.loads(fmt)
        except Exception:
            continue
        row = meta.get("row")
        header = meta.get("header")
        if row and header:
            rows[row][header] = chunk.get("translated_text", "")

    for row, cells in sorted(rows.items()):
        for header in ("name.1", "desc", "notes"):
            text = cells.get(header, "")
            if not text:
                continue
            if CN_RE.search(text):
                warnings.append({"row": row, "header": header, "issue": "contains_chinese", "text": text})
            if re.search(r",(?=[A-Za-z/])", text):
                warnings.append({"row": row, "header": header, "issue": "comma_spacing", "text": text})
            if re.search(r",,|\.\.(?!/)", text):
                warnings.append({"row": row, "header": header, "issue": "double_punctuation", "text": text})
            if header == "name.1" and re.search(r"\bvulnerability\b", text):
                warnings.append({"row": row, "header": header, "issue": "lowercase_vulnerability", "text": text})

    return warnings[:manual_review_limit]


def export_bilingual(session, api_base, project_id, output_path):
    resp = perform_request(
        session,
        "GET",
        f"{api_base}/api/export/{project_id}?format=xlsx&bilingual=true",
        "Export bilingual workbook",
        timeout=600,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(resp.content)


def main():
    args = parse_args()
    repo_root = Path(args.repo_root).expanduser().resolve()
    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    project_name = sanitize_project_name(args.project_name or input_path.stem)
    output_path = (
        Path(args.output).expanduser().resolve()
        if args.output
        else input_path.with_name(f"{input_path.stem}_translated.xlsx")
    )
    report_path = (
        Path(args.report).expanduser().resolve()
        if args.report
        else output_path.with_name(f"{output_path.stem}_report.json")
    )

    source_cols, sheet_headers = detect_source_columns(input_path, args.source_headers)

    session = requests.Session()
    health = get_json(session, f"{args.api_base}/api/health", "Check backend health")
    if health.get("status") != "ok":
        raise RuntimeError(f"Backend is not healthy: {health}")

    google_cfg = resolve_google_translate_config(session, args.api_base, activate=args.activate_google)
    translation_ids = resolve_dictionary_ids(session, args.api_base, args.translation_dicts)
    replacement_ids = resolve_dictionary_ids(session, args.api_base, args.replacement_dicts)

    created = create_project(
        session,
        args.api_base,
        input_path,
        project_name,
        source_cols,
        translation_ids,
        replacement_ids,
    )
    project_id = created["id"]
    initial_project = get_json(session, f"{args.api_base}/api/project/{project_id}", "Fetch created project")
    expected_chunks = count_project_chunks(initial_project)

    try:
        translate_result = post_json(
            session,
            f"{args.api_base}/api/translate/{project_id}/translate-all",
            {},
            "Translate all chunks",
        )
        ensure_translation_completed(translate_result, expected_chunks, "Translate all chunks")
    except Exception:
        if not args.keep_failed_project:
            delete_project(session, args.api_base, project_id)
        raise
    replace_result = post_json(
        session,
        f"{args.api_base}/api/proofread/{project_id}/batch-replace-all",
        {},
        "Run batch replacement",
    )

    backup_path = backup_database(repo_root, project_name)
    proofread_result = run_detection_proofread(repo_root, project_id)
    put_json(
        session,
        f"{args.api_base}/api/project/{project_id}/status",
        {"status": "done"},
        "Set project status",
    )

    project = get_json(session, f"{args.api_base}/api/project/{project_id}", "Fetch final project")
    warnings = audit_project(project, args.manual_review_limit)

    if not args.skip_export:
        export_bilingual(session, args.api_base, project_id, output_path)

    report = {
        "project_id": project_id,
        "project_name": project_name,
        "input": str(input_path),
        "output": None if args.skip_export else str(output_path),
        "repo_root": str(repo_root),
        "api_base": args.api_base,
        "google_config": {
            "id": google_cfg.get("id"),
            "name": google_cfg.get("name"),
            "provider": google_cfg.get("provider"),
            "model_name": google_cfg.get("model_name"),
        },
        "translation_dicts": list(zip(args.translation_dicts, translation_ids)),
        "replacement_dicts": list(zip(args.replacement_dicts, replacement_ids)),
        "source_headers": args.source_headers,
        "source_cols": source_cols,
        "sheet_headers": sheet_headers,
        "chunk_count": project.get("chunk_count"),
        "translate_result": {
            "translated": translate_result.get("translated"),
            "errors": translate_result.get("errors", []),
        },
        "replace_result": replace_result,
        "backup": str(backup_path),
        "proofread": {
            "verify_clean": proofread_result["verify_clean"],
            "repair_stdout_tail": proofread_result["repair_stdout"][-4000:],
            "verify_stdout": proofread_result["verify_stdout"],
        },
        "manual_review_warnings": warnings,
        "status": project.get("status"),
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))

    print(json.dumps({
        "project_id": project_id,
        "project_name": project_name,
        "output": None if args.skip_export else str(output_path),
        "report": str(report_path),
        "warnings": len(warnings),
        "verify_clean": proofread_result["verify_clean"],
    }, ensure_ascii=False, indent=2))

    if not proofread_result["verify_clean"]:
        raise SystemExit("Detection proofreading did not return a clean result.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
