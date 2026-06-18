---
name: detection-proofread
description: Use when proofreading detection translation projects in the AI Translation Studio repo, especially `de*` projects that should follow the repo's detection dictionaries and `tools/detection/check_and_fix.py`. Use for running the detection proofreading script, backing up the active database first, reviewing residual translation issues, and continuously tightening the detection proofreading rules without overriding user-confirmed terminology.
---

# Detection Proofread

## Workflow
1. Confirm the target project, owner API base, and dictionaries before changing anything.
   Bind the proofreading run to the platform that owns the project. If the project is on `http://192.168.10.89`, use the 10.89 backend/database for dictionary inspection, DB backup, `tools/detection/check_and_fix.py`, manual SQL fixes, and export. Do not start or use a local backend/DB for that remote project ID.
   Use the local active project DB at `~/Documents/翻译软件/backend/instance/translator.db` only when the selected API base is local or the user explicitly says to use the local backend for this project.
   Check project dictionaries first; translation dictionaries outrank personal language preference.

2. Back up the live database before any repair pass or manual SQL change.
   For local projects, write backups under `~/Documents/翻译软件/output/env-backup/`. For remote projects, create the backup on the remote platform via SSH, for example with `--platform-ssh dx@192.168.10.89 --platform-root /opt/Aitrans`.
   Use descriptive names such as `translator_before_<project>_<reason>_<date>.db`.

3. Run the detection proofreading script first.
   For remote projects, run this command on the remote platform; if SSH or remote script access is unavailable, stop and report the blocker instead of falling back to local DB tools.
   Command:
   ```bash
   ./backend/venv/bin/python ~/Documents/翻译软件/tools/detection/check_and_fix.py <project_id> --repair
   ```
   Re-run without `--repair` to confirm the script now reports zero issues or only expected residuals.

4. Review the project manually after the script pass.
   Focus on `name.1`, `desc`, and `notes`.
   Prefer narrow fixes that match the Chinese source and the active dictionaries.
   Treat URLs, vendor links, and path casing as protected content unless the source clearly requires normalization.

5. Fold repeatable fixes back into the detection script.
   Add narrow deterministic patterns, not broad stylistic rewrites.
   Re-run the script on the current project after each meaningful rule change.
   Verify the script still compiles:
   ```bash
   ./backend/venv/bin/python -m py_compile ~/Documents/翻译软件/tools/detection/check_and_fix.py
   ```

## Priority Rules
- Obey project dictionaries first.
- Keep project ownership fixed: remote API projects must be proofread, repaired, backed up, and exported on the remote backend/database that owns them; never use local DB tools against a remote project ID.
- For software and product names, exact dictionary matches outrank manual language judgment.
- If a Chinese software name has no exact approved dictionary entry, do not normalize it to a more “natural” English product name. Flag it for review instead.
- Never replace a user-confirmed term with a more “natural” alternative.
- Prefer source-aligned terminology over generic security English.
- Chinese and English must stay semantically aligned. Never add scope, platform, product class, or attack context that is not explicit in the Chinese source.
- Do not upgrade a generic label to a narrower one by assumption. Example: `应用程序漏洞` can be `Application Vulnerability`, but must not become `Web Application Vulnerability` unless the source explicitly says `Web应用程序漏洞`.
- Keep title normalization, path normalization, and note-template cleanup separate.
- Preserve URLs exactly.

## Detection Conventions In This Repo
- Detection proofreading script:
  `~/Documents/翻译软件/tools/detection/check_and_fix.py`
- Common project pattern:
  `de####`
- Common title fields:
  `name.1`
- Common description fields:
  `desc`
- Common note fields:
  `notes`

## User-Confirmed Terminology
- If the dictionary says `信息泄露 -> Exfiltration`, keep `Exfiltration`.
- If the dictionary says `内存越界 -> memory overread`, keep `memory overread`.
- Do not silently switch these to `Information Disclosure` or `memory out-of-bounds read`.
- For detection terminology in this repo, use:
  `数据泄漏 -> Data Exfiltration`
  `信息泄露 -> information exfiltration`
- In English title fields such as `name.1`, keep approved attack phrases in title-style casing, including uppercase `Vulnerability` at the end:
  `SQL Injection Vulnerability`
  `Remote Code Execution Vulnerability`
  `Remote Command Execution Vulnerability`
  `Authentication Bypass Vulnerability`
  `Arbitrary File Read Vulnerability`
  `Arbitrary File Upload Vulnerability`
  `Arbitrary Code Execution Vulnerability`
  `Cross-Site Scripting (XSS) Vulnerability`
  `Arbitrary User Login Vulnerability`
  `File Upload Vulnerability`
  `Arbitrary File Write Vulnerability`
  `Command Execution Vulnerability`
  `Arbitrary User Addition Vulnerability`
  `Password Reset Vulnerability`
  `Data Exfiltration Vulnerability`
  `Sensitive Information Exfiltration Vulnerability`
  `Unauthorized Access Vulnerability`
  `Template Injection Vulnerability`
  `Directory Traversal Vulnerability`
  `XML Entity Injection Vulnerability`
  `XML External Entity Injection Vulnerability`
  `XML External Entity Injection (XXE) Vulnerability`
  `Server Side Request Forgery Vulnerability`
  `Server Side Request Forgery (SSRF) Vulnerability`
- Whenever the word `Vulnerability` appears in a title field, it must use uppercase `V`. Treat lowercase `vulnerability` in titles as a proofreading failure every time.
- Do not mechanically append or remove `Vulnerability` for mixed-style titles. For `Command Injection`, `Path Traversal`, `File Inclusion (LFI/RFI)`, `XML External Entity Injection (XXE)`, and `Server Side Request Forgery (SSRF)`, preserve the original approved wording exactly, while still keeping the attack phrase itself in title-style casing even when no `Vulnerability` suffix is present. Use `Cross-Site` with a hyphen, but keep `Server Side` without a hyphen when that is the approved wording.
- For framework-tagged payload titles such as `double quote bypass (Flask)`, title-case the attack phrase before the framework tag: `Double Quote Bypass (Flask)`.
- In title fields, do not add articles before filenames, interface names, method names, or paths. Keep technical identifiers source-aligned, for example `/download.ashx`, `postquerypublic`, `RESTFulServiceForWeb/Do`, `config.ini`.
- For title/article style in this repo, use `a SQL injection vulnerability`, not `an SQL injection vulnerability`.
- In title fields only, normalize `通信` to `Traffic`.
- In title fields only, normalize `流量` to `Traffic`, not `Flow`.
- In title fields only, normalize Chinese `C&C通信` to `C2 Traffic`; do not keep it as `C&C communication`.
- Do not mechanically rewrite body text `communication` to `Traffic`; keep that replacement scoped to titles.
- In English detection outputs, remove GB/GBT/国标 standard qualifiers for WVP video platform entries. Examples:
  `WVP Video Platform (GB 28181)` -> `WVP Video Platform`
  `WVP video platform (GB/T 28181-2016)` -> `WVP video platform`
  Remove explanatory clauses such as `implemented based on the GB/T 28181-2016 standard`, then repair the sentence so it still reads naturally, for example `WVP-PRO is a streaming media platform that relies on ...`.
  This cleanup is English-only; do not modify the Chinese source columns.

## Safe Rule Design
- Fix punctuation, spacing, glued terms, and path casing with deterministic patterns.
- Scope rules by header when possible.
- Prefer exact phrase replacements over loose regex for vulnerability terminology.
- Never bake domain assumptions into a replacement rule. If the rule injects a word that does not appear in the Chinese source, treat it as unsafe unless it is explicitly dictionary-backed.
- When adding a regex, test it on the current project and confirm it does not mutate unrelated fields.
- If a rule starts changing user-approved wording, remove or narrow it immediately.

## Manual Review Checklist
- Check whether titles still contain glued terms such as `CRLFinjection` or missing spaces after commas.
- Check whether English added meaning that is absent from Chinese, especially injected qualifiers such as `Web`, `server-side`, `vendor`, platform names, or protocol labels.
- Check title class labels carefully: `应用程序漏洞` vs `Web应用程序漏洞`, `漏洞利用` vs `Web漏洞利用`, and similar pairs must stay strictly source-aligned.
- Check whether approved attack phrases in `name.1` still use the repo casing convention, including uppercase `Vulnerability` at the end of the title phrase.
- Check whether paths such as `/v2/files` were distorted by translation.
- Check whether `desc` sentences still contain leftover machine artifacts such as missing articles, wrong product spacing, or injected unrelated terms.
- Check whether `notes` preserve the URL and the approved brand casing `digiDations`.
- Report remaining seq numbers and exact phrases before making non-deterministic wording changes.
