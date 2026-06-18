---
name: detection-translate
description: Use when translating detection Excel workbooks through the AI Translation Studio repo, especially `.xlsx` files with `name.1`, `desc`, and `notes` source columns that should be translated with Google Translate, the detection dictionaries, replacement flow, and `/Users/carmenz/Documents/翻译软件/tools/detection/check_and_fix.py`.
---

# Detection Translate

Use this skill when the user wants to translate a detection workbook through the local AI Translation Studio workflow, not by ad hoc sheet editing.

## Default Workflow
1. Confirm the local AI Translation Studio backend is the target environment.
   Default repo root:
   `/Users/carmenz/Documents/翻译软件`
   Default API:
   `http://127.0.0.1:5002`

2. Use the bundled script for the end-to-end flow:
   - activate the Google Translate model config
   - inspect the workbook and detect the detection source columns
   - create a real platform project
   - attach the standard detection dictionaries
   - run translate-all
   - run batch replacement
   - back up the live database
   - run the detection proofreading script with repair
   - verify the proofreading script reports zero issues
   - export a bilingual `.xlsx`
   - generate a small warning report for manual review

3. After the script finishes, manually review the warning report.
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
/Users/carmenz/Documents/翻译软件/backend/venv/bin/python \
  ~/.codex/skills/detection-translate/scripts/run_detection_translate.py \
  --input /absolute/path/to/source.xlsx \
  --project-name de0506 \
  --output /absolute/path/to/output.xlsx
```

Useful options:
- `--api-base http://127.0.0.1:5002`
- `--repo-root /Users/carmenz/Documents/翻译软件`
- `--manual-review-limit 20`
- `--skip-export`

## Guardrails
- Resolve the active Google Translate config by provider name, not by hard-coded config ID.
- Resolve dictionary IDs by dictionary names, not by hard-coded IDs.
- For software and product names, exact dictionary matches outrank manual language judgment.
- If a Chinese software name has no exact approved dictionary entry, do not normalize it to a more “natural” English product name. Keep it for manual review or dictionary completion instead.
- Do not skip the replacement flow before proofreading.
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
