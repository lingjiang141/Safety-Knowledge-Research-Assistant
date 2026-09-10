# 07 — 冻结评测样本并保存可复查的基线报告

Status: needs-triage
State: open
Type: HITL
Milestone: M1
User stories: US18, US19, US21, US22
Source: [PRD](../../../PRD.md)

## What to build

把开发问题绑定实际语料证据，另建保留测试集，运行评测入口产生检索、引用和无答案行为报告。

## Acceptance criteria

- [ ] 人工核对可回答性、相关片段和等价证据规则；未导入 S01 时不能将相关题标为可回答。
- [ ] 开发集与保留集分开，保留答案不进入调参上下文；正式冻结记录 hash 和版本。
- [ ] Recall@5 按片段定义；重要结论含无引用结论均纳入支持情况检查，分别报告拒答与误拒答。
- [ ] 报告样本量、配置、延迟、费用、失败和未运行项；预算不够时保留付费评测待办，不虚构完整报告。
- [ ] 小样本规模可按余额安排；约 60 题是扩展建议。此任务只用开发集调试入口并保存基线，保留集最终执行留至最终评测。

## Blocked by

- [05-evidence-cases](05-evidence-cases.md)
- [06-version-sync](06-version-sync.md)
- [13-structured-guides](13-structured-guides.md)
- [14-procedures-code](14-procedures-code.md)
- [11-pdf](11-pdf.md)

## Completion evidence

完成时填写：代码版本、演示命令、测试结果、真实与模拟验证的区分、费用与未知预留、未解决问题。不得仅凭复选框关闭任务。

## Comments

尚未开始实现。遵守 PRD 的资料边界及 10 元总预算；AFK 表示常规实现无需逐项确认，不表示允许跳过密钥、预算或人工语义复核。



新主线要求：标注以原文跨度及条件完整性为准，之后才映射各切分结果；开发/保留数据划分要覆盖指南、步骤代码和文本报告。保留集延后到 12 使用。新增切分对照在 15 执行，混合检索排在其后。
