---
name: validation-proofread
description: Internal/helper validation cleanup skill for already-created `va*` projects in the AI Translation Studio repo. Use only when a validation project already exists and needs proofreading repair, notes/title cleanup, or rule tightening. This is not a peer to `standardize-validation-rules` and `validation-translate-proofread`.
---

# Validation Proofread

## Positioning
Keep validation work as two primary user-facing workflows:

- `standardize-validation-rules`: standardize the Chinese workbook
- `validation-translate-proofread`: translate + proofread + export the bilingual deliverable

Use `validation-proofread` only when a validation project already exists in the platform and the user wants project cleanup without starting from a workbook again.

## Workflow
1. Confirm this is really project-only proofreading.
   If the user is starting from an `.xlsx` workbook, route to `validation-translate-proofread` instead.
   If the task is Chinese standardization before translation, route to `standardize-validation-rules` instead.

2. Confirm the target project and inspect its dictionaries before changing anything.
   Use the active project DB at `~/Documents/翻译软件/backend/instance/translator.db` unless the running backend is clearly pointing elsewhere.
   Check project dictionaries first; translation dictionaries outrank personal language preference.

3. Back up the live database before any repair pass or manual SQL change.
   Write backups under `~/Documents/翻译软件/output/env-backup/`.
   Use descriptive names such as `translator_before_<project>_<reason>_<date>.db`.

4. Run the validation proofreading script first.
   Command:
   ```bash
   ./backend/venv/bin/python ~/Documents/翻译软件/tools/validation/check_and_fix.py <project_id> --repair
   ```
   Re-run without `--repair` to confirm the script now reports zero issues or only expected residuals.

5. Review the project manually after the script pass.
   Focus on `cn_name`, `cn_desc`, `cn_notes`, and playbook-style `Pipelines` descriptions.
   Prefer narrow fixes that match the Chinese source and the active dictionaries.
   Treat URLs, paths, hostnames, and product names as protected content unless the source clearly requires normalization.

6. Run delivery QA before reporting completion.
   Do not rely on "the script ran" as proof of quality. A deliverable must pass all of the gate checks below:
   - no broken dates such as `2026 05 16`; dates must stay `YYYY-MM-DD`
   - disclosure dates must use `披露时间：YYYY-MM-DD`
   - no loose CVE such as `CVE 2026 46364`; use `CVE-2026-46364`
   - in vulnerability titles, CVE must appear immediately after the product/software name and before endpoint/component and vulnerability type; `WordPress Smart Slider 3 slide- 任意文件读取漏洞，CVE-2026-3098` is wrong, use `WordPress Smart Slider 3，CVE-2026-3098，slide，任意文件读取漏洞`
   - URLs, paths, hostnames, function names, parameters, CVEs, versions, and code identifiers must be preserved unless the source explicitly requires a change
   - no reference URL path may be extracted into a title, for example `/campaigns/...`, `/actors/...`, or `/malware/...`
   - no `_x000D_`, flattened reference block, or same-line `Please refer to:` / `请参考： https://...`
   - Chinese reference blocks must have one blank line before `请参考：`: use `正文。\\n\\n请参考：\\nhttps://...`, not `正文。\\n请参考：\\nhttps://...`
   - no validation replacement bleed in descriptions, such as version numbers changed to `变种`, `Execution`, `Network Traffic`, or broken `.NET`
   - no residual `攻击技巧`; validation wording should use `攻击手法`
   - no residual FireEye attribution noise such as `归属于 FireEye 跟踪的未分类威胁组织的指标或活动`
   - no passive `由 <actor> ...` wording for attacker/threat-actor descriptions in Chinese output; use the actor as the subject instead, for example `APT-U3313 使用` / `攻击者 APT-U3313 使用该工具`, not `由 APT-U3313 使用` or `该工具由攻击者 APT-U3313 使用`
   - remove province/city location prefixes from vendor/product-introduction phrases; `山东博硕软件技术有限公司` should become `博硕软件技术有限公司`, and `山东青岛博鸣软件科技有限公司` should become `博鸣软件科技有限公司`. Keep geography only when it is part of the attack target, campaign scope, asset location, or source evidence, not when it merely prefixes a vendor/company name.
   - no `系统变种` in OS version discovery rows; use `系统版本`
   - every `cn_desc` body must end with terminal punctuation (`。` / `！` / `？`) before any reference block
   - no obvious Chinese readability failures in `cn_desc`, especially product description fragments that do not form a sentence
   - no duplicate Web vulnerability wording where the opening says `存在...漏洞的利用尝试` and the next sentence mechanically repeats `接口存在...漏洞`
   - after any script or bulk standardization pass, proofread `cn_name` prefixes/category labels: every action title must keep the expected validation prefix such as `恶意文件传输 -`, `Web应用程序漏洞 -`, `AI应用程序漏洞 -`, `工控安全 -`, `命令与控制 -`, or `受保护的沙盘 -`; flag rows where only `variant`/punctuation changed but the title still lacks the category prefix
   - threat actor names used as standalone title segments must include their entity type, for example `Mustang Panda 威胁组织，...`, `Parisite 威胁组织，...`, or `Hexane 威胁组织，...`; campaign names should use `攻击活动`, not `威胁组织`
   - rows with explicit Web endpoint paths such as `/api/...`, `.ashx`, `.php`, or `.jsp` must not be classified as generic `应用程序漏洞`
   - AI products with endpoint paths, such as AI coding agents, LLM platforms, MCP/Model Context Protocol tools, or AI workflow products, must remain `AI应用程序漏洞` rather than being classified as `Web应用程序漏洞`
   - industrial-control / OT products with endpoint paths, such as MES, SCADA, manufacturing execution, production-process management, or data acquisition/monitoring systems, must remain `工控安全` rather than being classified as `Web应用程序漏洞`
   - no host command row may remain as a bare command-help sentence; titles like `使用“CMD”命令显示...` and descriptions like `“CMD”显示...` must be rewritten into validation-action wording
   - no duplicate platform marker in titles, such as `Windows (Windows)`, `Linux (Linux)`, or `macOS (macOS)`; for host command titles, place the platform once after the action/tool object, for example `主机命令行 - 执行 ADExplorer.exe 工具 (Windows)，创建 AD 数据库快照`
   - platform markers must never attach to actor/campaign labels, for example `UAT-8302 威胁组织 (Windows)` or `Shadow Campaigns 攻击活动 (Windows)` is wrong; move `(Windows)` / `(Linux)` / `(macOS)` to the malware/tool/action object instead, such as `UAT-8302 威胁组织，执行 Stowaway 工具 (Windows)，通信隧道创建`
   - platform markers must not sit after behavior/attack names when a concrete tool, malware, or command exists; `ICMPINGER，主机扫描 (Windows)` and `KMLOG，键盘记录 (Windows)` are wrong, use `ICMPINGER (Windows)，主机扫描` and `KMLOG (Windows)，键盘记录`; if the source mentions a command such as `ping`, use `执行 ping 命令 (Windows)，DNS Exfiltration`

7. Manually sample high-risk rows after QA.
   Always read representative rows, not just machine-check them:
   - Web / AI / application vulnerability rows with CVE, path, disclosure time, and URL
   - rows containing versions such as `3.9.0`, paths, functions, parameters, or command-line flags
   - long `Sequences` and playbook-style descriptions
   - notes/reference blocks and any row with `受保护的沙盘`
   If any sample is not fluent Chinese or has protected-token damage, fix it and re-run QA.

8. Fold repeatable fixes back into the validation script.
   Add narrow deterministic patterns, not broad stylistic rewrites.
   Re-run the script on the current project after each meaningful rule change.
   Verify the script still compiles:
   ```bash
   ./backend/venv/bin/python -m py_compile ~/Documents/翻译软件/tools/validation/check_and_fix.py
   ```

## Priority Rules
- Obey project dictionaries first.
- Never replace a user-confirmed term with a more “natural” alternative.
- Chinese and English must stay semantically aligned. Never add scope, platform, product class, or behavior details that are not explicit in the Chinese source.
- Do not narrow a generic Chinese label by assumption. Only add qualifiers such as `Web`, `server-side`, `Windows`, or `PowerShell` when the source or active dictionary explicitly requires them.
- Preserve URLs exactly.
- Preserve protected tokens exactly unless a narrower source-aligned fix is required:
  dates, disclosure dates, CVE/CNVD/CWE/CAPEC IDs, URLs, URI paths, hostnames, filenames, extensions, function names, parameters, command-line flags, product names, and versions.
- Keep title normalization, notes-template cleanup, and sentence-level cleanup separate.
- Remove bad replacement rules if they are globally unsafe. Example: `:` must never be globally replaced with `,`.
- Never use broad dash or punctuation rewrites that can damage dates, CVEs, paths, versions, or product names. For example, a global `- -> space` replacement is forbidden.

## Validation Conventions In This Repo
- Validation proofreading script:
  `~/Documents/翻译软件/tools/validation/check_and_fix.py`
- Common project pattern:
  `va####`
- Common title fields:
  `cn_name`
- Common description fields:
  `cn_desc`
- Common note fields:
  `cn_notes`

## User-Confirmed Terminology
- In `cn_name`, `受保护的沙盘` should be `Protected Sandbox`.
- In `cn_notes`, `受保护的沙盘` should be `Isolator`.
- In `cn_notes`, the template should use:
  `This rule requires Isolator to execute correctly.`
- `variant` format should be `variant -1`, not `variant-1` and not `variant - 1`.
- Reference blocks should stay multiline:
  `Please refer to:`
  `https://...`
- In title fields such as `cn_name`, whenever the word `Vulnerability` appears, it must use uppercase `V`. Treat lowercase `vulnerability` in titles as a proofreading failure every time.
- In title fields only, normalize `通信` to `Traffic`.
- In title fields only, normalize `流量` to `Traffic`, not `Flow`.
- In title fields, translate campaign/activity labels as `Campaign`, not `Activity` or `Activities`; for example `网络间谍活动模拟` should become `Cyber Espionage Campaign Simulation`.
- In title fields, keep phishing payload/count wording singular when the Chinese source is singular: `恶意链接 -> Malicious Link`, `恶意附件 -> Malicious Attachment`.
- Do not apply the `C2` wording rule to validation category prefixes. Preserve prefix mappings such as `命令与控制 -` -> `Command and Control -`; only normalize `C&C`/`C&C通信` inside the post-prefix title content or body text.
- In title content after the category prefix, normalize Chinese `C&C通信` to `C2 Traffic`; do not keep it as `C&C communication`.
- In all English validation output body/content fields, normalize `C&C` to `C2` when it refers to command-and-control infrastructure, traffic, server, channel, or protocol.
- Do not mechanically rewrite body text `communication` to `Traffic`; keep that replacement scoped to titles.

## Safe Rule Design
- Fix punctuation, spacing, glued terms, repeated words, and title casing with deterministic patterns.
- Scope rules by header when possible.
- Prefer exact phrase replacements over loose regex for ATT&CK-style terminology bleed.
- Never write a rule that injects extra meaning not present in Chinese. If a replacement adds an English qualifier that cannot be pointed back to source text or dictionary, narrow or remove it.
- If a rule starts changing user-approved wording, remove or narrow it immediately.
- When a script warning becomes an expected-good format, narrow the checker instead of teaching users to ignore it.
- Protect first, then rewrite. If a regex touches protected tokens, add negative lookarounds, token protection, or remove the regex.
- Prefer exact bad-phrase fixes for readability issues. Do not introduce broad "make Chinese prettier" rules that can alter technical evidence.
- If the output required hand fixes, either fold the exact safe rule back into the script or label the file as a one-off; do not claim the reusable workflow is fixed.

## Manual Review Checklist
- Check whether `cn_name` still contains Chinese leftovers such as `执行`, `利用`, or `通信`.
- Check whether English introduced extra qualifiers absent from Chinese, especially words such as `Web`, `server-side`, `vendor`, platform names, or protocol labels.
- Check paired labels strictly against source, for example generic vs narrowed classes like `应用程序漏洞` and `Web应用程序漏洞`.
- Check whether `cn_desc` still contains validation replacement bleed such as `Execution`, `Obfuscation`, `Persistence`, `Network Traffic`, or broken `.NET` spacing.
- Check English output for command-and-control wording: Chinese source may use `C&C`, but English output should use `C2` consistently in content/body text; do not rewrite the validation category prefix `Command and Control -`.
- Check attacker/threat-actor wording in `cn_desc`: avoid passive `由 APT...` / `由攻击者...` phrasing; make the actor the subject for consistent validation prose.
- Check vendor/product introductions in `cn_desc`: remove province/city prefixes before company names, such as `山东博硕软件技术有限公司` -> `博硕软件技术有限公司` or `山东青岛博鸣软件科技有限公司` -> `博鸣软件科技有限公司`; do not apply this to target geography or campaign geography.
- Check whether every `cn_desc` body ends with terminal punctuation before `请参考：`.
- Check whether `cn_notes` preserve `digiDations`, `Isolator`, lowercase `vendor`, and intact URLs.
- Check whether `Please refer to:` blocks still preserve the full body text before the URL block.
- Check Chinese `请参考：` blocks have a blank line before them and the URL remains on the next line.
- Check whether `Pipelines` descriptions still contain mixed Chinese, broken paths, or machine-translation fragments.
- Check date and disclosure formats globally, not only in Web rows:
  `YYYY-MM-DD` and `披露时间：YYYY-MM-DD`.
- Check vulnerability-title order globally: product/software, `CVE-YYYY-NNNN`, endpoint/component, vulnerability type. Flag CVEs placed at the end of the title or after the vulnerability type.
- Check `cn_name` prefixes after running automated rules. Search for action titles missing the `类别 - ...` shape, and compare neighboring rows with the same campaign/product so one missed row does not remain among standardized rows.
- Check actor/campaign entity labels in titles: bare actor names like `Mustang Panda，...`, `Parisite，...`, or `Hexane，...` should be `... 威胁组织，...`; campaign names such as `Shadow Campaigns` or `Crimson Palace` should be labeled as `攻击活动`.
- Check title translations for campaign wording: `攻击活动` / `活动` in validation titles should be `Campaign`; flag `Activity` / `Activities` when it is being used as the campaign label.
- Check Web vulnerability descriptions for duplicated "存在漏洞" phrasing and product-description fluency.
- Check that vulnerability rows with explicit Web endpoint paths remain `Web应用程序漏洞`, including ERP or management-system products.
- Check product-specific application/appliance exceptions before applying generic Web-path classification, especially Infoblox NETMRI and 深信服运维安全管理系统.
- Check that AI application products remain `AI应用程序漏洞` even when the vulnerable entry is a Web path, especially products described as AI agents, LLM platforms, MCP/Model Context Protocol tools, or AI workflow systems.
- Check that industrial-control / OT products remain `工控安全` even when the vulnerable entry is a Web path, especially MES, SCADA, manufacturing execution, production-process management, and data acquisition/monitoring systems.
- Check host command rows for titles still shaped as `使用“...”命令显示...` and descriptions still shaped as command help text instead of validation-action text.
- Check host command platform placement: avoid `主机命令行 - Windows (Windows)` and similar duplicates; keep only one platform marker and attach it to the action/tool object.
- Check protected-sandbox and actor-led host-command title OS placement: `(Windows)` / `(Linux)` / `(macOS)` should attach to malware/tool/command name when present; if no concrete tool or command exists, attach it to the action/object segment before `变种 #n` or at the end of that action. It must never attach directly to the APT/actor/threat-organization/campaign segment or to a generic behavior label such as `主机扫描`, `键盘记录`, `通信隧道创建`, or `数据泄露`, because the platform describes the tool/action object, not the actor or behavior name.
- Check versions such as `3.9.0` were not normalized to `变种`.
- Report remaining `seq` numbers and exact phrases before making non-deterministic wording changes.

## Deliverable Rules
- For Excel deliverables, write to a new output file. Do not overwrite the user's original workbook.
- Do not use `_DELIVERABLE` in final filenames.
- Do not use status words such as `已校对` unless proofreading has actually been completed. For standardization-only output, use a neutral filename such as `_standardized.xlsx`.
- Generate a QA/report artifact next to the deliverable, such as `_report.json`, listing row counts, sampled rows, and all issues found.
- Do not tell the user a workbook is deliverable unless the report has zero blocking issues and high-risk samples have been manually read.
- If QA fails, say it failed and keep working; do not present that file as final.
