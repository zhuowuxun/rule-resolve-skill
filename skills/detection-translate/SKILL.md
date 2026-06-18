---
name: detection-translate
description: Use when translating detection Excel workbooks through AI Translation Studio, especially `.xlsx` files with `name.1`, `desc`, and `notes` source columns that should be translated with Google Translate, detection dictionaries, replacement flow, and `tools/detection/check_and_fix.py`.
---

# Detection Translate

Use this skill when the user wants to translate a detection workbook through the local AI Translation Studio workflow, not by ad hoc sheet editing.

## Default Workflow
1. Confirm the local AI Translation Studio backend is the target environment.
   Default repo root:
   `~/Documents/翻译软件`
   Default API:
   `http://192.168.10.89`

   If the environment cannot access `192.168.10.89`, stop and ask the user to confirm the AI Translation Studio API base URL. Do not silently fall back to `127.0.0.1`.

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
   - activate the Google Translate model config
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
   - generate a small warning report for manual review

4. After the script finishes, manually review the warning report.
   Focus on `name.1`, `desc`, and `notes`.
   Treat Chinese path fragments, protected URLs, and vendor product names as source-aligned content unless the source clearly requires a translation.

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
- Do not skip the replacement flow before proofreading.
- Do not run replacement/proofreading/export if translation produced zero chunks, partial chunks, or any `errors`.
- Do not leave failed draft projects behind by default. If translation fails before replacement/export, delete the just-created project unless the user explicitly asks to keep it.
- Always back up `backend/instance/translator.db` before running detection proofreading repair.
- Never overwrite source columns in the final Excel; export bilingually unless the user explicitly asks for single-language overwrite.
- Keep URLs exact.
- Keep Chinese and English semantically aligned. Do not inject scope or platform qualifiers that are absent from the Chinese source.

## Manual Review Checklist
- Check for leftover Chinese in English fields that is not an intentional path or product token.
- Check for missing spaces after English commas.
- Check for glued attack phrases or lowercase `vulnerability` in `name.1`.
- Check for obviously broken machine phrasing in `desc`, especially missing articles, duplicated product names, or mangled identifiers.
- Check that `notes` still use the approved `digiDations recommends` template and preserve the vendor URL.
