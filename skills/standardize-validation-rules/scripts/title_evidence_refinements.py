"""Add only file types and request paths explicitly described in validation source."""
import re
from openpyxl import load_workbook

FILE_TYPES=[
 ('恶意 .NET 动态链接库','恶意 .NET 动态链接库文件'),
 ('特洛伊木马化的动态链接库','木马化的动态链接库文件'),
 ('恶意动态链接库','恶意动态链接库文件'),
 ('恶意可执行文件','恶意可执行文件'),
 ('压缩存档','压缩存档文件'),
 ('模块化后门','模块化后门'),
 ('恶意植入程序','恶意植入程序'),
 ('恶意组件','恶意组件文件'),
]

def refine_title(name,desc):
 if not isinstance(name,str) or not isinstance(desc,str):return name
 if name.startswith('恶意文件传输 - ') and '，下载' in name:
  before=name.split(' - ',1)[1].split('，下载',1)[0]
  if not re.search(r'文件|程序|后门|木马|工具|样本|组件|脚本|动态链接库|程序集|压缩存档',before,re.I):
   sentences=desc.split('。')[:2];body='。'.join(sentences)
   for evidence,label in FILE_TYPES:
    if evidence in body:
     name=name.replace('，下载','，'+label+'，下载',1);break
 if name.startswith('应用程序漏洞 - ') and re.search(r'CVE-\d{4}-\d+',name) and not re.search(r'(?<![\w])/[A-Za-z0-9_.-]+/',name):
  body=desc.split('请参考：',1)[0]
  match=re.search(r'(?:攻击目标是位于|向)\s*[`"“]?(/[-\w.%@{}:]+(?:/[-\w.%@{}:]+)+)[`"”]?\s*(?:的身份验证端点|发送)',body)
  if match:
   path=match.group(1)
   name=re.sub(r'(，变种 #\d+)$',lambda m:'，'+path+m.group(1),name) if re.search(r'，变种 #\d+$',name) else name+'，'+path
 return name

def refine_title_evidence(path):
 wb=load_workbook(path);changes=[]
 if 'Actions' not in wb:return changes
 ws=wb['Actions'];h={c.value:c.column for c in ws[1]}
 for i in range(2,ws.max_row+1):
  c=ws.cell(i,h['cn_name']);before=c.value;after=refine_title(before,ws.cell(i,h['cn_desc']).value)
  if after!=before:c.value=after;changes.append({'sheet':'Actions','row':i,'before':before,'after':after})
 wb.save(path);return changes
