---
name: rule-resolve
description: Meta workflow for rule deliverables. Use when the user asks to resolve, standardize, translate, proofread, or package detection / validation / mitigation rule Excel workbooks and wants one entry point that routes to the correct standardization or AI Translation Studio skill. Always preflight access to 10.89 before work, confirm the translation-platform API address if access or API health is unavailable, and support `help` / `帮助` for usage guidance.
---

# Rule Resolve

This is the top-level router for rule Excel work. It packages the three standardization skills and four translation/proofreading skills without merging their logic.

Bundled child skills live under `skills/` in this package. Prefer those bundled copies first so a downloaded `rule-resolve-skill` release is self-contained. Fall back to sibling installed skills only when a bundled child skill is missing.

## Start Message
After this skill is triggered and the route is chosen, send one short user-facing status line before substantial work:

```text
运行 <child-skill-name> skill 处理 <task-summary>。如果有不清楚的地方，可以输入 help 或 帮助 获取 skill 使用说明。
```

Examples:
- `运行 standardize-detection-rules skill 处理 detection 规则标准化。如果有不清楚的地方，可以输入 help 或 帮助 获取 skill 使用说明。`
- `运行 validation-translate-proofread skill 处理 validation 翻译校对。如果有不清楚的地方，可以输入 help 或 帮助 获取 skill 使用说明。`
- `运行 standardize-validation-mitigation skill 处理 mitigation 标准化。如果有不清楚的地方，可以输入 help 或 帮助 获取 skill 使用说明。`

Say this once at the start of the routed workflow, and again only if switching to another child skill.

## Help Response
If the user enters `help` or `帮助` while this skill is active, return a concise usage guide:

```text
rule-resolve 是规则处理总入口，会先检查 10.89，再按文件类型路由到对应 skill。

常用方式：
- detection 标准化：给 detection_rule_*.xlsx
- validation 主规则标准化：给 *_t_1.xlsx
- mitigation 标准化：给 *_mit_1.xlsx
- detection 翻译/校对：说明要翻译 detection 表或处理 de* 项目
- validation 翻译/校对：说明要翻译 validation 表或处理 va* 项目

如果要翻译/校对，我会确认 AI Translation Studio 地址；如果默认地址不通，需要你提供 API base URL。
```

Do not run destructive actions in response to `help` / `帮助`; only explain usage and wait for the next task.

## Mandatory Preflight
Before doing any rule work, run the bundled preflight:

```bash
python3 ~/.codex/skills/rule-resolve/scripts/preflight.py
```

For any translation or proofreading task that touches AI Translation Studio, require API health too:

```bash
python3 ~/.codex/skills/rule-resolve/scripts/preflight.py --require-translation-api --google-smoke
```

For translation tasks, pass the route-specific dictionaries so preflight checks more than `/api/health`.
`--google-smoke` creates a one-row temporary project, runs a real translation request, and deletes the project in a `finally` path. This is required because `/api/health`, model config, and dictionary checks can all pass while the 10.89 server still cannot reach Google:

```bash
# detection translation
python3 ~/.codex/skills/rule-resolve/scripts/preflight.py \
  --require-translation-api \
  --google-smoke \
  --required-dict 专业名称翻译 \
  --required-dict software翻译 \
  --required-dict 基础字符校对 \
  --required-dict detection校对

# validation translation
python3 ~/.codex/skills/rule-resolve/scripts/preflight.py \
  --require-translation-api \
  --google-smoke \
  --required-dict 专业名称翻译 \
  --required-dict software翻译 \
  --required-dict 基础字符校对 \
  --required-dict validation校对 \
  --required-dict "validation note replacement"
```

Interpretation:
- Default `10.89` host is `192.168.10.89`.
- If `host_reachable` is false, stop before platform-dependent work. Tell the user that `192.168.10.89` is unreachable from this environment and ask them to confirm the translation-platform address.
- If `host_reachable` is true but `translation_api_ready` is false for a translation/proofreading request, tell the user that `10.89` is reachable but AI Translation Studio translation readiness was not confirmed. Include whether `/api/health`, `/api/settings/model`, active Google Translate config, required dictionaries, and `google_smoke_check` passed, then ask for the correct API base URL or platform-side fix.
- If the user has already supplied an API address, pass it with `--api-base`.

Do not silently fall back to an unknown platform address.
Do not create translation projects when readiness is not confirmed. `/api/health` alone only means the Flask service is alive; it does not prove Google Translate credentials, model config, dictionaries, or the translate queue can run.
Do not silently change the platform-global active model. If the active model is not Google Translate, stop and ask the user to switch it in AI Translation Studio; only use a script option that activates Google after explicit user confirmation.

## Routing
After preflight, inspect the workbook/project shape and load exactly the child skill(s) needed.

Child skill resolution order:
1. bundled child skill: `~/.codex/skills/rule-resolve/skills/<child-skill>/SKILL.md`
2. sibling installed skill: `~/.codex/skills/<child-skill>/SKILL.md`
3. if neither exists, stop and report the missing child skill

When the bundled child skill contains scripts, resolve relative script paths from that bundled child skill directory, not from the sibling installed skill.

| User Intent / File Shape | Route To |
| --- | --- |
| Detection Chinese standardization; `name.1`, `desc`, `notes`; files like `detection_rule_*.xlsx` | `standardize-detection-rules` |
| Validation main-rule Chinese standardization; `Actions`, `Sequences`, optional `Email`; files like `*_t_1.xlsx` | `standardize-validation-rules` |
| Validation mitigation standardization; mitigation/remediation columns like `cn_notes`, `en_notes`, `cve`; files like `*_mit_1.xlsx` | `standardize-validation-mitigation` |
| Detection workbook translation through AI Translation Studio | `detection-translate` |
| Detection existing project proofreading; `de*` project already exists | `detection-proofread` |
| Validation workbook translation + proofread through AI Translation Studio | `validation-translate-proofread` |
| Validation existing project proofreading; `va*` project already exists | `validation-proofread` |

If the user asks for a full workflow, chain the appropriate standardization skill before translation:
- Detection full workflow: `standardize-detection-rules` then `detection-translate`.
- Validation main full workflow: `standardize-validation-rules` then `validation-translate-proofread`.
- Mitigation work stays in `standardize-validation-mitigation`; do not route mitigation work into validation main-rule or detection logic.

## Classification Checks
Inspect before routing:
- Detection sheets usually contain `Name`, `name.1`, `name_en`, `desc`, `desc_en`, `notes`, `notes_en`.
- Validation main workbooks usually contain `Actions` / `Sequences` / `Email` sheets and fields such as `cn_name`, `cn_desc`, `cn_notes`, `en_name`, `en_desc`, `en_notes`.
- Validation mitigation workbooks usually contain `cn_name`, `rule_type`, `os_scope`, `cve`, `cn_notes`, and `en_notes`, and may require yellow marking for fills or modified remediation content.
- Existing translation-platform projects should be handled by proofread skills, not by workbook-standardization skills.

If the shape is ambiguous, inspect headers and a few rows first. Do not guess across branches.

## Isolation Rules
- Never mix detection, validation main, and mitigation strategies.
- Do not use mitigation dictionary or remediation wording for validation main-rule `Actions` / `Sequences`.
- Do not use validation title prefixes for detection sheets unless the child detection skill says so.
- Do not copy from a manual comparison workbook as a generation source; use it only to learn repeatable differences.
- Keep URLs, paths, CVEs, versions, parameters, functions, and file extensions protected.
- Final workbooks must be Excel-openable: verify with `openpyxl` and `unzip -t`.
- Prefer concise output filenames such as `_standardized.xlsx`, `_translated.xlsx`, or `_proofread.xlsx`. Do not introduce `_DELIVERABLE` for standardization outputs.
- Validation translation must create exactly one AI Translation Studio project per input workbook. Do not split one workbook into separate `main` / `notes` projects; note-only replacement must be enforced by the validation translation child skill and backend replacement logic.

## How To Work
1. Run the mandatory preflight.
2. Inspect input workbook/project and choose the route.
3. Read the routed child skill's bundled `SKILL.md` from `skills/<child-skill>/` when present.
4. Use that child skill's bundled script when available.
5. Manually sample high-risk rows after script output.
6. Run Excel/platform QA gates from the child skill.
7. If user feedback reveals a repeatable rule, patch the routed child skill or script, not this router, unless the feedback is about routing/preflight.

## Stop And Ask
Stop and ask the user before continuing when:
- `192.168.10.89` is unreachable and the task needs platform, dictionary, tag-system, translation, or proofreading access.
- No AI Translation Studio API candidate passes `/api/health` for translation/proofreading work.
- AI Translation Studio `/api/health` passes but model config, Google Translate config, or required dictionary readiness fails.
- `translate-all` returns `502`, times out, reports errors, or translates `0` chunks after a project is created. Stop immediately, report the created project ID(s), and do not run replacement/proofreading/export.
- The workbook shape does not clearly match detection, validation main, or validation mitigation.
- The user provides a manual workbook but the generation source is unclear.
