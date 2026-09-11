# 10 — 证据不足时最多补充检索两轮

Status: done
State: closed
Type: AFK
Milestone: M3
User stories: US11, US12, US13, US17, US18, US19, US20
Source: [PRD](../../../PRD.md)

## What to build

执行要求：直接使用 tdd；若编排逻辑难以独立验证，先按 docs/development-workflow.md 使用 improve-codebase-architecture。用户已授权。

让助手根据已有检索结果决定是否在导入资料内补充搜索，最终输出答案与停止原因。

## Acceptance criteria

- [x] 初次检索之外最多两轮；达到证据要求、没有新证据、超时、错误或预算不足时停止。
- [x] 工具和参数由程序校验，不允许联网或写入；每个模型请求进入同一预算账本。
- [x] 轨迹展示查询、候选、最终证据、外部状态与错误，不要求思维链。
- [x] 测试无效循环、越权请求、无新证据和额度耗尽；基于开发集做开关对照，固定其他因素。

## Blocked by

- [08 — 用混合检索回答同一批问题并比较基线](08-hybrid.md)

## Completion evidence

**代码版本**：`skra/orchestrate.py`（新增，`MAX_SUPPLEMENTARY_ROUNDS=2` + `StopReason` 六值 +
`Orchestrator`）、`skra/answer.py` 新增 `bounded_answer()`（`answer()` 本身未改）、
`skra/store.py` 新增 `amend_run()`、`scripts/compare_supplement.py`（新增对照）。

**演示命令**：
- 对照：`.\\.venv\\Scripts\\python.exe scripts/compare_supplement.py --out docs/evidence/issue10-supplement.json`
- 测试：`.\\.venv\\Scripts\\python.exe -m unittest discover -s tests` → **144 tests 全绿**（10 新增 26）
- 单测：`tests.test_orchestrate`（19）、`tests.test_bounded_answer`（7）

**真实与模拟验证的区分**：
- 模拟契约：`test_orchestrate.py` 假检索器/假回调，验证停止规则与边界；无模型、无账本、无网络。
- 真实集成（结构层）：`test_bounded_answer.py` 走真实 `answer()` 路径 + 假传输；
  `compare_supplement.py` 用真实 OWASP 语料 + 真实向量检索做开发集开关对照。
- **未做付费生成**：回答质量是否提升属语义问题，未运行，不得据此声称效果提升。

**对照结论（如实）**：同查询静态语料下补充检索 10 题全 `no_new_evidence`、无增益（正确行为：
不会凭空造证据）；加宽臂 10 题全 `round_limit`（两轮上限确实 bind）；两臂 `lost_cases` 恒为空
（结构性质，非效果证据）。见 `docs/evidence/issue10-bounded-search-20260910.md`。

**费用与未知预留**：0 元（无付费调用）。账本 `0.471396 / 9.528604 / 预留 0 / blocked=false` 未变。

**未解决问题**：
- Q04/Q06 检索欠项（05 遗留）非本任务所能解决（同查询重检索不改变排序），移交 13/14/11。
- `answer_run_id` 不写入自身 run 记录（`record_run` 在 id 赋值前序列化）为既有行为，本轮未改。
- 生成侧语义效果留待付费 + 人工复核；保留集封存至 12。

## Comments

已实现并经开发集开关对照；AFK 不表示允许跳过密钥、预算或人工语义复核。
