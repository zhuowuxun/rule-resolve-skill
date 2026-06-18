#!/usr/bin/env python3
"""Fetch CVE descriptions and references from CVE detail pages."""

from __future__ import annotations

import argparse
import html as html_lib
import json
import re
import time
import urllib.request
from pathlib import Path
from typing import Dict, List


DESCRIPTION_RE = re.compile(r'<p data-testid="vuln-description">(.*?)</p>', re.S)
TABLE_RE = re.compile(r'data-testid="vuln-hyperlinks-table".*?</table>', re.S)
HREF_RE = re.compile(r'href="([^"]+)"')
NEXT_DATA_RE = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)
META_DESCRIPTION_RE = re.compile(r'<meta name="description" content="([^"]+)"', re.S)
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X) Codex Validation Skill"


def strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = (
        text.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
        .replace("&#160;", " ")
    )
    return re.sub(r"\s+", " ", text).strip()


def fetch_url(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read().decode("utf-8", errors="ignore")
        except Exception as exc:
            if attempt == 2:
                raise RuntimeError(f"Failed to fetch {url}: {exc}") from exc
            time.sleep(1.5 * (attempt + 1))
    return ""


def parse_nvd(html: str) -> tuple[str, List[str]]:
    description_match = DESCRIPTION_RE.search(html)
    description = strip_html(description_match.group(1)) if description_match else ""

    references: List[str] = []
    table_match = TABLE_RE.search(html)
    if table_match:
        seen = set()
        for ref in HREF_RE.findall(table_match.group(0)):
            if ref.startswith("http") and ref not in seen:
                seen.add(ref)
                references.append(ref)
    return description, references


def parse_tenable(html: str, tenable_url: str) -> tuple[str, List[str]]:
    description = ""
    references: List[str] = []

    data_match = NEXT_DATA_RE.search(html)
    if data_match:
        try:
            data = json.loads(html_lib.unescape(data_match.group(1)))
            cve_obj = data.get("props", {}).get("pageProps", {}).get("cve", {})
            description = str(cve_obj.get("description") or "").strip()
            seen = {tenable_url}
            references.append(tenable_url)
            for ref in cve_obj.get("references", []):
                url = str(ref.get("url") or "").strip()
                if url.startswith("http") and url not in seen:
                    seen.add(url)
                    references.append(url)
            for blog in cve_obj.get("blogs", []):
                url = str(blog.get("url") or "").strip()
                if url.startswith("http") and url not in seen:
                    seen.add(url)
                    references.append(url)
        except (TypeError, ValueError, json.JSONDecodeError):
            pass

    if not description:
        meta_match = META_DESCRIPTION_RE.search(html)
        description = strip_html(meta_match.group(1)) if meta_match else ""

    if not references and description:
        references.append(tenable_url)
    return description, references


def fetch_one(cve: str) -> Dict[str, object]:
    nvd_url = f"https://nvd.nist.gov/vuln/detail/{cve}"
    tenable_url = f"https://www.tenable.com/cve/{cve}"

    nvd_html = fetch_url(nvd_url)
    description, references = parse_nvd(nvd_html)
    source_url = nvd_url

    if not description or not references:
        try:
            tenable_html = fetch_url(tenable_url)
            tenable_description, tenable_references = parse_tenable(tenable_html, tenable_url)
            if tenable_description and not description:
                description = tenable_description
                source_url = tenable_url
            if tenable_references:
                if not references:
                    references = tenable_references
                    source_url = tenable_url
                else:
                    seen = set(references)
                    references.extend(ref for ref in tenable_references if ref not in seen)
        except RuntimeError:
            pass

    if not references:
        references.append(source_url)

    return {
        "cve": cve,
        "source_url": source_url,
        "description_en": description,
        "references": references[:5],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cves", nargs="+", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    data = [fetch_one(cve) for cve in args.cves]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"count": len(data), "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
