# Issue 10 验收证据：证据不足时最多补充检索两轮

- 日期：2026-09-10
- 里程碑：M3｜类型：AFK｜技能节奏：**tdd**（外加前置的针对性架构复核）
- 关联卡片：`.scratch/security-research-assistant/issues/10-bounded-search.md`
- 前置复核：`docs/evidence/issue10-precheck-orchestration-20260910.md`
- 对照报告：`docs/evidence/issue10-supplement.json`
- 全部验证**无付费调用**：账本 `0.471396 / 9.528604 / 预留 0 / blocked=false`，前后未变。

## 1. 交付物

| 文件 | 作用 |
| --- | --- |
| `skra/orchestrate.py`（新增） | 窄接口编排器：只管迭代与停止判定，不生成回答 |
| `skra/answer.py`（改） | 新增 `bounded_answer()`，在 `answer()` 外包一层有界补充检索；`answer()` 本身未改 |
| `skra/store.py`（改） | 新增 `amend_run()`：把补充记录并入同一条 run，保持运行身份 |
| `scripts/compare_supplement.py`（新增） | 开发集开关对照（三臂） |
| `tests/test_orchestrate.py`（新增，19 例） | 停止规则、边界、轨迹、工具越权、对照形态 |
| `tests/test_bounded_answer.py`（新增，7 例） | 补充轮真的接入回答路径 + 轨迹持久化 |

## 2. 验收项逐条核对

### ① 初次检索之外最多两轮；达到证据要求、没有新证据、超时、错误或预算不足时停止

- 常量 `MAX_SUPPLEMENTARY_ROUNDS = 2`（初次不计），`StopReason` 枚举六值：
  `sufficient` / `no_new_evidence` / `round_limit` / `timeout` / `error` / `budget`。
- 停止优先级（`Orchestrator.execute`）：足够 → 无新证据 → 两轮上限；超时与预算在每轮检索前检查，
  错误捕获检索器与回调异常。逐条测试：

| 停止原因 | 测试 | 断言 |
| --- | --- | --- |
| `sufficient`（谓词） | `test_sufficient_evidence_stops_immediately` | 1 次检索、0 补充轮 |
| `sufficient`（必需集） | `test_no_new_evidence_stops_before_the_cap` 对照组 | 命中 required 即停 |
| `no_new_evidence` | `test_no_new_evidence_stops_before_the_cap` | 2 次检索、1 补充轮 |
| `round_limit` | `test_the_cap_stops_a_productive_loop_at_two_rounds` | 3 次检索、恰 2 补充轮 |
| `timeout` | `test_a_deadline_stops_a_run_that_overran` | 0 次检索、`timeout` |
| `error`（检索器） | `test_a_retriever_error_stops_and_is_recorded` | 记录异常文本 |
| `error`（回调） | `test_an_answer_callback_error_stops_and_is_recorded` | 记录异常文本 |
| `budget`（检索前） | `test_budget_guard_stops_before_any_search` | 0 次检索 |
| `budget`（循环中） | `test_budget_guard_stops_mid_loop` | 保留已取证据 |

**真实集成验证**（非模拟契约）：`tests/test_bounded_answer.py` 走真实 `answer()` 路径 + 假传输，
确认补充轮确实被请求、能把 `insufficient` 升级为 `grounded`、且两轮上限在每轮都有新证据时仍然成立。

### ② 工具和参数由程序校验，不允许联网或写入；每个模型请求进入同一预算账本

- **参数**：`Orchestrator.execute` 复用 `store.check_search_args`（08 收敛的单点守卫），
  不制造第四份参数校验。`test_invalid_query_and_limit_are_refused_by_the_program` 断言
  空查询、`limit=0`、`limit=21` 均在触达检索器**之前**抛错（0 次检索）。
- **工具越权**：`_vet_candidates` 拒绝任何带 `tool`/`tool_call`/`function_call`/`arguments`
  的候选，以及无 `id` 的候选 → `StopReason.ERROR`，证据集为空。
  见 `test_a_candidate_that_requests_a_tool_is_refused`、`test_a_candidate_without_an_id_is_refused`。
- **不联网/不写入**：`Orchestrator` 无任何开启网络或写文件的参数；传入
  `allow_network=True` / `write_files=True` 会 `TypeError` 而非被静默忽略
  （`test_the_orchestrator_cannot_be_asked_to_write_or_fetch`）。
- **同一账本**：每一轮都经由真实 `answer()`，而 `answer()` 的每次请求都走
  `ledger.reserve → settle/unknown`。编排器不绕过账本，也不新增第二条计费路径。
  对照脚本 `--network_called=False / billed_calls=0 / cost_rmb=0`。

### ③ 轨迹展示查询、候选、最终证据、外部状态与错误，不要求思维链

- `trace` 每轮记录：`round`、`query`、`returned`（候选 id）、`new_ids`、
  `mode`、`run_id`（外部状态）。最终 `evidence` 为累积去重后的全部证据；
  停止时附 `stop_reason`、`stop_detail`、`supplementary_rounds`、`max_supplementary_rounds`、`elapsed_ms`。
- **无思维链**：回调返回值从不写入 trace。`test_the_trace_is_auditable_and_carries_no_chain_of_thought`
  让回调返回 `{"reasoning":"SECRET_THOUGHT"}`，断言整份结果 JSON 不含 `reasoning` / `SECRET_THOUGHT`。
- 轨迹随答案持久化到同一条 run（`amend_run`），`store.run(answer_run_id)["supplement"]` 可读回，
  含 `stop_reason`、`max_supplementary_rounds`、`trace`。

### ④ 测试无效循环、越权请求、无新证据和额度耗尽；基于开发集做开关对照，固定其他因素

- **无效循环**：`test_the_cap_stops_a_productive_loop_at_two_rounds`（每轮都有新证据仍止于 2 轮）；
  `test_a_static_reask_never_grows_the_evidence`（同一查询重复返回同一片段 → `no_new_evidence`）。
- **越权请求**：见 ② 的三例工具边界测试。
- **无新证据**：`no_new_evidence` 两例（见 ①）。
- **额度耗尽**：`budget` 两例（检索前 / 循环中）。
- **开发集开关对照**：`scripts/compare_supplement.py` 三臂，报告见 `issue10-supplement.json`。
  固定因素：语料（真实 OWASP 快照，排除合成夹具）、切分策略、k、问题与标注（D01–D10，与 07 冻结一致）。
  **唯一变化因素：补充检索轮数。**

## 3. 开发集开关对照结果（诚实记录）

| 臂 | 检索方式 | 10 题停止原因 | 到达证据 |
| --- | --- | --- | --- |
| `supplement-off` | 单次 top-k=5 | —（无循环） | 每题 5 片段 |
| `supplement-on` | 同一查询、静态语料 | **`no_new_evidence`×10**，1 补充轮 | 每题 5 片段，与 off 完全一致 |
| `supplement-widening` | 逐轮放宽 k（k,2k,3k） | **`round_limit`×10**，恰 2 补充轮 | 每题 15 片段，0 题退化 |

**结论（如实、不夸大）**：

1. **同查询静态语料下补充检索无增益，且这是正确行为**：重问同一问题得到的仍是同一 top-k，
   累积集不增长 → 立即 `no_new_evidence` 停止。有界循环**不会凭空造出证据**，这是安全性证据，不是效果提升。
2. **两轮上限确实会 bind**：加宽臂每轮都带来新证据，10 题全部止于 `round_limit`，
   证明"最多两轮"是硬约束而非仅在无新证据时才生效。
3. **累积语义只增不减**：两臂中 `lost_cases` 恒为空。这是结构性质（补充只会向累积集加入片段，
   不会移除初次已有的片段），**不作为效果证据**；报告 `delta.note` 已显式声明。
4. **生成侧效果未测**：额外的检索轮是否让**回答**更好，是需要付费调用 + 人工语义复核的问题，
   本任务**未运行**，已在报告 `not_run` 中列明。**结构状态命中 ≠ 语义通过。**

## 4. 版本一致性（与 06 衔接）

- `bounded_answer` 的每一轮都调用真实 `answer()`，因此每轮都执行 `revalidate`：
  证据在回答生成期间被更新或删除时，该轮照常阻止过时结论。
- 编排器轮次回调使"中途证据失效"成为可独立构造的场景，顺带缓解架构发现 ④
  （`revalidate` 可注入性），未在本轮重构 `answer()`。

## 5. 测试与真实/模拟验证的区分

- 本地测试：`.\.venv\Scripts\python.exe -m unittest discover -s tests` → **144 tests 全绿**
  （08 收尾时 118；10 新增 26：编排 19 + 集成 7）。
- **模拟契约测试**：`test_orchestrate.py` 用假检索器/假回调，验证停止规则与边界；
  `test_bounded_answer.py` 用真实 `answer()` 路径 + 假传输（`send`），不触网。
- **真实语义验证**：本任务**未做**付费生成，因此不得声称回答质量提升。
  已用真实 dev 语料 + 真实向量检索做了**结构对照**（`compare_supplement.py`），
  它测的是"到达了哪些片段"，不是"回答是否正确"。
- **保留集**：`examples/eval-holdout-cases.json` 全程未打开，封存至 Issue 12。

## 6. 费用与未解决问题

- 费用：本任务 **0 元**（无付费调用）。账本 `0.471396 / 9.528604 / 预留 0 / blocked=false` 未变。
- 未解决 / 移交：
  - **Q04/Q06 检索欠项**（05 遗留）：所需片段向量排序第 7、20 行块过粗，记入 13/14/11 结构适配；
    本任务的补充检索**不能**解决它（同查询重检索不改变排序），如实记录。
  - **`answer_run_id` 不写入自身 run 记录**（既有行为）：`record_run` 在 id 赋值前序列化，
    故持久化行不含 `answer_run_id`；测试已按真实行为断言，不在本轮改动。
  - **生成侧效果**：留待需要时在本机交互终端做付费 + 人工语义复核。
