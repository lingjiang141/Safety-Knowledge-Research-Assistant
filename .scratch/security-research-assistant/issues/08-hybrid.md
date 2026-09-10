# 08 — 用混合检索回答同一批问题并比较基线

Status: done
State: closed
Type: AFK
Milestone: M2
User stories: US3, US9, US18, US21
Source: [PRD](../../../PRD.md)

## What to build

前置工作：04–06 完成后、开始本任务前直接使用 improve-codebase-architecture，按 docs/development-workflow.md 检查实际改动痛点；用户已授权，不要求为重构而重构。

在可用问答与评测路径增加 BM25 与 RRF，保持纯向量模式可选，对固定开发集比较效果。

## Acceptance criteria

- [x] 候选、融合参数及排序可复查，融合与索引都过滤无效版本。
- [x] 中文问题与英文词项错配需记录；如加入查询翻译或扩展，另做对照并记成本。
- [x] 只改变主要检索因素，保留模型、语料、问题及生成设置；报告有利、无效及退化案例。
- [x] 完成真实检索实验及必要回归测试；生成实验均受全局预算限制，不提前承诺提升。

## Blocked by

- [x] [15-chunking-comparison](15-chunking-comparison.md)

## Completion evidence

**代码版本 / 演示命令**（本地、零费用，可反复运行）：

```
.venv/Scripts/python.exe scripts/compare_retrievers.py \
    --out docs/evidence/issue08-retriever-comparison-20260910.json
```

新增模块 `skra/bm25.py`（Okapi BM25，`k1=1.5`/`b=0.75`，body 优先排序）、
`skra/fusion.py`（RRF，`K=60` 等权，只读排名不合并分数尺度）；`skra/vector.py` 与
`skra/answer.py`、`skra/boundaries.py` 改用共享规则；`skra/store.py` 新增
`check_search_args` / `active_chunk_ids` / `record_run` / `search_terms` / 参数常量。

**测试结果**：本地 **118 tests 全绿**（新增 BM25 7 例、RRF 融合 8 例、共享规则守卫 5 例）。

**真实与模拟验证的区分**：
- **真实检索实验**（本地向量编码器 + 真实 OWASP 语料 + 真实开发集标注）：
  向量 0.850 / BM25 0.400 / RRF 0.750。见 § 结果。
- **未运行**：生成侧指标、人工语义复核、保留集执行。报告中已标为 `not_run`。

**结果（束级 Recall@5，开发集 D01–D10）**：三路均**未相对纯向量提升**。
BM25 −0.450（4/10 零候选，中英词项错配）；RRF 融合 −0.100（修回 BM25 的 D05/D06/D10，
但 D09 被"词面相似但跨度错误"的片段挤掉）。**如实记录为负面结果，未调参拟合。**

**费用与未知预留**：`billed_calls=0`、`cost_rmb=0`；账本全程未变
（0.471396 / 9.528604 / 预留 0 / blocked=false）。保留集未打开（`holdout_loaded=false`）。

**未解决问题**：
- D04（三路皆 0.00，需覆盖三个独立定义束）与 D07（跨资料 1/2 束）是**切分/跨资料排序**
  问题，融合无法补上缺失的束，继续交由 11/14 结构适配路径。
- RRF 的失效模式已定位（奖励跨路一致会放大词面相似而跨度错误的候选）；改进方向应是
  按跨度/结构约束重排或带位置去偏，而非调权重——那需要各自的证据，本任务不做。

**证据文档**：`docs/evidence/issue08-retriever-comparison-20260910.md`（对照报告 JSON 同目录）。

## Comments

尚未开始实现。遵守 PRD 的资料边界及 10 元总预算；AFK 表示常规实现无需逐项确认，不表示允许跳过密钥、预算或人工语义复核。

### 前置工作（卡片要求，已授权，按 docs/development-workflow.md 执行）

04–06 后、13 前的完整架构检查**已完成**（用户裁定本次不重构，5 项发现见
`docs/evidence/architecture-review-20260910.md`）。08 前复核以下三项**新增证据**即可，
**只有出现新问题才再次重构**，不机械执行：

- **⑤ 两检索器规则重复**（已确认为真实缺口）：`store.search` 有「正文优先于 metadata」排序
  （`(-score, kind != "body", id)`），`vector.search` **没有**。本任务要加第三、第四条检索路径
  （BM25、RRF），**这是复核 ⑤ 的直接时机**：融合前应先确认各路检索对 `active`/`limit`/装配
  的规则是共享还是再次复制。
- **③ `answer()` 巨函数**：121 行、多职责；本任务要改检索装配，需确认是否会加剧该函数耦合。
- **07 新增的 `eval.py` 跨度解析耦合点**：`resolve_span` 直接读 `chunks` 表（行范围覆盖 + `active=1`）。
  **15 对照中未观察到需随切分策略同步改动**，本任务再确认一次。

### 从 15 继承的实测起点（可直接复用，勿重复测量）

- 对照脚本 `scripts/compare_splitters.py` 已建立「**一次只改一个因素**」的做法：每策略从同一批快照
  建独立 DB、其余全冻结。**08 应沿用同一纪律**（只切检索器，模型/语料/问题/生成设置固定）。
- 开发集基线（Issue 07）：向量检索 k=5 `recall@5 = 0.85`，未命中 D04（0/3 束）、D07（1/2 束）。
- 15 在指南结构下 D07 已被救回（0.50 → 1.00）；**D04 三策略皆 0.00** 属排序/粒度缺口，
  是本任务观察 BM25/RRF 是否改善的直接对象。
- **跨策略/跨检索器都不能用 chunk 数或 chunk ID 直接比较 Recall**；分母仍是标注的证据束数。
- 15 结果：`docs/evidence/issue15-splitter-comparison-20260910.md`。

### 中英词项错配（卡片验收项 2，需专门记录）

开发集问题是中文，语料是英文。BM25 直接对中文查询与英文原文做词项匹配必然大量落空。
先**测量并记录**这种错配（例如中文查询词项命中 0 的用例数），再决定是否加入查询翻译/扩展；
**若加入，必须另做对照并记成本**（且翻译调用进同一预算账本）。不要默认它会提升。
