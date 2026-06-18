#!/usr/bin/env python3
"""End-to-end runner for validation mitigation standardization."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "p": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def normalize_workbook_target(target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    if target.startswith("xl/"):
        return target
    return "xl/" + target


def collect_cves(workbook_path: Path) -> list[str]:
    with zipfile.ZipFile(workbook_path) as archive:
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            sroot = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = ["".join(t.text or "" for t in si.iterfind(".//a:t", NS)) for si in sroot.findall("a:si", NS)]

        wb = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rel_map = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels.findall("p:Relationship", NS)}

        def value(cell: ET.Element) -> str:
            cell_type = cell.attrib.get("t")
            if cell_type == "inlineStr":
                return "".join(x.text or "" for x in cell.iterfind(".//a:t", NS))
            vnode = cell.find("a:v", NS)
            if vnode is None:
                return ""
            raw = vnode.text or ""
            return shared[int(raw)] if cell_type == "s" and raw.isdigit() else raw

        cves: list[str] = []
        for sheet in wb.find("a:sheets", NS):
            target = normalize_workbook_target(
                rel_map[sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]]
            )
            root = ET.fromstring(archive.read(target))
            for row in root.findall(".//a:sheetData/a:row", NS):
                values = [value(cell) for cell in row.findall("a:c", NS)]
                if len(values) > 5 and re.fullmatch(r"CVE-\d{4}-\d+", values[5]):
                    cves.append(values[5])
        return sorted(set(cves))


def run(cmd: list[str]) -> None:
    completed = subprocess.run(cmd, check=True, text=True, capture_output=True)
    if completed.stdout.strip():
        print(completed.stdout.strip())
    if completed.stderr.strip():
        print(completed.stderr.strip(), file=sys.stderr)


def load_cve_cache(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"CVE cache must be a JSON list: {path}")
    return [item for item in data if isinstance(item, dict)]


def cve_ids(data: list[dict[str, object]]) -> set[str]:
    return {str(item.get("cve", "")).upper() for item in data if item.get("cve")}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--dictionary", required=True, type=Path)
    parser.add_argument("--history", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--cve-json", type=Path)
    parser.add_argument("--compare-manual", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    fetch_script = script_dir / "fetch_cve_details.py"
    augment_script = script_dir / "augment_mitigation_cve_and_compare.py"

    cves = collect_cves(args.input)
    with tempfile.TemporaryDirectory() as tmpdir:
        details_json = args.cve_json or (Path(tmpdir) / "cve_details.json")
        if args.cve_json is None:
            fetch_cmd = [sys.executable, str(fetch_script), "--cves", *cves, "--output", str(details_json)]
            run(fetch_cmd)
        else:
            cached_data = load_cve_cache(args.cve_json)
            missing_cves = sorted(set(cves) - cve_ids(cached_data))
            if missing_cves:
                missing_json = Path(tmpdir) / "missing_cve_details.json"
                fetch_cmd = [sys.executable, str(fetch_script), "--cves", *missing_cves, "--output", str(missing_json)]
                run(fetch_cmd)
                merged_by_cve = {str(item.get("cve", "")).upper(): item for item in cached_data if item.get("cve")}
                for item in load_cve_cache(missing_json):
                    if item.get("cve"):
                        merged_by_cve[str(item["cve"]).upper()] = item
                details_json = Path(tmpdir) / "merged_cve_details.json"
                merged = [merged_by_cve[cve] for cve in sorted(merged_by_cve)]
                details_json.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
                print(json.dumps({"cve_cache_missing_fetched": missing_cves}, ensure_ascii=False))

        report_path = args.report or (args.output.parent / (args.output.stem + ".report.json"))
        manual_path = args.compare_manual or args.input
        augment_cmd = [
            sys.executable,
            str(augment_script),
            "--base",
            str(args.input),
            "--manual",
            str(manual_path),
            "--cve-json",
            str(details_json),
            "--dictionary",
            str(args.dictionary),
            "--output",
            str(args.output),
            "--report",
            str(report_path),
        ]
        if args.history:
            augment_cmd.extend(["--history", str(args.history)])
        run(augment_cmd)


if __name__ == "__main__":
    main()
