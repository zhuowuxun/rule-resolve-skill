# Validation Mitigation 标准化执行版

适用文件：

- `/Users/carmenz/Downloads/20260415134001-mit_1.xlsx`
- `/Users/carmenz/Downloads/mitigation字典_0118.xlsx`

这份文档只负责 `mitigation` 标准化，不包含 `Actions / Sequences / Playbook` 的命名和描述标准化细节。

---

## 一、适用范围

适用于以下内容：

- mitigation 字典结构确认
- remediation 中英文模板补数
- `mit_1.xlsx` 的 CVE、描述、reference、notes 相关补充
- 自动补数标黄规则

不适用于以下内容：

- `t_1.xlsx` 的标题规范
- `Actions / Sequences / Playbook` 的中文表达统一

---

## 二、目标

把 `mit_1.xlsx` 视为 validation mitigation 数据表，用字典和 CVE 来源完成 remediation、描述和 reference 的标准化补充。

---

## 三、mitigation 字典定义

字典文件：

- `/Users/carmenz/Downloads/mitigation字典_0118.xlsx`

当前确认这是 remediation 模板字典，不是逐条规则明细表。

### 字典主结构

- `mitigation`：由一个或多个 ATT&CK mitigation 编号直接拼接形成的组合键，例如 `M1031`、`M1031M1037`
- `remidiation`：中文 remediation 模板
- `remidiation_en`：英文 remediation 模板

### 当前确认结果

- 字典约 612 条组合模板
- 同一 mitigation 组合键对应一条中英文 remediation
- 可直接作为 `mit_1.xlsx` 的 remediation 补数字典

---

## 四、字典匹配原则

### 1. 精确匹配优先

- 优先按完整 mitigation 组合键精确匹配
- 组合键按字典中的原始拼接形式匹配
- 不擅自拆分、不擅自排序、不擅自重排

### 2. 近似匹配作为候选

- 仅在精确匹配失败时，才允许进入近似匹配
- 近似匹配只能作为人工参考，不能直接视为最终结果
- 近似补数结果必须标黄

### 3. 未命中处理

- 无精确命中、无可靠近似候选时，保持待补状态
- 不强行生成 remediation 文本

---

## 五、remediation 模板规律

### 1. 基础句式

中文 remediation 模板整体结构稳定，通常由以下部分组成：

- 条件句：`如果某类安全产品对此攻击漏检`
- 短期建议：`塞讯验证短期建议：...`
- 中长期建议：`中长期建议：...`

### 2. 破坏性句式

部分模板会在句首加入：

- `此攻击手法是具有破坏性的，如果...`

### 3. 防护对象口径

模板中的防护对象主要包括：

- `网络安全产品`
- `终端安全产品`
- `终端/主机安全产品`
- `网络或主机安全产品`

规则：

- 下游补数时不能只看 mitigation 编号
- 还要保留字典已有的防护对象口径
- 不擅自把 `终端安全产品` 改写成 `网络安全产品`，或反向替换
- `主机命令行` 按 OS 规范句首防护对象：Windows 使用 `终端或主机安全产品`，Linux 使用 `主机安全产品`，macOS 使用 `终端安全产品`

---

## 六、mit_1.xlsx 标准化

### 当前列职责

推断列结构如下：

1. `uuid`
2. `tag_cn`
3. `cn_name`
4. `rule_type`
5. `os_scope`
6. `cve`
7. `cn_notes`
8. `en_notes`

### 1. 优先处理有 CVE 的规则

- 优先处理有 `CVE` 的行

### 2. 补充 CVE 内容

对有 `CVE` 的行：

- 用 `https://www.cve.org/CVERecord?id=CVE-xxxx-xxxx` 获取：
  - Description 英文放英文列
  - 中文翻译放中文列
  - Reference 链接

补充规则：

- 若 `cve.org` 没内容，再取 `https://www.tenable.com/cve/CVE-xxxx-xxxx`
- 若两边都没内容，则对应单元格留空并标黄

### 3. Reference 处理

- 从 reference 中提取真实 URL
- 正文后统一补：

```text

请参考：
链接1
链接2
...
```

- 最多保留前 5 条链接

### 4. remediation 补数

当 remediation 相关内容为空时：

- 先用 mitigation 组合键进行精确匹配
- 若精确命中，直接写入中英文 remediation
- 若未命中，再进入近似匹配
- 差距不能太大
- 近似回填后标黄
- 无可靠候选时保持待补

### 5. 硬件设备类系统判断

- 若规则针对的是硬件设备类系统，将“或主机安全产品”“通过优化WAF产品的检测规则实现防御或评估RSAP产品在贵司的适用性”“做好应用程序隔离。”删除
- 涉及类型归类或表达调整时，需要标黄供复核

---

## 七、必须标黄的情况

- mitigation 组合键未命中字典
- 仅命中近似组合
- `cve.org` 和 `tenable` 都未获取到有效内容
- 规则类型与 remediation 模板中的防护对象明显不一致
- 涉及硬件设备类系统判断

---

## 八、与 t_1.xlsx 的关系

- `t_1.xlsx` 涉及 remediation 时，应优先复用 `mit_1.xlsx` 已确认结果
- 不建议在 `t_1.xlsx` 中再次自由生成 remediation 文本
- 若出现同一 mitigation 组合但建议不一致，以 mitigation 字典及已确认的 `mit_1.xlsx` 为准
