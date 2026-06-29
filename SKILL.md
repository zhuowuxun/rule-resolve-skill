---
name: rule-resolve
description: Meta workflow for rule deliverables. Use when the user asks to resolve, standardize, translate, proofread, or package detection / validation / mitigation rule Excel workbooks and wants one entry point that routes to the correct standardization or AI Translation Studio skill. Always preflight access to 10.89 before work, confirm the translation-platform API address if access or API health is unavailable, optionally configure this Mac as a Google API proxy for remote 10.89 translation after user confirmation, and support `help` / `帮助` for usage guidance.
---

# Rule Resolve

This is the top-level router for rule Excel work. It packages the three standardization skills and four translation/proofreading skills without merging their logic.

Bundled child skills live under `skills/` in this package. Prefer those bundled copies first so a downloaded `rule-resolve-skill` release is self-contained. Fall back to sibling standalone skills only when a bundled child skill is missing.

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
如果 10.89 能打开但 Google Translate smoke check 不通过，我会问你是否用本机做代理访问 Google API；确认后我会配置代理并重新检查。
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
- If `host_reachable` is true but `translation_api_ready` is false for a translation/proofreading request, tell the user that `10.89` is reachable but AI Translation Studio translation readiness was not confirmed. Include whether `/api/health`, `/api/settings/model`, active Google Translate config, required dictionaries, and `google_smoke_check` passed. If only the Google smoke / translate request appears blocked while health, model, and dictionaries are ready, ask whether to use this Mac as a Google API proxy for 10.89 before asking for another API base.
- If the user has already supplied an API address, pass it with `--api-base`.

Do not silently fall back to an unknown platform address.
Do not create translation projects when readiness is not confirmed. `/api/health` alone only means the Flask service is alive; it does not prove Google Translate credentials, model config, dictionaries, or the translate queue can run.
Do not silently change the platform-global active model. If the active model is not Google Translate, stop and ask the user to switch it in AI Translation Studio; only use a script option that activates Google after explicit user confirmation.
## Platform Ownership Rule
Bind every AI Translation Studio task to exactly one platform before creating, proofreading, repairing, exporting, or inspecting a project.

- If a project is created or found through `http://192.168.10.89`, the 10.89 backend/database owns the whole lifecycle: translation, replacement, proofreading, DB backup, `check_and_fix.py` repair, status changes, and export.
- Do not start or use a local backend such as `127.0.0.1:5002` to proofread, repair, export, or inspect chunks for a remote 10.89 project ID. Numeric project IDs can collide across databases.
- Local backend/DB tooling may be used only when the selected API base is local, or when the user explicitly says to use the local backend for that project.
- For any non-local API base, DB backups and `check_and_fix.py` proofreading must run on that same platform via SSH (`--platform-ssh` or `AI_TRANSLATION_PLATFORM_SSH`). If SSH or remote script access is unavailable, stop and report the blocker instead of falling back to local DB tools.
- This same-backend rule applies to proofread-only routes (`validation-proofread`, `detection-proofread`) as well as full translate-and-proofread routes.

## Optional 10.89 Google API Proxy
This is a rule-resolve-level configuration for translation/proofreading routes. Use it for detection and validation translation when the remote platform is `http://192.168.10.89` and Google Translate egress from 10.89 is unreliable.

Rules:
- Ask the user before enabling it: `10.89 的 Google smoke 没过，要不要用本机做代理访问 Google API？`
- If the user has already explicitly answered yes in the current request, treat that as confirmation and configure the proxy immediately; do not ask the same question again.
- Do not enable it for pure standardization work.
- Do not assume AI Translation Studio's model `base_url` field affects `google_translate`; current Google Translate code uses Python `requests` and honors `HTTP_PROXY` / `HTTPS_PROXY`.
- Use `scripts/google_api_proxy.py` from this rule-resolve skill, not a child skill copy.
- After enabling the proxy, rerun preflight with the same route-specific required dictionaries and `--google-smoke`.
- Before production translation, compare local and remote dictionary counts when possible. If `software翻译` differs, synchronize dictionaries first or expect software/product names to differ.

Setup:

```bash
# From ~/Documents/翻译软件
./backend/venv/bin/python ~/.codex/skills/rule-resolve/scripts/google_api_proxy.py lan-ip --all

screen -dmS google_api_proxy bash -lc './backend/venv/bin/python ~/.codex/skills/rule-resolve/scripts/google_api_proxy.py serve --bind 0.0.0.0 --port 8899 > /tmp/google_api_proxy.log 2>&1'

export AI_TRANSLATION_SSH_COMMAND='sshpass -e ssh -o StrictHostKeyChecking=no'
export SSHPASS='REMOTE_PASSWORD'

# Prefer an SSH reverse tunnel for 10.89. Direct LAN access from 10.89 to the Mac can fail across VPN/subnets.
./backend/venv/bin/python ~/.codex/skills/rule-resolve/scripts/google_api_proxy.py remote-tunnel \
  --remote dx@192.168.10.89 \
  --remote-port 18899 \
  --local-port 8899

./backend/venv/bin/python ~/.codex/skills/rule-resolve/scripts/google_api_proxy.py remote-probe \
  --remote dx@192.168.10.89 \
  --proxy-url http://127.0.0.1:18899

10.89 currently runs the backend as systemd service `ai_translator_backend.service` with gunicorn on port 5001. Configure that service with a systemd override:

./backend/venv/bin/python ~/.codex/skills/rule-resolve/scripts/google_api_proxy.py remote-enable-systemd \
  --remote dx@192.168.10.89 \
  --proxy-url http://127.0.0.1:18899
```

Teardown:

```bash
./backend/venv/bin/python ~/.codex/skills/rule-resolve/scripts/google_api_proxy.py remote-disable-systemd --remote dx@192.168.10.89
pkill -f '127.0.0.1:18899:127.0.0.1:8899' || true
screen -S google_api_proxy -X quit
```

If SSH fails, do not claim the proxy is configured. Report that local proxy startup may be ready but remote backend restart did not complete.
If `remote-probe` via `http://LOCAL_LAN_IP:8899` fails but SSH works, use `remote-tunnel` and proxy URL `http://127.0.0.1:18899`.

## Routing
After preflight, inspect the workbook/project shape and load exactly the child skill(s) needed.

Child skill resolution order:
1. bundled child skill: `~/.codex/skills/rule-resolve/skills/<child-skill>/SKILL.md`
2. sibling standalone skill: `~/.codex/skills/<child-skill>-standalone/SKILL.md`
3. legacy sibling skill, if still present: `~/.codex/skills/<child-skill>/SKILL.md`
4. if none exists, stop and report the missing child skill

When the bundled child skill contains scripts, resolve relative script paths from that bundled child skill directory, not from the sibling standalone skill.

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
2. If translation readiness fails only because Google smoke / egress appears blocked on remote 10.89, ask whether to enable the local Google API proxy. If the user already confirmed in the same request, configure it and rerun preflight immediately.
3. Bind the task to its owner API base (`local` or `10.89`) and keep that owner for translation, proofreading, repair, export, and DB inspection.
4. Inspect input workbook/project and choose the route.
5. Read the routed child skill's bundled `SKILL.md` from `skills/<child-skill>/` when present.
6. Use that child skill's bundled script when available.
7. Manually sample high-risk rows after script output.
8. Run Excel/platform QA gates from the child skill.
9. If user feedback reveals a repeatable rule, patch the routed child skill or script, not this router, unless the feedback is about routing/preflight or remote platform configuration.

## Stop And Ask
Stop and ask the user before continuing when:
- `192.168.10.89` is unreachable and the task needs platform, dictionary, tag-system, translation, or proofreading access.
- No AI Translation Studio API candidate passes `/api/health` for translation/proofreading work.
- AI Translation Studio `/api/health` passes but model config, Google Translate config, or required dictionary readiness fails.
- `translate-all` returns `502`, times out, reports errors, or translates `0` chunks after a project is created. Stop immediately, report the created project ID(s), and do not run replacement/proofreading/export.
- The task is bound to a remote platform but SSH or remote script access needed for DB backup, `check_and_fix.py`, or export is unavailable.
- The workbook shape does not clearly match detection, validation main, or validation mitigation.
- The user provides a manual workbook but the generation source is unclear.
