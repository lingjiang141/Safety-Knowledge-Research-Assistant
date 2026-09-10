# 14 — 检索操作步骤时保留前提、代码与警告

Status: needs-triage
State: open
Type: AFK
Milestone: M1D
User stories: US25, US27, US28
Source: [PRD](../../../PRD.md)

## What to build

在操作指南和含代码的 Markdown 中查询某一步，返回该步骤及必要前提、代码和相邻警告的可定位证据；只分析代码，不执行。

## Acceptance criteria

- [ ] 支持编号步骤、前置条件、围栏代码块和警告段的结构关联；与说明性段落允许混合，不能仅按文件类型路由。
- [ ] 短代码块保持完整；超长代码块不得绕过 token 上限，按行拆分、保留连续范围及父块关系并提示不完整。
- [ ] 检索命中子片段后，在明确证据 token 预算内扩展必要父级或相邻块；每个不连续原文跨度单独引用。
- [ ] 前提未提供时不能补造；清楚区分原文引用与为阅读补充的标题上下文。
- [ ] 用 TDD 覆盖前提和步骤跨块、代码围栏含标题符号、警告在相邻段、预算不足和注入示例不执行。
- [ ] CLI 查询与回答证据路径可演示，记录资料/策略/模型版本；真实生成未运行则标记，不冒用模拟结果。

## Blocked by

- [13-structured-guides](13-structured-guides.md)

## Completion evidence

待实现。记录代码与语料版本、演示命令、测试结果、费用和失败案例；不可将设计写成已验证创新。

## Comments

用户已授权将文档类型适配加入主线。13/14 开始时直接使用 tdd；13 前执行已授权的架构检查，详见 docs/development-workflow.md。

