---
name: validation-translate-proofread
description: Primary user-facing validation delivery workflow. Translate and proofread validation Excel workbooks in AI Translation Studio. Use when the user wants the “翻译+校对” half of validation work for `.xlsx` workbooks with `cn_name`, `cn_desc`, `cn_notes` and preallocated `en_name`, `en_desc`, `en_notes` columns. Pair with `standardize-validation-rules`; do not treat `validation-proofread` as a third peer workflow.
---

# Validation Translate Proofread

## Positioning
Validation should feel like two user-facing workflows only:

- `standardize-validation-rules`: standardize the Chinese validation workbook first
- `validation-translate-proofread`: translate, proofread, QA, and export the bilingual deliverable

`validation-proofread` still exists, but only as a project-only helper for already-created `va*` projects. It is not a third peer entry point.

## Core Rules
- Work in `~/Documents/翻译软件` for local scripts unless the user explicitly points to another AI Translation Studio checkout.
- Default API is `http://192.168.10.89`. If `192.168.10.89` is unreachable or AI Translation Studio readiness is not confirmed, stop and ask the user to confirm the platform API base URL. Do not silently fall back to `127.0.0.1`.
- Do not change the platform-global active model silently. Google Translate must already be active before translation starts, or `--activate-google` may be used only after explicit user confirmation.
- Do not overwrite the user's original workbook. Export a new `_DELIVERABLE.xlsx` plus a `_report.json`.
- Bind the project to the API base that creates or owns it. If the project is on `http://192.168.10.89`, keep translation, replacement, proofreading, DB backup, `check_and_fix.py`, status changes, and export on 10.89. Do not use a local backend/DB to proofread or repair that remote project ID.
- Use the local active database at `backend/instance/translator.db` only for local API projects or when the user explicitly says to use the local backend.
- Back up the database before repair passes or manual SQL changes under `output/env-backup/`.
- When `--api-base` points to a non-local platform such as `http://192.168.10.89`, DB backup, note-only replacement scope checks, and `tools/validation/check_and_fix.py` must run on that remote platform via `--platform-ssh`; never run local DB tools against a remote project ID.
- Treat project dictionaries as authoritative.
- If the workbook has not been standardized yet, run `standardize-validation-rules` first unless the user explicitly wants a raw translation pass.
- `validation note replacement` is note-only. It may apply only to chunks whose Excel header is `cn_notes` and must not touch `cn_name` or `cn_desc`.
- If the backend service code does not enforce note-only scoping, enforce it manually and patch the service before future runs.
- Validation translation must create exactly one AI Translation Studio project per workbook. Do not split one workbook into separate `main` and `notes` projects just to isolate `validation note replacement`; the backend replacement flow must scope that dictionary to `cn_notes`.

## Expected Dictionaries
Use these dictionaries when present:

- Translation dictionaries: `专业名称翻译`, `software翻译`
- Replacement dictionaries: `基础字符校对`, `validation校对`
- Note-only replacement dictionary: `validation note replacement`

Look up dictionary IDs from `backend/instance/translator.db`; do not assume IDs are stable. Typical current IDs are:

- `专业名称翻译`: `1`
- `基础字符校对`: `2`
- `software翻译`: `5`
- `validation校对`: `6`
- `validation note replacement`: `7`

## Workbook Intake
Inspect the workbook before creating a project:

```bash
./backend/venv/bin/python - <<'PY'
from openpyxl import load_workbook
p = "INPUT.xlsx"
wb = load_workbook(p, read_only=True, data_only=True)
for ws in wb.worksheets:
    headers = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    print(ws.title, ws.max_row, ws.max_column, headers)
wb.close()
PY
```

For standard validation workbooks, translate source columns `cn_name`, `cn_desc`, and `cn_notes`; export should populate adjacent `en_name`, `en_desc`, and `en_notes`. Do not translate `uuid`, `vid`, `created`, or already-English columns.

## Workflow
1. Confirm platform translation readiness before creating any project.
   Check `/api/health`, `/api/settings/model`, active Google Translate model config, required dictionaries (`专业名称翻译`, `software翻译`, `基础字符校对`, `validation校对`, `validation note replacement`), and `rule-resolve` preflight with `--google-smoke`. `/api/health` alone is not enough because the backend can be alive while Google Translate credentials, dictionaries, or server-side Google egress are unusable.

2. Confirm Google Translate is the active provider.
   Query model settings. If another provider is active, stop and ask the user to switch it in the platform. Do not call the model activation API silently, because that changes global platform behavior and affects manual UI translation.

3. Start the backend if needed.
   Start a local backend only for local API projects. For `http://192.168.10.89`, use the running remote backend and SSH for remote DB/script work; do not start a local backend as a proofreading fallback.

4. Back up the database.
   Example: `output/env-backup/translator_before_<project>_translate_validation_<date>.db`.

5. Create one translate project through the API.
   Use `source_type=xlsx`, `workflow=translate`, `target_lang=EN`, and one `source_col` list containing the indices for `cn_name`, `cn_desc`, and `cn_notes` when present. Attach the translation dictionaries and the combined replacement dictionary set (`基础字符校对`, `validation校对`, `validation note replacement`). `validation note replacement` must be scoped by backend `check_flow.py` so it only touches chunks whose Excel header is `cn_notes`.
   Before creating the project, verify `backend/services/check_flow.py` contains the `validation note replacement` note-only guard. If it does not, stop and ask for the platform/backend to be updated. Do not create separate `-main` / `-notes` projects as a workaround.

6. Translate all chunks.
   Call `/api/translate/<project_id>/translate-all` with `{"force": false}`. If a Google batch hits a transient auth error but fallback finishes with `errors: []`, continue.
   If `translate-all` returns `502`, times out, reports any `errors`, translates `0` chunks, or translates fewer chunks than the project created, stop immediately. Report the project ID(s) and do not run replacement, proofreading, or export.
   Delete the newly created platform project on translation failure unless `--keep-failed-project` is explicitly used for debugging.

7. Apply replacement dictionaries.
   Preferred path: ensure `backend/services/check_flow.py` skips `validation note replacement` unless header is `cn_notes`, then call `/api/proofread/<project_id>/batch-replace-all`.
   If service scoping is unavailable, run replacement in narrower code that excludes the note-only dictionary for non-note chunks.

8. Run validation proofreading.
   Use the existing skill/script on the same backend that owns the project. For 10.89, pass `--platform-ssh dx@192.168.10.89 --platform-root /opt/Aitrans` or set `AI_TRANSLATION_PLATFORM_SSH`; if password-based SSH is required, configure the shell wrapper explicitly, for example `AI_TRANSLATION_SSH_COMMAND='sshpass -e ssh -o StrictHostKeyChecking=no'`.
   ```bash
   ./backend/venv/bin/python -m py_compile tools/validation/check_and_fix.py
   ./backend/venv/bin/python tools/validation/check_and_fix.py <project_id> --repair
   ./backend/venv/bin/python tools/validation/check_and_fix.py <project_id>
   ```
   The final check must report zero issues, or only documented non-blocking false positives.

9. Manually sample high-risk rows.
   Always read representative title, description, and note chunks:
   - rows with CVE, disclosure dates, URLs, endpoint paths, versions, and reference blocks
   - AI application vulnerability rows
   - industrial-control / OT rows
   - long `Sequences` descriptions
   - protected sandbox notes
   - software names without exact `software翻译` dictionary hits
   If the user flags the note column, compare current `cn_notes` / `en_notes` against historical validation projects in `backend/instance/translator.db` before repairing. Use exact historical matches first; for near-identical note templates, adapt the historical wording narrowly instead of trusting a fresh machine translation.

10. Run independent delivery QA.
   Check at minimum:
   - every selected chunk has translation
   - no Chinese leftovers in `en_*`
   - CVEs, URLs, endpoint paths, versions, and ISO dates are preserved
   - `Disclosure date: YYYY-MM-DD` format is used
   - reference blocks are exactly multiline with one blank line before the marker: `<body text>\n\nPlease refer to:\nhttps://...`
   - no `_x000D_`, `<br>`, `<span translate="no">`, or flattened reference block remains
   - `cn_desc` body ends with terminal punctuation before any reference block
   - no ATT&CK replacement bleed in descriptions, such as title-case `Malware`, `Persistence`, `Obfuscation`, `Exfiltration`, `Reconnaissance`, `Lateral movement`, `Privilege Escalation`, `Policy`, or `Phishing Email`
   - `validation note replacement` outputs such as `Isolator` or `a Target Validator` are absent from `en_name` and `en_desc` unless source semantics explicitly require them outside note context
   - historical validation terminology rules are enforced: `攻击手法` / `attack techniques` -> `TTPs`, `工控安全` -> `OT Security`, and `#` in English title names becomes `-`
   - software names match the dictionary or the user-confirmed fallback table below
   - title fields (`en_name`) contain no standalone articles: `a`, `an`, or `the`
   - `Host Command Line` titles use capitalized base-form action verbs after the dash, not lowercase starts, `-ing`, or third-person `-s`

11. Export and verify the deliverable.
    Mark the project done, export with `format=xlsx&bilingual=true`, then open the output with `openpyxl` and verify expected `en_*` fill counts.

## Repair Guidance
- Fold repeatable safe fixes back into `tools/validation/check_and_fix.py`; keep rules narrow and deterministic.
- Protect URLs before substitutions and never rewrite inside URLs.
- Prefer exact phrase fixes for Google Translate artifacts and validation replacement bleed.
- Do not broaden validation classifications beyond the source Chinese:
  - `AI应用程序漏洞` remains `AI Application Vulnerability`
  - industrial-control / MES / SCADA rows remain industrial-control wording even when paths look web-like
  - generic `应用程序漏洞` must not become `Web Application Vulnerability` unless Chinese says `Web应用程序漏洞`
- Preserve prior validation glossary decisions: use `TTPs` for `攻击手法` in scenario descriptions, use `OT Security` for `工控安全`, and replace `#` with `-` in exported English title names.
- For `数据聚合` in validation titles, use `Data Aggregation`, not `Data Aggregator`.
- Do not add marketing, attribution, or business-value claims that are not present in the Chinese source. Remove invented trailing claims such as `helping enterprises achieve digital transformation and efficient management`.
- For product background sentences, preserve the Chinese information boundary. If the Chinese only says a product is for an industry, do not add launch parties, vendors, cities, or provinces. Example: `律师 e 通是一款律师行业协同办公云平台产品。` -> `Lawyer e-Pass is a collaborative office cloud platform product for the legal industry.` Do not append `jointly launched by China Telecom and Bizhi`.
- Preserve source sentence order in vulnerability descriptions: exploit/vulnerability impact and `Disclosure date: YYYY-MM-DD` should appear before general product background when the Chinese source has that order. Do not move product background ahead of vulnerability cause or impact sentences.
- In `cn_notes`, use `Isolator` for `受保护的沙盘` and `This rule requires Isolator to execute correctly.`
- For `cn_notes` OS/user-profile templates that mention `验证机器人`, keep the Validator concept attached to the endpoint/validator, not as a stray singular suffix after an OS name. Prefer forms such as `on Windows 10, Windows 11, Windows Server 2016, Windows Server 2019, and Windows Server 2022 Validators`.
- In `cn_notes`, follow the historical lowercase role-name style for execution recommendations: `administrator`, `user`, `regular user`, `root user`, `SYSTEM user`, and `non-administrator`. Do not apply title/name capitalization rules to these note roles.
- In `cn_name`, use `Protected Sandbox`, not `Isolator`.
- In `cn_name` / exported `en_name`, remove standalone title articles (`a`, `an`, `the`) anywhere in the title, including phrases such as `Discover the current user`, `Display a list`, and `using the tasklist command`.
- In `Host Command Line` titles, normalize action phrases to capitalized base form and avoid `-ing`: `Gather`, `Hijack`, `Hook`, `Load`, `Use`, `Write`, `Display`, `Collect`; prefer `via` over `using` in trailing method phrases when it avoids `-ing`.

## Software Name Fallbacks
Use the `software翻译` dictionary first. If a validation workbook contains a software/product name with no exact dictionary hit, check the row's `notes`/reference URL and apply user-confirmed fallbacks when applicable:

| Chinese/source name | Use |
|---|---|
| `郎速ERP` / `朗速ERP` | `LSERP` |
| `蓝凌EIS智慧协同平台` / `蓝凌 EIS` | `Landray EIS` |
| `ckan` | `ckan` |
| `鼎游票务系统` | `Ectrip Ticketing System` unless user explicitly chooses `Ectrip Cloud Ticketing System` |
| `深信服运维安全管理系统` / `深信服 运维安全管理系统` | `Sangfor OSM` |
| `short-video-maker` | `short-video-maker` |
| `NocoBase` | `NocoBase` |
| `泛微 E-cology10` | `Weaver e-cology10` |
| `WordPress Geo Mashup` | `WordPress Geo Mashup` |
| `Ech0` | `Ech0` |

When updating titles, also update the matching product mention in `cn_desc`. Preserve source semantics and do not invent an English name when the reference page only supports a conservative transliteration or project/repo name.

## Output
Place deliverables under `output/validation_runs/` unless the user requests another destination:

- `<input-stem>_validation_DELIVERABLE.xlsx`
- `<input-stem>_validation_DELIVERABLE_report.json`

The report should include project id, chunk counts, translated counts, header counts, sampled rows, blocking issues, and ATT&CK bleed hits. Do not call the file deliverable unless both the validation script and independent QA pass.
