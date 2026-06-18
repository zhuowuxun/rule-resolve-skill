---
name: standardize-validation-mitigation
description: Use when standardizing validation mitigation Excel workbooks such as `mit_1.xlsx`, especially when `cn_notes` and `en_notes` need mitigation-dictionary fill rules, CVE description/reference augmentation, hardware-product note cleanup, and comparison against a manual mitigation workbook.
---

# Standardize Validation Mitigation

Use this skill only for the mitigation branch of validation standardization.
It does not cover the full validation workflow for `Actions`, `Sequences`, or `Playbook` sheets.

## Scope
This skill is for workbooks shaped like the mitigation tables, for example:
- `20260415134001-mit_1.xlsx`
- `mitigation字典_0118.xlsx`
- optional manual comparison workbook such as `20260415134001-mit_2.xlsx`

This skill is not for:
- `t_1.xlsx`
- `Actions`
- `Sequences`
- full validation naming/description standardization

## Workflow
1. Inspect the workbook first.
   Confirm the mitigation sheet has the expected structure:
   - `uuid`
   - `tag_cn`
   - `cn_name`
   - `rule_type`
   - `os_scope`
   - `cve`
   - `cn_notes`
   - `en_notes`

2. Preserve existing remediation text unless it is empty.
   - Existing `cn_notes` / `en_notes` should be standardized in place.
   - The mitigation dictionary and approved standardized history corpus are used to fill empty remediation fields only.
   - If an approved standardized history workbook such as `action_mitigation260507.xlsx` is available, use it only as mitigation/remediation reference data:
     - Exact `uuid` or exact `name` matches may fill originally empty or `#N/A` `cn_notes` / `en_notes`.
     - Keep only the historical remediation body; do not copy old CVE descriptions or reference blocks from history.
     - Mark these history fills yellow and include them in `自动回填记录`.
     - Do not use historical `name` values to standardize `Actions / Sequences / Playbook` naming.
   - Prefer exact `tag_cn` dictionary matches; if no exact key exists, use the dictionary entry with the smallest MITRE-tag set difference and highest overlap as a fallback fill, only for empty or `#N/A` remediation fields.
   - For dictionary fills, do not rely on the mitigation tag alone. Re-check `cn_name`, `rule_type`, and `os_scope` before writing the final remediation text.
   - If a filled row is `命令与控制`, prefer the network/C&C remediation template over endpoint execution templates, even when the tag match is exact.
   - If a filled row is `恶意文件传输`, prefer the network malicious-file-transfer Hash template over endpoint execution templates.
   - If a filled row is `钓鱼邮件`, prefer the mail-security-gateway template; choose Hash wording for malicious files and URL wording for malicious links.
   - If a filled row is data leakage/DLP, prefer the `网络DLP产品` remediation template instead of generic network or host templates.
   - If a filled row is `容器安全`, prefer the `容器或主机安全产品` remediation template.
   - If a filled row is OT/ICS, prefer and preserve the OT safety-device remediation template; do not normalize OT safety wording back to generic network/host wording.
   - If a filled row is `AI应用程序漏洞`, preserve existing AI application security product wording such as `网络或主机或AI应用安全产品` / `network or server or AI application security products`; do not normalize it back to generic network/host wording.
   - For `主机命令行` rows, normalize the product-scope opening by OS:
     - Windows rows use `如果终端或主机安全产品对此攻击漏检` / `If the endpoint or server security products miss this attack`.
     - Linux rows use `如果主机安全产品对此攻击漏检` / `If the server security products miss this attack`.
     - macOS rows use `如果终端安全产品对此攻击漏检` / `If the endpoint security products miss this attack`.
   - For well-known vendors, cloud/SaaS products, and device/appliance products, prefer the historical vendor-contact short-term recommendation:
     - Chinese: `如果网络安全产品对此攻击漏检，塞讯验证短期建议：联络XXX告知漏洞。`
     - English: `If the network security products miss this attack, digiDations' short-term recommendation is: contact XXX to report the vulnerability.`
     - This applies to `Web应用程序漏洞`, `应用程序漏洞`, `AI应用程序漏洞`, and `WAF绕过` rows when the product/vendor is identifiable from `cn_name`; it can also be used for CVE rows, with CVE description/reference appended after the remediation paragraph.
     - Historical high-frequency examples include `泛微`, `用友`, `孚盟云`, `金蝶/金蝶云`, `百易云`, `智联云`, `致远互联`, `ServiceNow`, `Nextcloud`, `Cloudflare`, `海康威视`, and device/appliance vendors such as `D-Link`, `F5`, `Cisco`, `Pulse Secure`, `Ivanti`, `Fortinet`, `Buffalo`, `飞鱼星`, `腾达`, `网神SecGate`, `WIFISKY`, and `瑞斯康达`.
   - Infer OS from `os_scope` first, then from `cn_name` tokens such as `(Windows)`, `(Linux)`, `.exe`, `.dll`, `PowerShell`, `/etc/`, `LD_PRELOAD`, `syscall`, or `.MACHO`. Remove Windows-only wording such as `修改注册表` or `PowerShell` from Linux-related host-command remediations.
   - Mark only originally empty or `#N/A` `cn_notes` / `en_notes` cells that are filled from the dictionary or approved history corpus yellow, and add an `自动回填记录` sheet listing row, column, reason, old value, and new value.
   - Also mark cells yellow when the script changes cloud-system/cloud-software mitigation wording.
   - Also mark cells yellow when the script appends or rebuilds CVE description/reference blocks, even if the original remediation paragraph already existed.
   - Do not use a manual workbook as generation source.

3. For rows with CVE values, replace any old appended description/reference block.
   - Keep the remediation paragraph at the top.
   - Rebuild the trailing description/reference block from CVE sources.
   - Never preserve an existing CVE appendix just because a provided CVE cache is missing that CVE. The runner must fetch any missing CVE entries before augmentation, otherwise stale or cross-CVE descriptions can be retained.
   - If NVD/CVE official pages do not expose a usable description or reference list, try the Tenable CVE page (`https://www.tenable.com/cve/<CVE-ID>`) before falling back to a bare source URL. Tenable is useful for CVEs that are not yet visible or parseable on cve.org/NVD.
   - If all CVE sources return no reference list, still append the CVE detail/source URL as the fallback `请参考` / `Please refer to` reference; a row with a CVE must not lose its reference block because the external page has no parsed reference table.
   - In Chinese `cn_notes`, remove `nist.gov` links from appended `请参考` references. Keep `nist.gov` links in English `en_notes` `Please refer to` references.
   - When translating CVE version range wording, do not literalize `up to <version>` as `高达 <version>`; translate `A flaw/vulnerability has been found in <product> up to <version>.` as `<product> <version> 及之前版本存在漏洞。`
   - Append reference links in the fixed format:

   ```text

   请参考：
   https://...
   https://...
   ```

4. Apply mitigation-specific cleanup rules.
   - The destructive wording `此攻击手法是具有破坏性的` is only allowed in `受保护的沙盘` rows, but `受保护的沙盘` does not automatically mean destructive. Remove it from other rule types such as `命令与控制` or `恶意文件传输`.
   - Do not add or keep the destructive wording merely because the row is `受保护的沙盘`. If the sandbox rule name indicates cleanup/rollback-difficult but non-destructive behavior, remove the whole destructive/dangerous sentence head and start from `如果...`.
   - Non-destructive sandbox indicators include persistence/retention, C&C or C2 communication, beaconing, connecting/contacting C&C, scheduled tasks, registry/Run Key changes, Windows service/service persistence, auto-start/startup/logon items, log collection artifacts, and similar stay-resident or callback behavior. Typical Chinese/English tokens include `持久化`, `C&C`, `C2`, `信标`, `连接至`, `联络`, `通信`, `计划任务`, `任务计划`, `注册表`, `Run Key`, `采集日志`, `日志采集`, `自启动`, `启动项`, `登录项`, and `驻留`.
   - Keep destructive wording for sandbox rules whose names explicitly indicate destructive effects such as host/file destruction, stopping security protection, disabling data services, deleting shadow copies, wiping, encryption, ransomware, or destroy behavior.
   - When a sandbox row is filled from dictionary/history and the remediation starts directly with `如果...` / `If ...`, add the destructive sentence head only if the rule name has explicit destructive indicators such as stopping security protection, disabling data services, deleting shadow copies, wiping, encryption, ransomware, or destroy behavior. Do not add it merely for generic execution, loaders, file movement, or payload drop wording.
   - Treat `此攻击手法是具有危险性的` / `This attack method is dangerous` as old wording. For sandbox rows with destructive semantics, normalize it to `此攻击手法是具有破坏性的` / `This attack method is destructive`; otherwise remove the whole destructive/dangerous sentence head.
   - For hardware-style product groups currently identified by validated rules, remove:
     - `或主机安全产品`
     - `通过优化WAF产品的检测规则实现防御或评估RSAP产品在贵司的适用性`
     - `做好应用程序隔离。`
   - Current product groups with this cleanup rule:
     - `深信服运维安全管理系统`
     - `深信服下一代防火墙`
     - `安恒明御WEB应用防火墙`
     - `BMC FootPrints ITSM`
     - `F5 BIG-IP`
     - `HPE OneView`
     - `Cisco ASA 和 Firepower`
     - `Cisco vManage`
     - `Cisco Smart Licensing Utility`
     - `Cisco IOS 和 IOS XE 集群管理协议（CMP）`
     - `Pulse Secure SSL VPN`
     - `Ivanti Connect Secure VPN`
     - `Ivanti Endpoint Manager Mobile`
     - `Fortinet FortiMail`
     - `D-Link`
     - `D-Link Central WiFiManager 软件控制器`
     - `Buffalo 路由器`
     - `飞鱼星路由器`
     - `腾达 FH1201 路由器`
     - `网神SecGate 3600防火墙`
     - `WIFISKY-7层流控路由器`
     - `瑞斯康达 多业务智能网关`
   - Do not treat `WAF绕过` as a hardware-product rule; it should normally keep WAF/RSAP mitigation wording.
   - For cloud-style business systems or cloud software, use network-security-product wording and remove host/deployment-side wording:
     - Replace `网络或主机安全产品` with `网络安全产品`.
     - Remove WAF/RSAP applicability wording when the row is not explicitly a `WAF绕过` rule.
     - Remove `做好应用程序隔离。`.
     - For vendor/cloud products without CVE values, prefer the historical vendor-contact wording such as `联络孚盟云告知漏洞`.
   - For well-known vendors or device/appliance products, also prefer the vendor-contact wording even when the row has a CVE value; keep the CVE description/reference block after the remediation paragraph.
   - Preserve AI application security product wording for `AI应用程序漏洞`; do not treat `网络或主机或AI应用安全产品` as an old phrase.

5. Compare against a manual mitigation workbook only as evaluation.
   - Use the manual workbook to find rule gaps and wording improvements.
   - Do not copy its descriptions into the generated result.

6. Always audit the generated workbook against the source workbook before delivery.
   - Apart from the extra `自动回填记录` sheet, the output must keep the same sheet/cell values as the source except for explicitly approved mitigation changes.
   - Approved mitigation changes must be recorded in `自动回填记录` and highlighted yellow in the modified `cn_notes` / `en_notes` cells.
   - Only cells whose values actually changed may be highlighted or recorded; if a CVE fetch/append pass produces the same value as the source, leave the cell unhighlighted and do not add it to `自动回填记录`.
   - If any unrecorded cell value changes, treat the run as failed and inspect the report's `source_consistency.unexpected_diffs` before delivering.

## Script
Use the bundled runner for deterministic execution:

```bash
python3 ~/.codex/skills/standardize-validation-mitigation/scripts/run_validation_mitigation_standardization.py \
  --input /path/to/mit_1.xlsx \
  --dictionary /path/to/mitigation字典.xlsx \
  --history /path/to/action_mitigation260507.xlsx \
  --output /path/to/output.xlsx \
  --compare-manual /path/to/mit_2.xlsx
```

Outputs:
- standardized mitigation workbook
- JSON diff report when comparison is provided

## References
Use these only when needed:
- mitigation rules: `references/validation_mitigation标准化执行版_20260421.md`
- broader validation split index: `references/validation标准化重构草案_20260421.md`
- standardized history learning: `references/action_mitigation260507_history_learning.md`

## When To Stop And Ask
- The workbook is a full validation sheet rather than a mitigation sheet.
- The user wants `Actions` / `Sequences` standardization too.
- The mitigation sheet schema differs materially from the expected columns.
