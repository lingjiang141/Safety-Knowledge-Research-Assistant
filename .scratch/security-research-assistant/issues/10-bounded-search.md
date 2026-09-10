# 10 — 证据不足时最多补充检索两轮

Status: needs-triage
State: open
Type: AFK
Milestone: M3
User stories: US11, US12, US13, US17, US18, US19, US20
Source: [PRD](../../../PRD.md)

## What to build

执行要求：直接使用 tdd；若编排逻辑难以独立验证，先按 docs/development-workflow.md 使用 improve-codebase-architecture。用户已授权。

让助手根据已有检索结果决定是否在导入资料内补充搜索，最终输出答案与停止原因。

## Acceptance criteria

- [ ] 初次检索之外最多两轮；达到证据要求、没有新证据、超时、错误或预算不足时停止。
- [ ] 工具和参数由程序校验，不允许联网或写入；每个模型请求进入同一预算账本。
- [ ] 轨迹展示查询、候选、最终证据、外部状态与错误，不要求思维链。
- [ ] 测试无效循环、越权请求、无新证据和额度耗尽；基于开发集做开关对照，固定其他因素。

## Blocked by

- [08 — 用混合检索回答同一批问题并比较基线](08-hybrid.md)

## Completion evidence

完成时填写：代码版本、演示命令、测试结果、真实与模拟验证的区分、费用与未知预留、未解决问题。不得仅凭复选框关闭任务。

## Comments

尚未开始实现。遵守 PRD 的资料边界及 10 元总预算；AFK 表示常规实现无需逐项确认，不表示允许跳过密钥、预算或人工语义复核。
