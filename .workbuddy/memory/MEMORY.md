# 项目长期记忆：安全知识研究助手

## 关键约束（务必遵守）

- **禁止对共享 git 索引/对象库做临时操作**。想演示“修复前失败”时，用临时目录副本、
  `git worktree` 或直接在测试里断言旧行为；不要用 `git stash`、`git checkout --` 等
  触碰工作索引的命令。2026-09-10 曾因 `git stash push` 损坏对象库（11 个历史提交被删，
  已从工作区重建基提交 a08ac81）。
- 费用账本 `.data/budget.sqlite3` 跨知识库共用，10 元总预算，**不得重置或删除**。
  当前累计 **0.344997** 元、可用 **9.655003** 元、预留 0、blocked=false（保守记账，非平台实际账单）。
- 密钥只在本机环境变量/隐藏输入配置，不进代码、聊天或日志。无密钥时只跑本地测试。
- **导入任何资料前先核查页脚许可 + 使用条款**；公开可读 ≠ 可全文再发布（S01 Anthropic 即因此不能导入）。

## 流程约定

- 每次任务开始：读 HANDOFF.md → PRD.md → CONTEXT.md → docs/development-workflow.md → 对应 Issue → 最新证据。
- 技能时机：05 用 diagnose；06/13/14/11/10 用 tdd；04–06 后、13 前完整 improve-codebase-architecture。
- 先失败回归、再最小修复；模拟契约测试 ≠ 真实语义验证，不得混称；**结构状态命中 ≠ 语义通过**。
- 分阶段提交；更新 HANDOFF；不移动/不伪造恢复标签。用户提到的工作分支 `codex/issue05-continue`
  与标签 `checkpoint-issue05-before-handoff` 本机从未存在。

## 当前进度快照（2026-09-10）

- Issue：01/02/04 done；**03 blocked（用户已指示进入三类端到端验收收尾）**；**05 in-progress**；06–15 open。
- 主线：**05 → 06 → 架构检查 → 13 → 14 → 11 → 07 → 15 → 08 → 10 → 12**；03 欠项并行补齐。不进入 06。
- 当前提示词 **evidence-v3.5**，输出上限 **1500** token（常量 `OUTPUT_TOKEN_LIMIT`），单次最大预留 3.159228 元。
- 本地 **31 tests 通过**。
- 05 两条验收路径：
  1. 受控场景 `check_boundaries.py`：v3.3 下十题全部有符合要求的观察（非检索、非准确率）。
  2. 原始资料题 `check_acceptance.py`：v3.4 全跑→修 2 生成缺陷→v3.5 定向重跑 Q01/Q07/Q09 确认修复生效。
     欠项：**Q01 已换题待跑**（新题「提示注入与越狱有什么区别？」）、**Q04/Q06 检索未命中**
     （所需片段向量排序第 7，20 行块过粗——记入 13/14/11 结构适配，不改固定检索器）。
- 03 收尾可复用：十题中 Q02/Q05（有据）/Q08（无据）/Q09（部分有据）对应三类；
  尚缺新版 Q01 + v3.5 全批重跑、用户最终语义验收、平台账单核对。

## 已知架构痛点（06 后、13 前检查）

- `skra/cli.py` replay 按提示词版本逐次维护 coverage 校验版本集合（现已到 v3.5），
  每加一个提示词版本都要手动同步，属“同一规则在多入口漂移”。候选局部重构点。
- 切分粒度过粗（`heading-lines-v1:20`）会稀释定义段，导致检索未命中（Q04/Q06 实证）。

## 回答契约

- 回答状态由 `apply_coverage` 从 coverage 记录汇总，不信任模型顶层 status。
- 状态推导：`missing and answered` → partial；全部有结论无缺失 → grounded；
  无真实结论只有缺失 → insufficient。问题项只写 missing、无 claims 时**不计为已答**。
- 顶层的 `claims` 只放有引用支撑的结论，且必须被至少一个问题项关联；
  **「资料没有提供…」类缺失说明只能写进 `missing`**，写进 claims 会触发「问题覆盖存在未关联的结论」。
- 引用校验：允许同一证据片段被多条**不同**逐字 quote 引用（`{cid:[entry,…]}`）；
  但仍拒绝未知 id、非逐字 quote、空释义、**完全相同**的重复条目。
- **程序只校验显式结构，不校验语义**：纠正“用原则冒充数量答案/把风格要求当缺少事实”靠提示词
  （evidence-v3.5），必须用**定向真实复验**确认，本地测试通过 ≠ 语义已修复。

## 工具与命令

- 工作目录 `E:/DSWorking/project_01`，CLI `python -m skra`；向量功能用 `.\.venv\Scripts\python.exe -m skra`。
- 测试：`.\.venv\Scripts\python.exe -m unittest discover -s tests -v`
- 账本：`python -m skra budget`；离线重放：`python -m skra --db <db> replay <run_id>`
- 受控边界：`python scripts/check_boundaries.py`（免费）/ `--live`（付费）
- 原资料验收：`python scripts/check_acceptance.py`（免费）/ `--live`（付费）/ `--live --case Q01`（定向）
