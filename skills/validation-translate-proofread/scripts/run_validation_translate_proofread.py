#!/usr/bin/env python3
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import requests
from openpyxl import load_workbook


DEFAULT_REPO_ROOT = Path("/Users/carmenz/Documents/翻译软件")
DEFAULT_API_BASE = "http://127.0.0.1:5002"
DEFAULT_TRANSLATION_DICTS = ["专业名称翻译", "software翻译"]
DEFAULT_MAIN_REPLACEMENT_DICTS = ["基础字符校对", "validation校对"]
DEFAULT_NOTE_REPLACEMENT_DICTS = ["基础字符校对", "validation校对", "validation note replacement"]
DEFAULT_MAIN_SOURCE_HEADERS = ["cn_name", "cn_desc"]
DEFAULT_NOTE_SOURCE_HEADER = "cn_notes"
CN_RE = re.compile(r"[\u4e00-\u9fff]")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create and run a validation translate+proofread project through AI Translation Studio."
    )
    parser.add_argument("--input", required=True, help="Source validation workbook (.xlsx)")
    parser.add_argument("--project-name", help="Platform project name. Defaults to the workbook stem.")
    parser.add_argument("--output", help="Exported bilingual workbook path.")
    parser.add_argument("--report", help="JSON summary report path.")
    parser.add_argument("--api-base", default=DEFAULT_API_BASE, help="AI Translation Studio backend URL.")
    parser.add_argument("--repo-root", default=str(DEFAULT_REPO_ROOT), help="Repo root path.")
    parser.add_argument(
        "--translation-dicts",
        nargs="+",
        default=DEFAULT_TRANSLATION_DICTS,
        help="Validation translation dictionary names.",
    )
    parser.add_argument(
        "--main-replacement-dicts",
        nargs="+",
        default=DEFAULT_MAIN_REPLACEMENT_DICTS,
        help="Replacement dictionaries for the main validation project.",
    )
    parser.add_argument(
        "--note-replacement-dicts",
        nargs="+",
        default=DEFAULT_NOTE_REPLACEMENT_DICTS,
        help="Replacement dictionaries for the notes-only validation project.",
    )
    parser.add_argument("--skip-export", action="store_true", help="Skip bilingual Excel export.")
    parser.add_argument(
        "--manual-review-limit",
        type=int,
        default=20,
        help="Number of QA warnings to keep in the report.",
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
            f"{context} failed: could not reach {url}. Start the local AI Translation Studio backend first."
        ) from exc
    return ensure_ok(resp, context)


def get_json(session, url, context):
    return perform_request(session, "GET", url, context, timeout=120).json()


def post_json(session, url, payload, context):
    return perform_request(session, "POST", url, context, json=payload, timeout=1800).json()


def put_json(session, url, payload, context):
    return perform_request(session, "PUT", url, context, json=payload, timeout=1800).json()


def sanitize_project_name(name):
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", name.strip())
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
    return cleaned or "validation-translate-proofread"


def collect_sheet_headers(xlsx_path):
    wb = load_workbook(xlsx_path, read_only=True, data_only=True)
    sheet_headers = {}
    for ws in wb.worksheets:
        first_row = next(ws.iter_rows(min_row=1, max_row=1), None)
        headers = []
        if first_row:
            for cell in first_row:
                headers.append(str(cell.value).strip() if cell.value is not None else "")
        sheet_headers[ws.title] = headers
    wb.close()
    return sheet_headers


def detect_stable_column(sheet_headers, header_name, limit_sheets=None):
    indexes = set()
    found_sheets = []
    for sheet_name, headers in sheet_headers.items():
        if limit_sheets and sheet_name not in limit_sheets:
            continue
        if header_name in headers:
            indexes.add(headers.index(header_name))
            found_sheets.append(sheet_name)
    if not found_sheets:
        return None, []
    if len(indexes) != 1:
        raise RuntimeError(f"Header '{header_name}' appears in different columns across sheets: {sorted(indexes)}")
    return next(iter(indexes)), found_sheets


def activate_google_translate(session, api_base):
    settings = get_json(session, f"{api_base}/api/settings/model", "Fetch model configs")
    configs = settings.get("configs", [])
    google_configs = [cfg for cfg in configs if cfg.get("provider") == "google_translate"]
    if not google_configs:
        raise RuntimeError("No Google Translate model config found. Configure one first in the platform.")

    active_id = settings.get("active_id")
    active = next((cfg for cfg in configs if cfg.get("id") == active_id), None)
    selected = next((cfg for cfg in google_configs if cfg.get("is_active")), None) or google_configs[0]

    if not active or active.get("provider") != "google_translate" or active.get("id") != selected.get("id"):
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
            timeout=1800,
        )
    return resp.json()


def backup_database(repo_root, project_name):
    db_path = repo_root / "backend/instance/translator.db"
    if not db_path.exists():
        raise RuntimeError(f"Translator DB not found: {db_path}")
    backup_dir = repo_root / "output/env-backup"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    backup_path = backup_dir / f"translator_before_{project_name}_translate_validation_{stamp}.db"
    shutil.copy2(db_path, backup_path)
    return backup_path


def run_validation_proofread(repo_root, project_id):
    proofread_py = repo_root / "backend/venv/bin/python"
    proofread_script = repo_root / "tools/validation/check_and_fix.py"
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


def make_sheet_subset_copy(src, sheets_to_keep):
    wb = load_workbook(src)
    for sheet in list(wb.sheetnames):
        if sheet not in sheets_to_keep:
            wb.remove(wb[sheet])
    tmpdir = Path(tempfile.mkdtemp(prefix="validation_translate_proofread_"))
    dst = tmpdir / f"{src.stem}_subset.xlsx"
    wb.save(dst)
    return dst


def export_bilingual(session, api_base, project_id, output_path):
    resp = perform_request(
        session,
        "GET",
        f"{api_base}/api/export/{project_id}?format=xlsx&bilingual=true",
        "Export bilingual workbook",
        timeout=1800,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(resp.content)


def find_col(ws, header):
    for c_idx in range(1, ws.max_column + 1):
        if str(ws.cell(row=1, column=c_idx).value or "").strip() == header:
            return c_idx
    return None


def merge_note_exports(main_export, note_export, final_output):
    main_wb = load_workbook(main_export)
    note_wb = load_workbook(note_export)
    for sheet_name in note_wb.sheetnames:
        if sheet_name not in main_wb.sheetnames:
            continue
        main_ws = main_wb[sheet_name]
        note_ws = note_wb[sheet_name]
        main_cn = find_col(main_ws, "cn_notes")
        main_en = find_col(main_ws, "en_notes")
        note_cn = find_col(note_ws, "cn_notes")
        note_en = find_col(note_ws, "en_notes")
        if not all([main_cn, main_en, note_cn, note_en]):
            continue
        max_row = min(main_ws.max_row, note_ws.max_row)
        for row_idx in range(2, max_row + 1):
            main_ws.cell(row=row_idx, column=main_cn, value=note_ws.cell(row=row_idx, column=note_cn).value)
            main_ws.cell(row=row_idx, column=main_en, value=note_ws.cell(row=row_idx, column=note_en).value)
    main_wb.save(final_output)


def audit_workbook(path, manual_review_limit):
    wb = load_workbook(path, read_only=True, data_only=True)
    warnings = []
    title_headers = {"en_name", "en_subject", "name_en"}
    rows = defaultdict(dict)

    for ws in wb.worksheets:
        header_row = next(ws.iter_rows(min_row=1, max_row=1), None)
        headers = []
        if header_row:
            headers = [str(cell.value).strip() if cell.value is not None else "" for cell in header_row]
        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            for idx, header in enumerate(headers):
                hk = header.lower()
                if not (hk.startswith("en_") or hk.endswith("_en")):
                    continue
                text = row[idx]
                if text in (None, ""):
                    continue
                rows[(ws.title, row_idx)][hk] = str(text)

    wb.close()

    for (sheet_name, row_num), cells in sorted(rows.items()):
        for header, text in sorted(cells.items()):
            if CN_RE.search(text):
                warnings.append({"sheet": sheet_name, "row": row_num, "header": header, "issue": "contains_chinese", "text": text})
            if re.search(r",(?=[A-Za-z/])", text):
                warnings.append({"sheet": sheet_name, "row": row_num, "header": header, "issue": "comma_spacing", "text": text})
            if re.search(r",,|\.\.(?!/)", text):
                warnings.append({"sheet": sheet_name, "row": row_num, "header": header, "issue": "double_punctuation", "text": text})
            if header in title_headers and re.search(r"\bvulnerability\b", text):
                warnings.append({"sheet": sheet_name, "row": row_num, "header": header, "issue": "lowercase_vulnerability", "text": text})
            if header in title_headers and text.rstrip().endswith("."):
                warnings.append({"sheet": sheet_name, "row": row_num, "header": header, "issue": "title_trailing_period", "text": text})
            if header in title_headers and re.search(r"\b(a|an|the)\b", text):
                warnings.append({"sheet": sheet_name, "row": row_num, "header": header, "issue": "title_article", "text": text})

    return warnings[:manual_review_limit]


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
        else input_path.with_name(f"{input_path.stem}_validation_DELIVERABLE.xlsx")
    )
    report_path = (
        Path(args.report).expanduser().resolve()
        if args.report
        else output_path.with_name(f"{output_path.stem}_report.json")
    )

    sheet_headers = collect_sheet_headers(input_path)
    main_cols = []
    for header in DEFAULT_MAIN_SOURCE_HEADERS:
        col_idx, found_sheets = detect_stable_column(sheet_headers, header)
        if col_idx is None:
            raise RuntimeError(f"Missing required validation header: {header}")
        if not found_sheets:
            raise RuntimeError(f"Header '{header}' was not found in any sheet")
        main_cols.append(col_idx)

    notes_col, note_sheets = detect_stable_column(sheet_headers, DEFAULT_NOTE_SOURCE_HEADER)

    session = requests.Session()
    health = get_json(session, f"{args.api_base}/api/health", "Check backend health")
    if health.get("status") != "ok":
        raise RuntimeError(f"Backend is not healthy: {health}")

    google_cfg = activate_google_translate(session, args.api_base)
    translation_ids = resolve_dictionary_ids(session, args.api_base, args.translation_dicts)
    main_replacement_ids = resolve_dictionary_ids(session, args.api_base, args.main_replacement_dicts)
    note_replacement_ids = resolve_dictionary_ids(session, args.api_base, args.note_replacement_dicts)

    main_created = create_project(
        session,
        args.api_base,
        input_path,
        f"{project_name}-main",
        main_cols,
        translation_ids,
        main_replacement_ids,
    )
    main_project_id = main_created["id"]

    note_project_id = None
    note_subset_path = None
    if notes_col is not None and note_sheets:
        note_subset_path = make_sheet_subset_copy(input_path, note_sheets)
        note_created = create_project(
            session,
            args.api_base,
            note_subset_path,
            f"{project_name}-notes",
            [notes_col],
            translation_ids,
            note_replacement_ids,
        )
        note_project_id = note_created["id"]

    main_translate = post_json(
        session,
        f"{args.api_base}/api/translate/{main_project_id}/translate-all",
        {},
        "Translate all main chunks",
    )
    main_replace = post_json(
        session,
        f"{args.api_base}/api/proofread/{main_project_id}/batch-replace-all",
        {},
        "Run batch replacement for main project",
    )

    note_translate = None
    note_replace = None
    if note_project_id is not None:
        note_translate = post_json(
            session,
            f"{args.api_base}/api/translate/{note_project_id}/translate-all",
            {},
            "Translate all note chunks",
        )
        note_replace = post_json(
            session,
            f"{args.api_base}/api/proofread/{note_project_id}/batch-replace-all",
            {},
            "Run batch replacement for note project",
        )

    backup_path = backup_database(repo_root, project_name)
    main_proofread = run_validation_proofread(repo_root, main_project_id)
    if not main_proofread["verify_clean"]:
        raise SystemExit("Validation proofreading did not return a clean result for the main project.")

    note_proofread = None
    if note_project_id is not None:
        note_proofread = run_validation_proofread(repo_root, note_project_id)
        if not note_proofread["verify_clean"]:
            raise SystemExit("Validation proofreading did not return a clean result for the note project.")

    put_json(
        session,
        f"{args.api_base}/api/project/{main_project_id}/status",
        {"status": "done"},
        "Set main project status",
    )
    if note_project_id is not None:
        put_json(
            session,
            f"{args.api_base}/api/project/{note_project_id}/status",
            {"status": "done"},
            "Set note project status",
        )

    main_project = get_json(session, f"{args.api_base}/api/project/{main_project_id}", "Fetch final main project")
    note_project = None if note_project_id is None else get_json(
        session,
        f"{args.api_base}/api/project/{note_project_id}",
        "Fetch final note project",
    )

    warnings = []
    if not args.skip_export:
        tmpdir = Path(tempfile.mkdtemp(prefix="validation_translate_proofread_export_"))
        main_export = tmpdir / "main_bilingual.xlsx"
        export_bilingual(session, args.api_base, main_project_id, main_export)
        if note_project_id is not None:
            note_export = tmpdir / "note_bilingual.xlsx"
            export_bilingual(session, args.api_base, note_project_id, note_export)
            merge_note_exports(main_export, note_export, output_path)
        else:
            shutil.copy2(main_export, output_path)
        warnings = audit_workbook(output_path, args.manual_review_limit)

    report = {
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
        "main_replacement_dicts": list(zip(args.main_replacement_dicts, main_replacement_ids)),
        "note_replacement_dicts": list(zip(args.note_replacement_dicts, note_replacement_ids)),
        "sheet_headers": sheet_headers,
        "main_project": {
            "id": main_project_id,
            "source_headers": DEFAULT_MAIN_SOURCE_HEADERS,
            "source_cols": main_cols,
            "translate_result": {
                "translated": main_translate.get("translated"),
                "errors": main_translate.get("errors", []),
            },
            "replace_result": main_replace,
            "chunk_count": main_project.get("chunk_count"),
            "verify_clean": main_proofread["verify_clean"],
            "verify_stdout": main_proofread["verify_stdout"],
        },
        "note_project": None if note_project_id is None else {
            "id": note_project_id,
            "source_header": DEFAULT_NOTE_SOURCE_HEADER,
            "source_col": notes_col,
            "sheets": note_sheets,
            "subset_path": str(note_subset_path) if note_subset_path else None,
            "translate_result": {
                "translated": note_translate.get("translated"),
                "errors": note_translate.get("errors", []),
            },
            "replace_result": note_replace,
            "chunk_count": note_project.get("chunk_count"),
            "verify_clean": note_proofread["verify_clean"],
            "verify_stdout": note_proofread["verify_stdout"],
        },
        "backup": str(backup_path),
        "manual_review_warnings": warnings,
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))

    print(
        json.dumps(
            {
                "project_name": project_name,
                "main_project_id": main_project_id,
                "note_project_id": note_project_id,
                "output": None if args.skip_export else str(output_path),
                "report": str(report_path),
                "warnings": len(warnings),
                "verify_clean": main_proofread["verify_clean"] and (note_proofread is None or note_proofread["verify_clean"]),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
