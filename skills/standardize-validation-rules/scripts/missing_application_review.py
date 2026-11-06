"""Flag vulnerability titles with no identifiable product segment for review."""
import re
from openpyxl import load_workbook
from openpyxl.styles import PatternFill

YELLOW = PatternFill('solid', fgColor='FFFFF59D')
PREFIX = re.compile(r'^(?:Web应用程序漏洞|AI应用程序漏洞|应用程序漏洞|远程服务漏洞|工控安全)\s*-\s*(.*)$', re.I)
CODE_OR_PATH = re.compile(r'^(?:CVE[-\s]\d{4}[-\s]\d+|CNVD[-\s]\d{4}[-\s]\d+|/|变种\s*#\d+)', re.I)
GENERIC = re.compile(r'^(?:(?:SQL\s*注入|SSRF|XSS|远程代码执行|命令执行|身份认证绕过|认证绕过|任意文件读取|任意文件上传|路径穿越|权限提升|信息泄露|未授权访问)漏洞|漏洞)$', re.I)

def lacks_application_name(value):
    if not isinstance(value, str):
        return False
    match = PREFIX.match(value.strip())
    if not match:
        return False
    body = match.group(1).strip()
    if not body:
        return True
    first = re.split(r'[，,]', body, maxsplit=1)[0].strip()
    return bool(CODE_OR_PATH.match(first) or GENERIC.fullmatch(first))

def flag_missing_applications(path):
    wb = load_workbook(path)
    findings = []
    if 'Actions' not in wb:
        return findings
    ws = wb['Actions']
    h = {cell.value: cell.column for cell in ws[1]}
    if 'cn_name' not in h:
        return findings
    for row in range(2, ws.max_row + 1):
        title = ws.cell(row, h['cn_name'])
        if not lacks_application_name(title.value):
            continue
        columns = ['cn_name'] + (['en_name'] if 'en_name' in h else [])
        for column in columns:
            ws.cell(row, h[column]).fill = YELLOW
        findings.append({'sheet':'Actions', 'row':row, 'uuid':ws.cell(row, h['uuid']).value if 'uuid' in h else None,
                         'title':title.value, 'marked_columns':columns, 'reason':'漏洞标题缺少应用或产品名称，待核对'})
    if findings:
        wb.save(path)
    return findings
