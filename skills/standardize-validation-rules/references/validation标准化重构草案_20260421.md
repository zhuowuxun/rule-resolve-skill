# Validation 标准化重构索引

已将原先混合的执行草案拆分为两套独立文档，分别对应两种不同文件类型的标准化。

## 1. validation 主规则标准化

适用对象：

- `/Users/carmenz/Downloads/20260415134001-t_1.xlsx`

对应文档：

- `/Users/carmenz/Documents/tag管理系统/validation主规则标准化执行版_20260421.md`

说明：

- 只处理 `Actions / Sequences / Playbook` 的标题、描述、notes 与规则类型口径
- 不承载 mitigation 字典补数细节
- 只在需要引用 mitigation 结果时，说明“复用已确认的 mitigation 输出”

## 2. validation mitigation 标准化

适用对象：

- `/Users/carmenz/Downloads/20260415134001-mit_1.xlsx`
- `/Users/carmenz/Downloads/mitigation字典_0118.xlsx`

对应文档：

- `/Users/carmenz/Documents/tag管理系统/validation_mitigation标准化执行版_20260421.md`

说明：

- 只处理 mitigation 字典结构、remediation 补数、CVE 描述补充、reference 提取、标黄规则
- 不承载 `Actions / Sequences` 的命名与描述标准化细节

## 使用顺序

1. 先看 mitigation 文档，确定 `mit_1.xlsx` 的补数与字典映射规则
2. 再看主规则文档，处理 `t_1.xlsx` 的标准化
3. 当 `t_1.xlsx` 需要 remediation 时，仅复用已确认的 mitigation 结果，不在主规则文档里重新定义 remediation 模板
