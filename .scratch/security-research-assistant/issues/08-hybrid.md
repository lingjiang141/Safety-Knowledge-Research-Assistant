# 08 — 用混合检索回答同一批问题并比较基线

Status: needs-triage
State: open
Type: AFK
Milestone: M2
User stories: US3, US9, US18, US21
Source: [PRD](../../../PRD.md)

## What to build

前置工作：04–06 完成后、开始本任务前直接使用 improve-codebase-architecture，按 docs/development-workflow.md 检查实际改动痛点；用户已授权，不要求为重构而重构。

在可用问答与评测路径增加 BM25 与 RRF，保持纯向量模式可选，对固定开发集比较效果。

## Acceptance criteria

- [ ] 候选、融合参数及排序可复查，融合与索引都过滤无效版本。
- [ ] 中文问题与英文词项错配需记录；如加入查询翻译或扩展，另做对照并记成本。
- [ ] 只改变主要检索因素，保留模型、语料、问题及生成设置；报告有利、无效及退化案例。
- [ ] 完成真实检索实验及必要回归测试；生成实验均受全局预算限制，不提前承诺提升。

## Blocked by

- [15-chunking-comparison](15-chunking-comparison.md)

## Completion evidence

完成时填写：代码版本、演示命令、测试结果、真实与模拟验证的区分、费用与未知预留、未解决问题。不得仅凭复选框关闭任务。

## Comments

尚未开始实现。遵守 PRD 的资料边界及 10 元总预算；AFK 表示常规实现无需逐项确认，不表示允许跳过密钥、预算或人工语义复核。
