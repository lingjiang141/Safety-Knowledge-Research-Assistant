# 项目长期记忆：安全知识研究助手

## 关键约束（务必遵守）

- **禁止对共享 git 索引/对象库做临时操作**。想演示“修复前失败”时，用临时目录副本、
  `git worktree` 或直接在测试里断言旧行为；不要用 `git stash`、`git checkout --` 等
  触碰工作索引的命令。2026-09-10 曾因 `git stash push` 损坏对象库。
- 费用账本 `.data/budget.sqlite3` 跨知识库共用，10 元总预算，**不得重置或删除**。
  当前累计 0.108174 元、可用 9.891826 元、预留 0、blocked=false。
- 密钥只在本机环境变量/隐藏输入配置，不进代码、聊天或日志。无密钥时只跑本地测试。

## 流程约定

- 每次任务开始：读 HANDOFF.md → PRD.md → CONTEXT.md → docs/development-workflow.md → 对应 Issue → 最新证据。
- 技能时机：05 用 diagnose；06/13/14/11/10 用 tdd；04–06 后、13 前完整 improve-codebase-architecture。
- 先失败回归、再最小修复；模拟契约测试 ≠ 真实语义验证，不得混称。
- 分阶段提交；更新 HANDOFF；不移动/不伪造恢复标签。

## 已知架构痛点（06 后、13 前检查）

- `skra/cli.py` replay 按提示词版本逐次维护 coverage 校验版本集合，每加一个提示词版本都要手动同步，
  属“同一规则在多入口漂移”。候选局部重构点。

## 回答契约

- 回答状态由 `apply_coverage` 从 coverage 记录汇总，不信任模型顶层 status。
- 状态推导：`missing and answered` → partial；全部有结论无缺失 → grounded；
  无真实结论只有缺失 → insufficient。问题项只写 missing、无 claims 时**不计为已答**。
- **程序只校验显式结构，不校验语义**：若模型仍把 `claims:[0]`(原则结论) 关联到纯数量问题项，
  程序会如实推导 `partial`，不会也无法自动改写。纠正“用原则冒充数量答案”靠提示词（evidence-v3.3），
  必须用**定向真实复验**确认，本地测试通过 ≠ 语义已修复。
