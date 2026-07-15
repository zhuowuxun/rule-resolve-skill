---
name: detection-translate
description: Use when translating detection Excel workbooks through AI Translation Studio, especially `.xlsx` files with `name.1`, `desc`, and `notes` source columns that should be translated with Google Translate, detection dictionaries, replacement flow, and `tools/detection/check_and_fix.py`.
---

# Detection Translate

Use this skill when the user wants to translate a detection workbook through AI Translation Studio, not by ad hoc sheet editing.

## Default Workflow
1. Confirm the AI Translation Studio backend that will own the project.
   Default repo root:
   `~/Documents/翻译软件`
   Default API:
   `http://192.168.10.89`

   If the environment cannot access `192.168.10.89`, stop and ask the user to confirm the AI Translation Studio API base URL. Do not silently fall back to `127.0.0.1`.
   Keep the same owner backend for translation, replacement, proofreading, DB backup, `check_and_fix.py`, status changes, and export. Use local backend/DB tooling only for local API projects or when the user explicitly says to use the local backend.

2. Before creating any project, verify translation readiness:
   - `/api/health` responds
   - `/api/settings/model` responds
   - a `google_translate` model config exists and is already the active platform model
   - required dictionaries exist: `专业名称翻译`, `software翻译`, `基础字符校对`, `detection校对`
   - `rule-resolve` preflight with `--google-smoke` passes, proving the 10.89 server can actually reach Google Translate/OAuth

   `/api/health` alone is not enough. A healthy Flask service can still have broken Google Translate credentials or dictionaries.
   Model and dictionary readiness alone is also not enough; if Google egress is blocked, platform UI translation will hang or fail even though config checks pass.
   Do not change the platform-global active model silently. If Google Translate is not active, stop and ask the user to switch it in the platform, or use `--activate-google` only after explicit confirmation.

3. Use the bundled script for the end-to-end flow:
   - inspect the workbook and detect the detection source columns
   - create a real platform project
   - attach the standard detection dictionaries
   - run translate-all
   - stop immediately if `translate-all` returns `502`, times out, reports errors, or translates fewer chunks than the project created
   - delete the newly created platform project on translation failure unless `--keep-failed-project` is explicitly used
   - run batch replacement
   - back up the live database
   - run the detection proofreading script with repair
   - verify the proofreading script reports zero issues
   - export a bilingual `.xlsx`
   - run export-side product-name proofreading for rows whose `notes` contain vendor/homepage URLs
   - run export-side path proofreading so English fields preserve exact source paths and path casing from `name.1` / `desc`
   - generate a small warning report for manual review

   When `--api-base` points to a non-local platform such as `http://192.168.10.89`, all database-side operations must run on that platform, not on the user's local `~/Documents/翻译软件` database. Pass `--platform-ssh` so DB backup and `tools/detection/check_and_fix.py` execute on the remote platform. If `--platform-ssh` is missing for a non-local API, the script must stop instead of repairing a local project with the same numeric ID.

4. After the script finishes, manually review the warning report.
   Focus on `name.1`, `desc`, and `notes`.
   Treat Chinese path fragments, protected URLs, and vendor product names as source-aligned content unless the source clearly requires a translation.
   For software/product names that do not have an exact dictionary entry, use the vendor URL in `notes` and the software description in `desc` as evidence for proofreading. Do not leave literal machine translations when the URL clearly reveals the product/vendor spelling, such as `fangmail.net -> FangMail`, `macrowing.com/XDMS -> Macrowing`, or `crawl4ai -> Crawl4AI`.
   If translation changes a protected path or code identifier, such as replacing vendor tokens inside `/servlet/...` or splitting `/gradio_api/proxy`, restore the exact path from the Chinese source columns.

## Standard Detection Settings
- Translation dictionaries:
  - `专业名称翻译`
  - `software翻译`
- Replacement dictionaries:
  - `基础字符校对`
  - `detection校对`
- Preferred source headers:
  - `name.1`
  - `desc`
  - `notes`
- Preferred export mode:
  bilingual `.xlsx`, so reserved English columns are reused instead of creating extra output columns.

## Script
Run the bundled script with the backend venv Python:

```bash
~/Documents/翻译软件/backend/venv/bin/python \
  ~/.codex/skills/detection-translate/scripts/run_detection_translate.py \
  --input /absolute/path/to/source.xlsx \
  --project-name de0506 \
  --output /absolute/path/to/output.xlsx
```

Useful options:
- `--api-base http://192.168.10.89`
- `--api-base http://127.0.0.1:5002` only when the user confirms a local backend
- `--repo-root ~/Documents/翻译软件`
- `--platform-ssh dx@192.168.10.89` when using the 10.89 platform API
- `--platform-root /opt/Aitrans`
- `--ssh-command "sshpass -e ssh -o StrictHostKeyChecking=no"` when a password-based SSH wrapper is explicitly configured in the shell
- `--keep-failed-project` only when the failed draft project should be preserved for debugging
- `--activate-google` only after explicit user confirmation because it changes platform-global model settings
- `--manual-review-limit 20`
- `--skip-export`

## Guardrails
- Resolve the active Google Translate config by provider name, not by hard-coded config ID.
- Do not auto-activate Google Translate. Platform model activation is global and affects manual UI translation too.
- Resolve dictionary IDs by dictionary names, not by hard-coded IDs.
- For software and product names, exact dictionary matches outrank manual language judgment.
- If a Chinese software name has no exact approved dictionary entry, do not normalize it to a more “natural” English product name. Keep it for manual review or dictionary completion instead.
- Exception: when `notes` contains a vendor/homepage URL or the Chinese description contains an official English alias, use that URL/alias to proofread the exported English product name. This is evidence-backed proofreading, not free normalization.
- Do not skip the replacement flow before proofreading.
- Do not run replacement/proofreading/export if translation produced zero chunks, partial chunks, or any `errors`.
- Do not leave failed draft projects behind by default. If translation fails before replacement/export, delete the just-created project unless the user explicitly asks to keep it.
- Always back up `backend/instance/translator.db` before running detection proofreading repair.
- For remote platform API bases, back up the remote platform DB and run the remote platform `check_and_fix.py`; never run local DB tools against a remote project ID.
- Never overwrite source columns in the final Excel; export bilingually unless the user explicitly asks for single-language overwrite.
- Keep URLs exact.
- Keep URI paths and code identifiers exact, including case and vendor tokens. Do not translate path fragments.
- Keep Chinese and English semantically aligned. Do not inject scope or platform qualifiers that are absent from the Chinese source.

## Manual Review Checklist
- Check for leftover Chinese in English fields that is not an intentional path or product token.
- Check for missing spaces after English commas.
- Check for glued attack phrases or lowercase `vulnerability` in `name.1`.
- Check rows with vendor URLs but no exact product dictionary entry; product names must align with the official URL/alias rather than a literal machine translation.
- Check paths in `name_en` / `desc_en` against the Chinese source path; translated paths are defects.
- Check for obviously broken machine phrasing in `desc`, especially missing articles, duplicated product names, or mangled identifiers.
- Check that `notes` still use the approved `digiDations recommends` template and preserve the vendor URL.
