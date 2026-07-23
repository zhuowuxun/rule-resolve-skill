---
name: standardize-validation-rules
description: Primary user-facing validation standardization workflow. Use when standardizing validation main-rule Excel workbooks such as `t_1.xlsx`, especially `Actions`, `Sequences`, and `Email` sheets that need approved Chinese naming, description, notes, OS suffix, actor wording, and Web-vulnerability formatting while staying separate from mitigation logic. This is the “标准化” half; pair it with `validation-translate-proofread` for the later translation+QA half.
---

# Standardize Validation Rules

## Positioning
Validation should feel like two user-facing workflows:

- `standardize-validation-rules`: standardize the Chinese workbook
- `validation-translate-proofread`: translate, proofread, QA, and export the bilingual output

Do not treat `validation-proofread` as a third peer workflow; that skill is only for already-created `va*` project cleanup.

Use this skill only for the main-rule branch of validation standardization.
It is separate from mitigation and should not reuse mitigation output style.

## Scope
This skill is for validation main workbooks shaped like:
- `t_1.xlsx`
- `Actions`
- `Sequences`
- `Email`

This skill is not for:
- `mit_1.xlsx`
- mitigation dictionaries
- CVE remediation appendices
- mitigation-style `请参考：` blocks

## Workflow
1. Inspect the workbook structure first.
   Expected sheets:
   - `Actions`
   - `Sequences`
   - optional `Email`
   Confirm whether the workbook is validation main-rule, validation mitigation, or detection before applying any script. Do not mix branches.

2. Standardize `Actions` in place.
   - Normalize `cn_name`, `cn_desc`, and `cn_notes`.
   - If both `notes` and `cn_notes` exist, update `cn_notes` as the Chinese delivery-notes column and keep raw `notes` unchanged unless the user explicitly asks otherwise.
   - Keep `APT-U####` identifiers with the hyphen.
   - Remove campaign identifiers such as `CAMP.26.029` from rule names; in descriptions, replace such identifiers with `攻击活动` if they need to remain semantically visible.
   - Standardize `变种 #n`.
   - Standardize actor wording such as `行为体` / `威胁集群` / `恶意软件集群` to the approved wording.
   - Standardize `攻击技巧` to `攻击手法`.
   - Preserve organization hierarchy when present, using `子组织` rather than flattening the relationship.

3. Apply validation-only naming rules.
   - Web rules should use the approved vulnerability naming pattern.
   - Normalize `Web安全验证 -` / `web安全验证 -` to `Web应用程序漏洞 -`.
   - If a title contains an explicit Web endpoint path such as `/api/...`, `.ashx`, `.php`, `.jsp`, or another URL-path-like entry, keep/classify it as `Web应用程序漏洞` even when the product name contains application words such as `ERP` or `管理系统`.
   - AI product classification has higher priority than Web endpoint classification. If the product or description identifies the target as an AI application, LLM platform, AI coding agent, MCP/Model Context Protocol server/tool, or AI workflow product, use `AI应用程序漏洞` even when the vulnerability entry contains a Web path such as `/session/`.
   - Industrial-control / OT product classification has higher priority than Web endpoint classification and lower priority than AI classification. If the product or description identifies MES, SCADA, manufacturing execution, production-process management, data acquisition/monitoring, scheduling, warehouse, or equipment-fixture management systems, use `工控安全` even when the vulnerable entry is a Web path such as `.ashx`.
   - Product-specific application/appliance classification has higher priority than generic Web-path classification. For products such as Infoblox NETMRI and 深信服运维安全管理系统, use `应用程序漏洞` even when the entry contains a Web path.
   - Normalize loose CVE forms such as `CVE 2026 2441` to `CVE-2026-2441`; when a raw vulnerability title lacks the CVE but the description contains it, extract the normalized CVE into the title before the vulnerability type.
   - If an Actions row lacks a validation prefix, infer the prefix from `cn_name`, `cn_desc`, and `cn_notes`; double-robot notes with vulnerability names should not be classified as `主机命令行`.
   - If a title mentions malicious files but the note is a single-machine execution note rather than a source/target robot note, classify it as `主机命令行`, not `恶意文件传输`.
   - If a raw vulnerability title describes an executable exploit program/file and the notes use source/target robots, classify it as `恶意文件传输`, not `应用程序漏洞`.
   - Mark rows where a missing prefix was added so the inferred prefix can be manually reviewed.
   - For raw malicious-download titles like `X，由 Y 威胁组织使用，.EXT 文件下载变种 #n`, standardize as `恶意文件传输 - Y，X，.EXT 文件，下载，变种 #n`; preserve threat-actor spacing such as `Lazarus Group`.
   - Use `AI应用程序漏洞` for AI application products such as Langflow, Open WebUI, OpenClaw, MLflow, LiteLLM, MindsDB, LibreChat, NocoBase, opencode, and short-video-maker.
   - Use `应用程序漏洞` for application/appliance products such as Citrix NetScaler, D-Link NAS, Fortinet FortiClientEMS, Fortinet FortiSandbox, Jumpserver, Infoblox NETMRI, 深信服运维安全管理系统, and similar product-specific business/application appliances.
   - Do not force 东胜物流软件 to `应用程序漏洞` in validation main-rule workbooks; when it is represented as a Web endpoint vulnerability, keep `Web应用程序漏洞`.
   - Use `工控安全` for industrial-control products such as 深科特 LEAN MES and similar MES/SCADA/manufacturing execution systems; descriptions that identify the product as an industrial protocol gateway, protocol conversion gateway, communication gateway, or industrial-device integration product should also use `工控安全`.
   - Host command, command-and-control, malicious file transfer, protected sandbox, scene, and email rows should follow the confirmed validation naming rules.
   - Host command titles must not stop at appending an OS suffix. Rewrite verbose forms like `主机命令行 - 使用“CMD”命令显示XXX` into `主机命令行 - CMD，XXX显示 (Windows)` or the closest concise action form.
   - In `Sequences`, normalize residual `下载威胁` wording to `下载攻击活动` so the final title does not become `下载威胁 攻击活动`.
   - In `Sequences`, if the subject already ends with `恶意软件活动`, normalize it to `恶意软件攻击活动` rather than appending another `攻击活动`.
   - In `Sequences`, correct machine-translated actor/malware names and verbs when the description makes the English original clear, for example `珍珠窃取者` -> `Pearl Stealer`, `Koi Stereer` -> `Koi Stealer`, and `放弃 Koi Stealer 活动` -> `投放 Koi Stealer 攻击活动`.
   - In `Sequences`, keep scene numbering as trailing `#n` such as `恶意活动场景 - APT36 威胁组织攻击活动 #2`; do not use `，变种 #n` for scene titles.
   - OS suffixes use English parentheses such as `(Windows)` / `(Linux)` / `(macOS)`.
   - Place OS suffixes near the malware/tool/product segment, not after action verbs such as `执行` / `下载` / `投放`.
   - For protected-sandbox rows, keep OS suffix placement stable: attach `(Windows)` / `(Linux)` to the concrete malware/tool/file/object name when present; do not leave OS after action phrases such as `数据聚合`, `C&C 渗透`, `C&C 信标`, `C&C 域名信标`, `DNS 泄露数据`, `执行`, `下载`, or `投放`.
   - For host-command rows, attach the OS suffix to the concrete command/action/object segment, not to the actor or malware family segment. For example, use `主机命令行 - APT42，TAMECAT，清除运行历史记录 (Windows)，变种 #1`, not `TAMECAT (Windows)，清除运行历史记录`.
   - For protected-sandbox rows, preserve English malware/tool names extracted from the description and do not translate them into Chinese. Examples: use `SANDCLOCK`, not `沙漏`; use `Stage Script释放器`, not `舞台脚本释放器`.
   - For protected-sandbox persistence rows, if the description names a task/service such as `ChromeUpdate`, insert that object before the action, for example `ChromeUpdate，持久化 (Windows)`.
   - Pure extension file types should keep the dot, for example `.EXE 文件` / `.MACHO 文件`; infer `(macOS)` for macOS-specific extensions such as `.MACHO` and `.SCPT`.
   - If a malicious file-transfer description says the downloaded object is an `恶意快捷方式文件` or `.LNK 文件`, add `恶意快捷方式文件` before `下载` in the title.
   - If a malicious file-transfer description gives a precise file type such as `.NET 木马` or `恶意 .NET 可执行文件`, add that precise malicious-file type to the title even when the malware family name is already present, for example `REGALSPICE，恶意 .NET 木马文件，下载`.
   - If a malicious file-transfer title only says `下载`, infer and add the downloaded file/tool type from the description, for example `远程访问工具` -> `恶意远程访问工具`.
   - If a malicious file-transfer title has only an actor plus a generic file/tool type, but the description names a concrete malware family/tool such as `CORNFLAKE 感染程序`, insert that concrete name before the generic type and before `下载`; do not insert generic technical words such as `API`, `URL`, `GET`, or `POST`.
   - Keep inferred malicious file-transfer types concise, such as `恶意远程访问工具`, `恶意远程访问木马文件`, `恶意安装程序`, `恶意 Windows Installer 程序包`, `恶意 JavaScript 下载器`, and do not backfill long URL paths into titles.
   - For malicious file-transfer rows, infer precise file/container types from the description when the title only says `下载`, including `.NET 可执行文件`, `恶意 .NET DLL文件`, `恶意 .NET 程序集`, `Python 脚本文件`, `恶意 PowerShell 下载脚本`, `恶意 PowerShell 脚本`, `恶意 VBA 脚本`, `macOS 后门文件`, `恶意 macOS 可执行文件`, `32 位 Windows .DLL文件`, `恶意 Windows .DLL文件`, `恶意动态链接库文件`, `恶意软件组件文件`, `恶意库组件文件`, `木马化的软件组件文件`, `混淆脚本文件`, `恶意配置脚本文件`, `恶意混淆脚本文件`, `恶意批处理脚本文件`, `恶意脚本文件`, `恶意 JavaScript 木马文件`, `恶意文档文件`, `恶意电子表格文件`, `恶意网页文件`, `恶意配置文件`, `释放器`, and `压缩存档文件`.
   - In malicious file-transfer names, shorten redundant malware nouns such as `Dindoor后门恶意软件` to `Dindoor后门` and `恶意软件释放器` to `释放器`, while descriptions may retain the fuller object wording.
   - For command-and-control rows, preserve URI paths from the description in `cn_name`, for example `/api/auth/login` or `/api/home/status`.
   - For Web / AI / application vulnerability rows, if the description contains a more complete endpoint path than the raw title and it contains the title path's tail, use the complete description path in both `cn_name` and the opening sentence.
   - Normalize `电报` to `Telegram` in command-and-control names.
   - Collapse duplicated C2 wording such as `C&C 或 C&C` to a single `C&C`.
   - For phishing-email malicious-link rows, keep the existing Email subject and do not backfill long URL paths from the `Email` body into the action title; `恶意链接` is enough unless the title/description already contains a concise payload family or file type.

4. Apply validation-only description rules.
   - Prefer the opening `此验证动作还原了...`.
   - Every `cn_desc` body must end with terminal punctuation (`。` / `！` / `？`) before any reference block.
   - Host command descriptions must describe the validation action, not merely restate the tool help text. For example, `“tasklist”显示...` should become `此验证动作还原了在 Windows 主机上执行 tasklist /svc 命令以显示...的行为。`
   - Normalize `网络钓鱼电子邮件` to `钓鱼邮件` in descriptions as well as titles.
   - File-transfer descriptions should use `此验证动作还原了主机尝试下载...。` and should not append `的过程` at the end of the first sentence.
   - File-transfer descriptions should use one consistent actor/object association format: `恶意软件或工具 (APT-U####)`; do not mix this with `恶意软件或工具，APT-U####`. When there are multiple objects, attach the APT ID to the first malware/tool object, for example `REMCOS (APT-U5487) 和 SHADOWLADDER`.
   - File-transfer type enrichment is primarily for `cn_name`; do not force the first description sentence from `与 APT-U#### 关联的文件` into a longer typed object unless the original wording is unclear or ungrammatical.
   - For scene descriptions composed from malicious-file-transfer download threats, use wording such as `此验证场景包括了与 X 相关的各种变种的下载。` rather than `各种样本`; do not apply this to non-download ransomware attack scenes such as plain `INC 勒索软件攻击活动`.
   - Web descriptions should follow the detection-inspired order:
     - utilization sentence
     - attack explanation
     - disclosure time
     - software description
     - reference block, when present
   - Web descriptions must be fluent Chinese, not only structurally correct.
   - Remove duplicate vulnerability wording: after the opening `此验证动作还原了针对...存在的...漏洞的利用尝试。`, the next attack sentence should not mechanically repeat `接口存在...漏洞，...`; rewrite it to the actual attacker action/impact.
   - Trim promotional product-copy phrases in software descriptions, especially broad claims such as helping users manage leads, guide sales follow-up, or improve team sales capability; keep only concise product identity and necessary feature context.
   - Disclosure time format is fixed: `披露时间：YYYY-MM-DD。`
   - Reference blocks should stay multiline:
     ```text
     请参考：

     https://...
     ```
   - Remove disposable markdown/link placeholders and unwanted attribution tails.
   - Remove province/city prefixes from company introductions when they are only geographic qualifiers.
   - Keep raw `notes` and `Pipelines` URLs intact; do not run mitigation reference-block logic on validation main-rule workbooks.
   - Preserve all protected technical evidence in descriptions: URL, path, hostname, filename, extension, function, method, parameter, CLI flag, CVE, version, and date.
   - Preserve defanged indicators such as `example[.]com`; do not treat `[.]` as disposable markdown text.
   - Attribution/political-noise cleanup must be narrowly scoped. Do not delete normal validation-action sentences merely because they contain `APT-U####` plus `威胁组织`.
   - If the source `cn_desc` is non-empty, standardization must not output an empty `cn_desc`; fall back to the source-normalized description and report the row instead of erasing evidence.
   - For protected-sandbox notes, use `此验证动作需要在受保护的沙盘中才能正确执行。`; do not write `受保护的沙盘环境中`.

5. Handle `Email` conservatively.
   - Keep existing `cn_subject` unchanged; subjects may already be manually adjusted.
   - Only normalize `cn_body` when there is an obvious formatting issue, and never infer or randomize a new subject unless the user explicitly asks.

6. Apply optional `Pipelines` cleanup when the workbook contains the sheet.
   - Only do light validation-main cleanup: actor wording, English/Chinese spacing, punctuation, and obvious machine-translation residue.
   - Preserve playbook meaning and URLs; do not rewrite playbook descriptions as `此验证动作还原了...`.

7. Keep mitigation logic out.
   - Do not generate mitigation-style `请参考：` blocks.
   - Do not use mitigation dictionary fill logic.
   - Do not treat the workbook as a remediation sheet.

8. Compare against a manual workbook only as evaluation.
   - Use the manual workbook to identify rule gaps.
   - Absorb stable rule improvements into the validation script or this skill.
   - Do not copy mitigation-specific wording into validation outputs.

9. Run delivery QA and manual sampling before final response.
   A workbook is not final just because the script completed. Required gates:
   - do not visually mark all rewritten names or prefixes with yellow fill; keep standardized Excel deliverables clean unless the user explicitly asks for highlighted diffs
   - no `YYYY MM DD` date fragments anywhere
   - no `披露时间:`; must be `披露时间：YYYY-MM-DD`
   - no loose CVE such as `CVE 2026 46364`
   - no `_x000D_`
   - no old `变种-1` / `变种 1` title format
   - no URL mismatch between original and output for rows where URLs are preserved
   - no reference links flattened onto the same line as `请参考：`; reference blocks must be `请参考：` followed by one blank line and then the URL lines
   - no reference links may remain in `cn_notes`; if source `cn_desc` contains URLs, the standardized output must keep them at the end of `cn_desc` as a multiline `请参考：` block, while `cn_notes` should contain only execution/validator notes
   - no reference URL paths such as `/campaigns/...`, `/actors/...`, `/malware/...` inserted into C2 titles
   - no protected-token damage: dates, CVEs, paths, hostnames, filenames, extensions, functions, parameters, flags, versions, and product names
   - no defanged-domain damage such as turning `telen[.]example[.]com` into `telen example com`
   - no source-described Actions row may have an empty output `cn_desc`
   - no residual `攻击技巧`; use `攻击手法`
   - no residual FireEye attribution noise such as `归属于 FireEye 跟踪的未分类威胁组织的指标或活动`
   - no `系统变种` when the row describes GetVersionExW or OS version discovery; use `系统版本`
   - no `cn_desc` body may end without terminal punctuation before a reference block
   - no protected-sandbox OS suffix may appear after an action phrase when a malware/tool/actor segment is available
   - no known bad readability fragments such as broken product descriptions, missing spaces around common English identifiers, or `可以自动化、可视性...`
   - Web / AI / application vulnerability rows must pass the duplicate-vulnerability check described above
   - rows with explicit Web endpoint paths must not be downgraded from `Web应用程序漏洞` to generic `应用程序漏洞`
   - AI products with endpoint paths must remain `AI应用程序漏洞`, not `Web应用程序漏洞`
   - industrial-control products with endpoint paths must remain `工控安全`, not `Web应用程序漏洞`
   - no host command title may remain in the verbose `使用“...”命令显示...` form after standardization
   - no host command description may remain as bare command help text such as `“CMD”显示...` without the `此验证动作还原了...` opening
   - the final `.xlsx` must be Excel-openable, not merely a valid zip archive:
     - after XML-level edits, always rewrite/save the final workbook through `openpyxl`
     - reopen the exact output file with `openpyxl` and iterate all cells
     - run `unzip -t` on the exact output file
     - if any of these checks fail, do not deliver the workbook

   Manual sampling is mandatory after machine QA. Read at least:
   - several Web / AI / application vulnerability rows with CVE + path + URL
   - one row with a disclosure date
   - one row with a version number
   - one long `Sequences` row
   - one row with protected paths/functions/parameters
   Fix any issue found and re-run QA.

10. Compare the standardized workbook against the source workbook before final response.
   - Align by `uuid` / `vid` when available and compare `cn_name`, `cn_desc`, `cn_notes`, `cn_subject`, `cn_body`, and any standardized `Sequences` fields.
   - Treat loss of `未` / `未经` before `授权` / `身份验证`, dropped CVE/path/URL/file/function/parameter/date/version tokens, dropped defanged indicators, and empty output descriptions from non-empty sources as failed runs.
   - For Web / AI / application vulnerability rows, if the source description contains a fuller endpoint path than the title, verify the final `cn_name` and opening sentence use the full path instead of only the short title path.
   - For `恶意文件传输`, verify inferred file/tool types were added before `下载` only when useful, and that concrete filenames already present in the source were not overwritten by generic type labels.
   - For `Sequences`, verify campaign IDs are removed or converted to `攻击活动`, while meaningful non-markdown extra sentences about threat organizations, malware, tools, or activity background are preserved after cleanup.
   - Keep existing `Email` subjects unchanged unless the user explicitly asked to change them.
   - If the compare finds real content loss, patch the script/rules, regenerate, rerun QA, and rerun the source compare before delivery.

## Script
Use the bundled runner for deterministic execution:

```bash
python3 ~/.codex/skills/standardize-validation-rules/scripts/run_validation_main_standardization.py \
  --input /path/to/t_1.xlsx \
  --output /path/to/output.xlsx \
  --report /path/to/report.json
```

## Protected Token Rules
These are hard constraints. Normalization rules must not alter them unless a narrow source-aligned correction explicitly targets the token.

- dates: `2026-05-16` must not become `2026 05 16`
- disclosure dates: always `披露时间：YYYY-MM-DD`
- CVE/CNVD/CWE/CAPEC IDs
- URLs and URL paths
- URI paths such as `/api/v1/utils/code/execute`
- hostnames and domains
- filenames and extensions such as `.LNK`, `.NET`, `.ashx`
- functions/methods such as `BuiltinCaptcha::saveCaptcha()`
- parameters such as `User-Agent`, `website_url`, `ENABLE_CODE_EXECUTION`
- command-line flags such as `--app-name basic-auth`
- product names and versions such as `MLflow 3.9.0`, `Notepad++`, `MS17-010`

Forbidden broad rewrites:
- global dash removal or `-` to space
- global colon replacement
- global slash/path spacing
- global title-casing inside paths, code, URLs, or product names

If a rule must edit punctuation, scope it by field, row type, and surrounding text. Add QA that proves the protected tokens survive.

## Output Naming
- Use a new output file; never modify the input workbook.
- Use `_standardized.xlsx` for the final standardized workbook.
- Do not add verbose delivery/final suffixes to validation standardization filenames.
- Keep a sibling report such as `_standardized_report.json`.
- If a generated workbook fails QA, do not present it as final. Fix, regenerate, and re-run QA first.

## References
Read these only when needed:
- main validation rules: `references/validation主规则标准化执行版_20260421.md`
- split index: `references/validation标准化重构草案_20260421.md`

## When To Stop And Ask
- The workbook is actually a mitigation sheet.
- The user wants mitigation dictionary or CVE remediation logic.
- The sheet structure differs materially from `Actions` / `Sequences` / `Email`.
