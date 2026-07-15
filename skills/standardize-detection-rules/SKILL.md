---
name: standardize-detection-rules
description: Use when standardizing detection Excel deliverables that contain `name.1`, `desc`, and `notes` columns, especially Web vulnerability rule sheets that need the approved Chinese naming pattern, reordered description structure, preserved disclosure time, and the fixed 塞讯验证建议 note template.
---

# Standardize Detection Rules

Use this skill for detection rule spreadsheets, not validation sheets.
It is designed for `.xlsx` files shaped like the usual delivery tables with columns such as `Name`, `name.1`, `desc`, and `notes`.

## Workflow
1. Inspect the workbook first.
   Confirm the target sheet and verify the required columns exist:
   - `name.1`
   - `desc`
   - `notes`

2. Standardize `name.1`.
   Use this pattern by default:
   `Web应用程序漏洞 - 产品名，CVE，路径或入口，漏洞类型`

   Apply these rules:
   - convert the separator before the vulnerability phrase into Chinese commas
   - move `CVE-xxxx-xxxx` forward so it appears immediately after the product name
   - remove leftover wrapping parentheses after extracting the CVE
   - keep the default prefix `Web应用程序漏洞 - `
   - for AI / LLM application products, use `AI应用程序漏洞 - ` instead of `Web应用程序漏洞 - `
   - currently confirmed AI application products include `9Router`, `Blinko`, `Crawl4AI`, `Gradio`, `Langflow`, `LMDeploy`, and `Scramble`
   - for hardware/security-appliance style products such as 上网行为管理, 防火墙, 安全网关, 路由器, 交换机, VPN, load-balancing devices, or PA/Palo Alto/PAN-OS/GlobalProtect security products, use `应用程序漏洞 - ` instead of the `Web应用程序漏洞 - ` prefix
   - for industry/operation platforms that merely expose web endpoints, such as `Acrel EEMS 电力运维平台`, use `应用程序漏洞 - ` rather than `Web应用程序漏洞 - `
   - do not infer `AI应用程序漏洞 - ` only from an `/api` path; the product or historical standard must indicate an AI/LLM application
   - keep the application name before the first Chinese comma
   - if `desc` contains a more complete path that clearly expands the title path, use the complete `desc` path in `name.1` as well, for example title `/database` plus desc `/api/settings/database` becomes `/api/settings/database`
   - preserve parameterized paths from `desc`, including colon parameters such as `/workflow/docs/:componentName`
   - treat action-style entry names in `desc`, such as `qcld_wb_chatbot_conversation_save AJAX Action`, as valid rule entry points when they expand a shorter title token
   - when `desc` contains a more precise vulnerability family than the title, promote it into `name.1`, for example `ClickHouse SQL 注入漏洞` should not be reduced to generic `SQL注入漏洞`
   - if the title path and `desc` path are completely unrelated, do not force-replace the title path; highlight the `name.1` and `desc` cells yellow for manual review

3. Standardize `desc`.
   The description should follow this order:
   - opening sentence: `此检测规则还原了针对……的利用尝试`
   - attack-method explanation in the middle
   - `披露时间` preserved
   - application description last

   Guardrails:
   - do not remove `披露时间`
   - do not invent exploit details that are absent from the source
   - preserve technical path and filename casing inside the attack-method text, such as `/api/...` and `ModuleGridSource.aspx`
   - preserve authentication semantics exactly: `经过身份认证/验证`, `经过认证`, `经身份认证/验证`, `经认证`, `认证用户`, `已获得登录权限`, `未授权`, `未认证`, `未经认证`, and `未经身份认证/验证` must match the source row; do not guess or add/remove `未`
   - after the opening sentence already says `针对 产品/入口 存在的漏洞类型`, remove an immediately repeated attack-method prefix like `产品/入口 接口存在漏洞类型，` and keep the remaining attacker condition / impact
   - when a repeated attack-method prefix contains a more complete path than the original title endpoint, first synchronize the full path into `name.1` and the opening sentence, then remove the repeated `完整路径 存在漏洞类型，` prefix from the attack-method text
   - for version-qualified duplicate prefixes such as `产品 1.2.3 及之前版本通过 入口 存在某漏洞。由于...` or `产品 1.2.3 之前版本的 入口 存在某漏洞，参数...`, keep the version context but remove the repeated vulnerability prefix
   - if a first clause restates `产品/入口存在某漏洞，` but the rest of the sentence contains the actual attacker condition or impact, drop only that repeated first clause
   - you may tighten wording for attack-method phrasing
   - if a historical standardized software description exists, reuse or shorten toward that wording
   - keep the application description at the end
   - treat product-introduction phrasing such as `自主研发`, `是…一款`, `核心价值`, `核心使命`, `不仅具有`, and `专业产品` as software description, not attack-method explanation
   - trim marketing/praise wording from software descriptions, such as `功能全面`, `性能稳定`, `扩展性强`, `核心竞争力`, `护城河`, and `开放、互联、融合、智能`; keep only neutral product purpose or category
   - remove political, policy, or official-planning endorsement wording from software descriptions, such as `依据国家...规范`, `国家“十三五”`, `十三五`, and `经过充分的客户需求调研`; keep only neutral product-purpose wording

4. Standardize `notes`.
   Rewrite vendor guidance into this exact three-line structure:

   ```text
   塞讯验证建议：
   请关注厂商主页获取更新：
   https://example.com/
   ```

   Preserve the URL exactly.

5. Prefer a slim output.
   Unless the user explicitly asks for comparison columns, keep the original workbook shape and overwrite only the target fields in the output copy.

6. Compare the standardized workbook against the source workbook before final response.
   - Align rows by stable IDs when present and otherwise by row order; compare `name.1`, `desc`, and `notes`.
   - Verify protected evidence is preserved: CVEs, URLs, URI paths, filenames, extensions, disclosure dates, versions, vendor links, product names, and authentication markers such as `经过身份认证/验证`, `经过认证`, `经身份认证/验证`, `经认证`, `未授权`, `未认证`, `未经认证`, and `未经身份认证/验证`.
   - Treat any authenticated/unauthenticated state mismatch, loss of `未` / `未经`, endpoint/path tails, `披露时间`, reference/vendor URLs, or technical impact text as a failed run.
   - Confirm rows with full paths in `desc` also use those full paths in `name.1`; if `desc` and `name.1` paths are unrelated, confirm the yellow highlight is present.
   - Approved intentional differences include CVE extraction into the title, prefix correction, moving/shortening software description to the end, duplicate vulnerability wording removal, city/province cleanup, and promotional/political wording cleanup.
   - If the compare finds real content loss, patch the script/rules, regenerate the workbook, rerun Excel QA, and rerun the source compare before delivery.

## Script
Use the bundled script for deterministic execution:

```bash
python3 ~/.codex/skills/standardize-detection-rules/scripts/standardize_detection_excel.py \
  --input /path/to/input.xlsx \
  --output /path/to/output.xlsx
```

Useful options:
- `--sheet Sheet1`
- `--historical-json /path/to/history.json`

## Expected Inputs
- Detection Excel workbook (`.xlsx`)
- Optional historical JSON export that contains prior standardized `name` / `desc` pairs

## Expected Output
- A new `.xlsx` file with standardized `name.1`, `desc`, and `notes`
- Same core columns as the input unless the user asks for extra audit columns

## When To Stop And Ask
- The workbook is not a detection sheet
- Required columns are missing
- The user wants a different naming prefix than `Web应用程序漏洞 - `
- There are multiple plausible product-name splits and the wrong split would be costly
