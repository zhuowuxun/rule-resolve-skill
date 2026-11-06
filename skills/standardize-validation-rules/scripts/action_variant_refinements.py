"""Place Actions title variant markers at the end without modifying identifiers."""
import re
from openpyxl import load_workbook

CN_MARKER = re.compile(r'变种\s*#\s*(\d+)|(?<![A-Za-z0-9/_])#\s*(\d+)')

def normalize_chinese_title(title):
    if not isinstance(title, str) or ' - ' not in title:
        return title
    hits = list(CN_MARKER.finditer(title))
    if len(hits) != 1:
        return title
    hit = hits[0]; number = hit.group(1) or hit.group(2)
    # A bare marker is a variant only in a malicious-file download title.
    if hit.group(1) is None and not (title.startswith("恶意文件传输 - ") and "下载" in title):
        return title
    body = (title[:hit.start()] + title[hit.end():]).strip()
    body = re.sub(r'\s*，\s*，', '，', body)
    body = re.sub(r'\s+，', '，', body).strip(' ，')
    return f'{body}，变种 #{number}'

def refine_action_variants(path):
    wb = load_workbook(path); changes = []
    if 'Actions' not in wb:
        return changes
    ws = wb['Actions']; headers = {c.value:c.column for c in ws[1]}
    if 'cn_name' not in headers:
        return changes
    for row in range(2,ws.max_row+1):
        cell=ws.cell(row,headers['cn_name']); before=cell.value; after=normalize_chinese_title(before)
        if after != before:
            cell.value=after; changes.append({'sheet':'Actions','row':row,'before':before,'after':after})
    wb.save(path)
    return changes
