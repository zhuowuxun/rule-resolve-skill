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
   - currently confirmed AI application products include `Blinko`, `LMDeploy`, and `Scramble`
   - for hardware/security-appliance style products such as 上网行为管理, 防火墙, 安全网关, 路由器, 交换机, VPN, load-balancing devices, or PA/Palo Alto/PAN-OS/GlobalProtect security products, use `应用程序漏洞 - ` instead of the `Web应用程序漏洞 - ` prefix
   - for industry/operation platforms that merely expose web endpoints, such as `Acrel EEMS 电力运维平台`, use `应用程序漏洞 - ` rather than `Web应用程序漏洞 - `
   - do not infer `AI应用程序漏洞 - ` only from an `/api` path; the product or historical standard must indicate an AI/LLM application
   - keep the application name before the first Chinese comma

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
   - preserve negation markers such as `未授权` / `未经身份验证`; if source text has the malformed bare phrase `经身份验证的攻击者/用户`, repair it to `未经身份验证的攻击者/用户` unless the source clearly says `经过身份验证`
   - after the opening sentence already says `针对 产品/入口 存在的漏洞类型`, remove an immediately repeated attack-method prefix like `产品/入口 接口存在漏洞类型，` and keep the remaining attacker condition / impact
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
