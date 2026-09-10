# 项目长期记忆：安全知识研究助手

## 关键约束（务必遵守）

- **禁止对共享 git 索引/对象库做临时操作**。想演示“修复前失败”时，用临时目录副本、
  `git worktree` 或直接在测试里断言旧行为；不要用 `git stash`、`git checkout --` 等
  触碰工作索引的命令。2026-09-10 曾因 `git stash push` 损坏对象库（11 个历史提交被删，
  已从工作区重建基提交 a08ac81）。
- 费用账本 `.data/budget.sqlite3` 跨知识库共用，10 元总预算，**不得重置或删除**。
  当前累计 **0.471396** 元、可用 **9.528604** 元、预留 0、blocked=false（保守记账，2026-09-10 用户已核对平台账单一致）。
- 密钥只在本机环境变量/隐藏输入配置，不进代码、聊天或日志。无密钥时只跑本地测试。
- **导入任何资料前先核查页脚许可 + 使用条款**；公开可读 ≠ 可全文再发布（S01 Anthropic 即因此不能导入）。

## 流程约定

- 每次任务开始：读 HANDOFF.md → PRD.md → CONTEXT.md → docs/development-workflow.md → 对应 Issue → 最新证据。
- 技能时机：05 用 diagnose；06/13/14/11/10 用 tdd；04–06 后、13 前完整 improve-codebase-architecture。
- 先失败回归、再最小修复；模拟契约测试 ≠ 真实语义验证，不得混称；**结构状态命中 ≠ 语义通过**。
- 分阶段提交；更新 HANDOFF；不移动/不伪造恢复标签。用户提到的工作分支 `codex/issue05-continue`
  与标签 `checkpoint-issue05-before-handoff` 本机从未存在。

## 当前进度快照（2026-09-10）

- **Issue：01/02/03/04/05/06 done**（03/05/06 均 2026-09-10 完成）；07–15 open（09 可选）。
- 主线：**13 → 14 → 11 → 07 → 15 → 08 → 10 → 12**（+ 可选 09）。**架构检查已完成（用户裁定不重构）**，下一步 13（按 tdd）。
- 当前提示词 **evidence-v3.5**，输出上限 **1500** token（常量 `OUTPUT_TOKEN_LIMIT`），单次最大预留 3.159228 元。
- 本地 **39 tests 通过**（06 新增版本一致性 6 例）。
- **06 版本一致性（done）**：`update`/`delete` CLI 子命令；chunks 增 `version`/`active` 列；
  更新=新版本失效旧版（PRD 4.3）；`answer.revalidate` 阻止回答期间证据失效的过时答案；
  向量索引仅取 active。旧库自动 `ALTER TABLE` 迁移。详见 `docs/evidence/issue06-version-sync-tdd-20260910.md`。
- **架构检查（done，用户裁定不重构）**：5 项「规则被复制」摩擦点记录于
  `docs/evidence/architecture-review-20260910.md`（①提示词版本白名单漂移 ②切分不变量分散
  ③answer()巨函数 ④revalidate 可注入性 ⑤两检索器规则重复），供 13 前复核。
- 05 两条验收路径：
  1. 受控场景 `check_boundaries.py`：v3.3 下十题全部有符合要求的观察（非检索、非准确率）。
  2. 原始资料题 `check_acceptance.py`：v3.4 全跑→修 2 生成缺陷→v3.5 定向重跑 Q01/Q07/Q09 确认修复生效。
     欠项：**Q01 已换题待跑**（新题「提示注入与越狱有什么区别？」）、**Q04/Q06 检索未命中**
     （所需片段向量排序第 7，20 行块过粗——记入 13/14/11 结构适配，不改固定检索器）。
- 03 收尾可复用：十题中 Q02/Q05（有据）/Q08（无据）/Q09（部分有据）对应三类。
  **2026-09-10 全批 --live 已跑完**（报告 `docs/evidence/issue03-acceptance-live-v35-full-20260910.json`，
  复核 `issue03-acceptance-review-v35-full-20260910.md`）：complete=True、8/10 命中，
  三类代表题语义通过、新版 Q01 grounded、v3.5 全批生效；Q04/Q06 仍为检索欠项（诚实降级、无编造）。
  待办：平台账单核对 + 用户最终语义验收（03 未关单）。

## 已知架构痛点（架构检查 2026-09-10 已记录，用户裁定暂不重构）

- 详见 `docs/evidence/architecture-review-20260910.md`。要点：
  ① `cli.py` replay 白名单与 `answer.PROMPT_VERSION` 两处漂移（无测试护栏）；
  ② 切分策略版本编码进「片段 id/文档幂等/向量指纹」三个不变量，跨 store+vector；
  ③ `answer()` 121 行巨函数多职责；④ `revalidate` 缺可注入调用点；
  ⑤ `store.search` 与 `vector.search` 重复 limit/active/runs/装配 4 处规则。
  13 引入新切分/检索后端前先按 ②⑤ 评估影响面。

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
- 测试：`.\.venv\Scripts\python.exe -m unittest discover -s tests -v`（当前 39 tests）
- 账本：`python -m skra budget`；离线重放：`python -m skra --db <db> replay <run_id>`
- 受控边界：`python scripts/check_boundaries.py`（免费）/ `--live`（付费）
- 原资料验收：`python scripts/check_acceptance.py`（免费）/ `--live`（付费）/ `--live --case Q01`（定向）
- 资料版本管理（06）：`python -m skra update <file> --source <src>` / `python -m skra delete <src>`
