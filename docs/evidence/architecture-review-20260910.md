# 架构检查（04–06 后、13 前）：发现与结论

日期：2026-09-10｜技能：**improve-codebase-architecture**（流程：探索 → 呈现候选 → 用户裁定）
范围：`skra/store.py`、`vector.py`、`answer.py`、`cli.py`、`boundaries.py`。
**结论：用户裁定本次不重构**（④）。以下 5 项发现作为证据记录，供 13 前或新证据出现时复核，
避免重复走查。检查不等于重构，无实际痛点保留现状。

## 五个「同一规则被复制」的摩擦点

### ① 提示词版本白名单在多入口漂移（确认成立）

- 证据：`answer.py:11` `PROMPT_VERSION="evidence-v3.5"`；`cli.py:104` 硬编码
  `{"evidence-v3","evidence-v3.1",…,"evidence-v3.5"}`；提示词正文在 `answer.py:16-67` `SYSTEM`。
- 摩擦：同一「当前版本」事实存两处。新增版本至少改 2 处（含 `OUTPUT_TOKEN_LIMIT` 则 3 处）；
  漏改会让 replay 旧记录**静默跳过** coverage 校验（退化而非报错）。
- 候选解法：白名单可由语义派生（v3 起均需校验），收敛为单一常量 + 一致性回归测试。
- 历史证据：HANDOFF/进度文档逐条记录「升级提示词 + `cli.py` 同步」，实证每次手动同步。

### ② 切分策略不变量分散（确认）

- 证据：`store.py:10` `SPLITTER`；`store.py:58` 片段 id = `digest(doc_id:content_hash:SPLITTER:start:end)`；
  `store.py:92/104` 幂等判定；`vector.py:55` `corpus()` 指纹；`vector.py:79` 索引失效判定。
- 摩擦：切分策略版本同时编码进 **片段 id / 文档幂等 / 向量语料指纹** 三个不变量，
  跨两模块。改切分（未来 13/14/11）会连锁触发旧 id 失效、幂等失效、索引重建，
  但「改切分涉及哪些表」无单一出处。
- 候选解法：合并到 store 的「版本标识」单一函数。

### ③ `answer()` 巨函数（121 行）

- 证据：`answer.py:280-401` 塞入检索调用、问题切分、配置/价格校验、传输与用量、
  校验与诊断、状态汇总与持久化，另有 demo/preflight 分支。
- 摩擦：任一职责的测试都需构造完整 `store+ledger+send` 环境。
- 候选解法：拆 `prepare_config` / `call_model` / `assemble_output` 三段窄接口。
- 深浅判断：`Store.read/documents/run` 等浅透传应保留（删除会把复杂度转给 N 个调用方）。

### ④ 可测试性缺口：`revalidate` 缺可注入调用点

- 证据：`revalidate`（`answer.py:262-277`）是纯函数，唯一调用点 `answer.py:386`，
  夹在 `finally` 的 runs 写入之前。`test_version_sync.py` 只能用「先检索再删除」时序触发，
  无法独立测「版本不匹配」分支。
- 关联缺口：`PROMPT_VERSION` 与 `cli.py` 白名单的一致性**无测试护栏**。

### ⑤ 两套检索入口的共同规则重复（确认）

- 证据：`store.search`（`store.py:137-162`）与 `vector.search`（`vector.py:73-99`）逐字重复：
  limit 校验（`store.py:138`/`vector.py:74`）、active 过滤（两处）、runs 持久化（`store.py:158-161`/
  `vector.py:95-98`）、候选装配 `self.read(cid)`。受控适配器又两处手写 runs 插入
  （`boundaries.py:30-33`、`test_question_coverage.py:37-40`）。
- 摩擦：`runs` 表列签名改动需同步 4 处，无单点守卫；新增检索后端（BM25/混合）会再复制。
- 候选解法：抽 `record_run()` / `make_result()` 到 store。

## 关键改动点的公共接口（供 13 复用）

- 资料管理 `Store`：`ingest`（幂等 + 原子发布 + 旧版本退役）、`delete`、`documents`、`read`（active 过滤 + 失效提示）、
  `search`、`run`。切分逻辑内聚在 `_chunk`。
- 检索 `VectorSearch`：`build`（指纹校验）、`search`（active 过滤 + 指纹失效检测）。
- 回答 `answer(store, query, ledger, config, key, send, demo, preflight, search)` +
  纯函数 `question_parts` / `apply_coverage` / `validate` / `revalidate` / `cost`。
- **接口即测试面**：现有 39 tests 均经这些公共接口进入（`test_version_sync.py` 明确声明只走公共 Store 接口）。

## 复用建议（13 开始时）

- 改切分策略前，先按 ② 确认「片段 id / 幂等 / 向量指纹」三处影响面，避免遗漏重建。
- 13 引入新检索后端前，先按 ⑤ 收敛共同规则，避免第四份 runs 插入。
- 迁移期新增提示词版本时，按 ① 手动同步并在 13 前补一致性测试。

所有复用建议均以「检查结论」形式记录，**本轮未实施任何重构**；用户裁定保留现状。
