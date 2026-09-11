# 项目一进度

> 本文件倒序记录，旧段落会出现过时状态；以最新节、ROADMAP.md 任务 State 与 HANDOFF.md 为准。

## 2026-09-10 Issue 12 完成（done）—— 主线全部收口

- **五项验收全满足、无预算耗尽 → Issue 12 关闭**。用户「全部接受」：引文与释义一致、Q06 归因接受、
  Q08 行为通过、`0.75` 与四例缺口作为最终交付接受。
- **最终交付（诚实版）**：保留集检索 `recall_at_5=0.75`（dev 0.85）；生成侧**行为正确**
  （不编造、如实降级、释义准确、不编造分歧）；**能力缺口四例**（H03 0.50 / H04 0.00 / H09 0.00 + Q06 partial）
  均已定位（根因 `heading-lines-v1:20` 粗块 → 排序掉出预算），**移交 13/14/11 结构适配，不改固定检索器**。
- **⑤ 三态**：已完成（评测/演示/复盘/4 题行为复核/`run_baseline` 缺陷修复）；故意可选（09、结构适配修复、
  生成侧正式指标以 4 题行为复核代替）；**预算所致未完成：无**（可用 9.4825 元）。
- **主线 01–08、10、11、13、14、15、12 全部 done；09 可选未采用；M0–M3 全完成。**
- 费用：本任务付费 **0.046104 元**（账本 0.471396 → **0.5175**，可用 9.4825，预留 0，blocked=false）。
- 148 tests 全绿。证据：`docs/evidence/issue12-holdout-and-failures-20260910.md`、
  `issue12-generation-review-20260910.md`、`issue12-holdout-baseline-20260910.json`。

## 2026-09-10 Issue 12 进行中 —— 保留集首次开封评测 `recall@5=0.75`（修缺陷后）、演示脚本跑通、三例真实失败复盘

- **本轮先修一个真实评测缺陷（先于评测）**：`run_baseline(..., holdout=...)` 会加载保留集却**只评 dev**，
  且把 `sample_kind` **硬编码 `"development"`** —— 会让"保留集最终评测"把 **dev 分数挂在保留集标题下**。
  按 tdd 先写失败测试 `tests/test_eval.py::FinalHoldoutEvaluationTest`（4 例，3 红）→ 最小修复
  （`kind` 推导/校验、评 `loaded.holdout`、正确标注、剔除过时 `not_run`）→ CLI 接线。
- **保留集首次开封评测（07 起封存，12 首次开封）**：报告
  `docs/evidence/issue12-holdout-baseline-20260910.json`，`sample_kind="holdout"`、
  `evaluated_case_ids=[H01…H10]`、**`recall_at_5=0.75`**（dev 0.85）、`broken_bundles=0`、
  `failed_cases=[]`、`complete=false`（生成侧与人工复核未跑）。逐例：H03 0.50、H04 0.00、H09 0.00，其余 1.00。
  **未因结果改任何代码或提示词。**
- **三例真实失败（均已定位，未修，交接 13/14/11）**，共同根因 `heading-lines-v1:20` 把标题+来源+出版者+导语
  压进 18–20 行块、答案被埋、嵌入被稀释 → **覆盖片段存在，是"排序未进前 5"，不是"资料没有"**：
  - **H04 0.00**：覆盖块 `2d61fd19df57` L1–18（整个文档头），top-5 之外（独立复现第 7 名）→ 两 bundle 全未命中。
  - **H09 0.00**：覆盖块 `7e3ff71da9ec` L45–64（"预防与缓解"整节）未进前 5。
  - **H03 0.50**：两 bundle 只中一个（`45f7c6e76593` L60–62 未中 / `a0636ee4f451` L52–54 中）→
    bundle 规则要求**全部**覆盖片段进前 5，partial 计未命中（**故意设计**，不因单例放宽）。
- **演示脚本 `scripts/demo.py` 跑通**（约三分钟，免费离线；`--live` 才付费）：① 切分预览 ② 同题前后证据
  ③ 失败复盘 ④ 边界（无证据→`insufficient`、0 结论）⑤ 生成回执（`request_bytes=13078`、
  单次最大预留 `3.159228` 元、`available=9.528604`、`blocked=False`、`network_called=False`）。
  展示重点按卡片：**切分预览 / 同题前后 / 失败复盘为主，指标仅作支撑**；区分工程改良与学术创新。
  调试中修 2 处：`preflight` 需传入已核实 config（密钥检查在预留分支之前）；
  中文问句对英文语料关键词检索零命中 → 生成步骤改用可命中英文问题。
- **验收项状态**：①②③④ 完成；**⑤（最终判定）与平台账单核对待完成，故 12 不关闭**。
  证据文档 `docs/evidence/issue12-holdout-and-failures-20260910.md`（含 §5 逐项核对、§7 HITL 待办）。
- **测试**：148 tests 全绿（144 → 148）。**费用 0 元**；账本 `0.471396 / 9.528604 / 预留 0 / blocked=false` 未变。

### 追加：生成侧复核（验收项 ②）→ 用户裁定通过

- 用户跑 `scripts/check_acceptance.py --live --case Q05 --case Q06 --case Q08 --case Q09`：
  **3/4 通过**——Q05 grounded ✅ / Q08 insufficient ✅（检索到证据却答不了，**0 结论、无任何数字**）/
  Q09 partial ✅（概念按原文、百分比单列）；**Q06 partial ❌**（期望 grounded）。
- **Q06 根因已查实**：含「最小权限」（LLM01 措施 4）的块 `L36-55` 在 Q06 查询下排**第 5 名**，
  验收运行器内部 `k=3` → 门外 → 模型拿不到措施 4 → **如实**判 partial。
  属 **Issue 03 已记录的已知检索欠项**，与 H03/H09 同源，**非生成缺陷**。
- 用户逐题裁定：引文与释义**一致**、Q06 归因**接受**、Q08 行为**算通过** → **② 通过**。
  证据 `docs/evidence/issue12-generation-review-20260910.{md,json}`。
- **费用 0.471396 → 0.5175 元（新增 0.046104）**；可用 9.4825、预留 0、blocked=false。
- **诚实边界**：样本仅 4 题，**不构成指标、不宣称整体准确率**；② 通过的是**行为正确性**，非检索能力充分。

## 2026-09-10 Issue 10 完成 —— 有界补充检索（最多两轮 + 停止原因轨迹，开发集对照如实记录无增益）

- **Issue 10 完成（done）**：让回答在证据不足时于导入资料内**最多补充检索两轮**，输出**停止原因与可复查轨迹**。
  **前置针对架构发现 ③④ 做局部复核**（`answer()` 实测 120 行），结论：**新增窄接口 `skra/orchestrate.py`，
  不重写 `answer()`**。
- **TDD 落地**：`MAX_SUPPLEMENTARY_ROUNDS = 2`（初次不计）；`StopReason` 六值
  `sufficient` / `no_new_evidence` / `round_limit` / `timeout` / `error` / `budget`；
  `Orchestrator` 只做迭代与停止判定——`answer_once(evidence, round_no)` 回调 + `is_sufficient` 谓词解耦，
  不生成回答，可用假检索器/假回调独立验证。
- **参数与工具边界（程序校验）**：复用 08 收敛的 `check_search_args`（**不制造第四份守卫**）；
  `_vet_candidates` 拒绝带 `tool`/`tool_call`/`function_call`/`arguments` 的候选与无 `id` 候选；
  `Orchestrator` 无任何联网/写入参数（传入未知 kwarg 会 `TypeError`）；每轮经真实 `answer()` 走**同一账本**。
- **轨迹（无思维链）**：每轮记 `round`/`query`/`returned`/`new_ids`/`mode`/`run_id`；
  回调返回值**从不写入 trace**（测试断言不含 `reasoning`）；轨迹随答案**持久化到同一条 run**
  （新增 `store.amend_run`，补写在答案自己的记录上，不追加新行）。
- **集成**：`skra/answer.py` 新增 `bounded_answer()`（`answer()` 本身未改）——每轮以**累积证据**作答，
  补充是扩宽证据而非替换。
- **开发集开关对照（`scripts/compare_supplement.py`，免费离线；固定语料/切分/k/问题/标注，
  唯一变量=补充轮数）**：

  | 臂 | 检索方式 | 10 题停止原因 | 到达证据 |
  | --- | --- | --- | --- |
  | `supplement-off` | 单次 top-k=5 | — | 每题 5 片段 |
  | `supplement-on` | 同查询、静态语料 | **`no_new_evidence`×10**，1 补充轮 | 每题 5 片段，与 off 一致 |
  | `supplement-widening` | 逐轮放宽 k | **`round_limit`×10**，恰 2 补充轮 | 每题 15 片段，0 题退化 |

- **结论（如实、不夸大）**：① 同查询静态语料下补充检索**无增益且这是正确行为**——重问同一问题仍返回同一
  top-k，累积集不增长即停止，**有界循环不会凭空造证据**（安全性证据，非效果提升）；② 加宽臂证明
  **两轮上限确实 bind**；③ 两臂 `lost_cases` 恒为空是**结构性质**，不作为效果证据；
  ④ **生成侧效果未测**（需付费 + 人工语义复核），报告 `not_run` 已列明。**结构状态命中 ≠ 语义通过。**
- **测试**：**144 tests 通过**（118 → 144；新增 `tests/test_orchestrate.py` 19 例、
  `tests/test_bounded_answer.py` 7 例）。
- **交付**：`skra/orchestrate.py`、`skra/answer.py`（+`bounded_answer`）、`skra/store.py`（+`amend_run`）、
  `scripts/compare_supplement.py`、`docs/evidence/issue10-bounded-search-20260910.md`、
  `issue10-supplement.json`、`issue10-precheck-orchestration-20260910.md`。
- 本轮**无付费调用**；账本保持 **0.471396** 元 / 可用 9.528604 / 预留 0 / blocked=false。
  **保留集未打开**（`holdout_loaded=false`）。
- **里程碑/主线**：**01–08、10、11、13、14、15 done；12 open**（09 可选）。**下一步 Issue 12（最终保留评测与演示）**，
  其依赖 10/11/15 均已满足。

## 2026-09-10 Issue 08 完成 —— 向量 / BM25 / RRF 三路检索对照（**无净提升，如实负面结果**）

- **Issue 08 完成（done）**：在已有问答与评测路径增加 **BM25** 与 **RRF 融合**，保持纯向量模式可选。
  新增 `scripts/compare_retrievers.py`（免费离线）。**一次只改一个因素**：语料 / 切分器 / 问题 / 标注 /
  编码器 / top-k=5 / 证据预算全部冻结，三路跑在**同一个数据库、同一份片段**上。
- **前置架构复核（发现 ⑤）**：实测 `INSERT INTO runs` 在代码中重复 **5 处**（比记录的 4 处更多），
  `limit` 校验、`active` 过滤也各有 4–5 份拷贝。为让 BM25 与融合层不制造第 5、第 6 份拷贝，
  把共享规则收进 `skra/store.py`：`check_search_args` / `active_chunk_ids` / `record_run` /
  `search_terms` / `TOKEN_RE` / 参数常量。**等价性逐字节证明**：收敛前后 keyword 检索哈希均为
  `010e9ca4a50a37fc936dc11c2dce8bf43b68a5d0cf07c4af3f82df9a8480ea04`。
- **TDD 落地**：`skra/bm25.py`（Okapi BM25，`k1=1.5`/`b=0.75`，body 优先排序，7 例）、
  `skra/fusion.py`（RRF，`K=60` 等权，**只读排名不合并分数尺度**、**拒绝融合已失效片段**，8 例）、
  防回潮守卫 `tests/test_shared_retrieval_rules.py`（5 例，白名单仅 `skra/store.py`）。
- **对照结果（束级 Recall@5，开发集 D01–D10）**：
  `vector`（基线）**0.850** / 1979 token；`bm25` **0.400**（**−0.450**，退化 D02/D05/D06/D09/D10）；
  `hybrid-rrf` **0.750**（**−0.100**，退化 D09）。**有利案例：无。**
- **三条机制结论（报告内可复查）**：① **中英词项错配**：4/10 用例（D04/D05/D06/D10）在纯词项检索下
  **零候选**，与实现前量化完全吻合；② **融合失效模式**：D09 唯一标注束由单片段 `1e8bc828` 覆盖（向量排第 5），
  而「词面相似但跨度错误」的 `e9312b2a` 同时拿到 BM25 第 1 + 向量第 9 → 被 RRF 抬到第 2，
  挤掉正确的目标片段，**一致 ≠ 正确**；③ **D04/D07 是切分/跨资料排序问题**，融合只能重排已有候选、
  补不上缺失的束，继续交由 11/14 结构适配路径。
- **测试**：**118 tests 通过**（98 → 118）。
- **交付**：`skra/bm25.py`、`skra/fusion.py`、`skra/store.py`（共享规则）、`skra/vector.py`/`answer.py`/`boundaries.py`（改用共享规则）、
  `scripts/compare_retrievers.py`、`scripts/measure_term_mismatch.py`、
  `docs/evidence/issue08-retriever-comparison-20260910.{json,md}`、`issue08-term-mismatch-20260910.txt`、
  `issue08-precheck-architecture-20260910.md`。
- 本轮**无付费调用**（`billed_calls=0`、`cost_rmb=0`）；账本保持 **0.471396** 元 / 可用 9.528604 / 预留 0 / blocked=false。
  **保留集未打开**（`holdout_loaded=false`）。
- **里程碑/主线**：**01–08、11、13、14、15 done；10/12 open**（09 可选）。**下一步 Issue 10（有限补充检索）**。

## 2026-09-10 Issue 15 完成 —— 四种切分策略对照（含一处真实缺陷修复）

- **Issue 15 完成（done，对照型）**：新增 `scripts/compare_splitters.py`（免费离线）。
  **一次只改一个因素**：语料 / 问题 / 标注 / 编码器 / top-k=5 / 证据预算全部冻结；
  每个策略从**同一批快照**建独立 SQLite（不做「重导入基线」这种会污染对照的操作）。
- **Recall 锚在原文行跨度，不锚在片段 id**：分母恒为标注**证据束数**（报告里 `annotated_bundles`
  对每策略同值，证明分母没动）。**跨策略不用 chunk 数或 id 比较 Recall。**
  `required_together` 的束只有**所有覆盖片段都被取回**才算命中，只取到一部分记 `broken`。
- **对照结果（开发集 D01–D10，向量检索 k=5）**：
  `heading-lines-v1:20`（基线）0.850 / 1979.3 token；
  `heading-block-v2`（指南）**0.900 / 1920.7**（**+0.050**，提升 D07，无退化）；
  `heading-procedure-v3`（步骤）**0.400 / 398.3**（**−0.450**，退化 D05–D09）。
  `pdf-pages-v1` **未对照**（语料无 PDF、不能切 Markdown），写入 `not_run`。
- **发现并修复真实缺陷**：procedure 策略把 LLM01 正文行（9/11/13）误标 `kind=metadata`，元数据数
  **11（应为 3）**，会把正文挤出 body 搜索槽。根因两段：① `peel_metadata` 剥离标题块后无标题正文单元
  继承了 `(说明性元数据)` 标签；② 合并阶段又无条件并入元数据单元。**指南策略无此 bug**（有
  `is_metadata_block` 双重保险）。先失败回归 → 最小修复 → 元数据数 11 → 3。
- **测试**：新增 `tests/test_split_labels.py` 4 例 + `tests/test_procedures.py` 1 例回归；
  **98 tests 通过**（93 → 98）。
- **两项诚实局限（验收项 5）**：① procedure-v3 的 −0.450（LLM06 从 7 片段切到 37，粒度过碎、
  排序竞争不过完整段落）；② **D04 三策略皆 0.00**（procedure 把「编号行 + 定义句」切成两片段 →
  `broken`；基线/指南下则是排序未进前 5，**两种 0.00 原因不同，未混称**）。
- **采样局限（验收项 1）**：语料仅 3 份 OWASP Markdown（81/86/50 行）、**无围栏代码、无独立长篇报告**，
  「步骤/代码」以编号措施代表、「文本型报告」以指南散文段代表，已如实记录。
- **保留集未打开**：全程只用开发集；选择规则 = 指南结构零风险采用 / 步骤结构本语料不采用。
- 交付：`scripts/compare_splitters.py`（含 `--preview` 导出切分预览与原文前后对照，215 片段）、
  `docs/evidence/issue15-splitter-comparison-20260910.{json,md}`、`issue15-splitter-preview-20260910.json`。
- 本轮**无付费调用**（`billed_calls=0`、`cost_rmb=0`）；账本保持 **0.471396** 元 / 可用 9.528604 / 预留 0 / blocked=false。
- **里程碑/主线**：**01–07、11、13、14、15 done；08/10/12 open**（09 可选）。**下一步 Issue 08（混合检索）**。

## 2026-09-10 Issue 07 完成 —— 评测样本冻结 + 免费检索基线

- **Issue 07 完成（done，按 tdd 21 例）**：新增 `skra/eval.py` 与 CLI `eval` 子命令。
  接口（用户确认）：**以原文跨度 + 必须共同出现的条件为锚**（不用片段 id）；开发/保留集**文件与代码双重隔离**；
  **先只做免费检索/结构基线**。`tests/test_eval.py` 21 例；**93 tests 通过**（72 → 93）。
- **为什么不用片段 id**：片段 id 是切分策略的函数，锚在它上面会让 Recall 在策略之间不可比（PRD 5.3）。
  跨度按行范围映射到当前策略产出的片段，**分母是标注的证据束数**，切分不改分母。
  `required_together` 的束被切开、只取到一部分 → 记 `broken`，**不算命中**（否则就是奖励本来要抓的失败）。
- **双重隔离**：① 分文件；② 文件自身 `kind` 权威（改名也拒）；③ `load_sample(dev)` 默认不可达保留集；
  ④ 测试守卫（磁盘上放保留集，断言普通运行不打开它）。CLI 实测把保留集当 `--sample` 传入即报错。
- **冻结**：`sample_hash` / `corpus_hash` / `splitter` / `encoder` / 逐文档 hash；同输入同哈希（有测试断言）。
- **基线结果（开发集 10 题，向量检索 k=5，免费离线）**：
  `recall_at_5 = 0.85`、`failed_cases = []`、`broken_bundles = 0`、`mean_evidence_tokens = 1979.3`（估算）、
  `total_metadata_chunks = 0`、耗时 936.5 ms。
  未命中 **D04（0/3 束）、D07（1/2 束）** —— 与 03/05 全批的 Q04/Q06 检索欠项同源，属已知缺口。
  **无 broken 束**说明基线切分下所有标注跨度都落在单片段内，缺口全部来自排序未进前 5。
- **未运行项如实声明**：`complete=false`、`not_run` 三条（生成侧指标、保留集执行、切分对照/混合检索）、
  `manual_review="pending"`。`estimate_tokens` 是字符数/4 的**估算，不是真实分词计数**，报告内已标注。
- **保留集封存**：`examples/eval-holdout-cases.json`（H01–H10）已创建但**本题不运行**，
  覆盖三类结构（长段落散文 / 项目符号清单 / 编号措施步骤），推迟到 Issue 12。
- **依赖教训复用**：本轮新增文件均无新依赖；`--exclude` 剔除项写入报告，否则基线不可复现。
- 证据 `docs/evidence/issue07-baseline-and-freeze-20260910.md` + 原始报告 `issue07-baseline-20260910.json`。
- 本轮**无付费调用**；账本保持 **0.471396** 元 / 可用 9.528604 / 预留 0 / blocked=false。
- **里程碑/主线**：**01–07、11、13、14 done；15/08/10/12 open**（09 可选）。**下一步 Issue 15**。

## 2026-09-10 17:20 Issue 11 收尾 + 全库文档对账

- **Issue 11 完成（done，按 tdd 11 循环）**：新增 `skra/pdf.py`（`pdf-text-v1`，pypdf 纯文本层，
  **不执行文件内容**）；新策略 `pdf-pages-v1`；chunks 增 **`page` 列**（1 基，Markdown 为 NULL）；
  重复页眉页脚→`kind=metadata`（保留可查、不占正文名额）；跨页段落**不合并**；
  扫描件/无文本层/阅读顺序混乱**明确抛错不静默降级**；无 OCR / 复杂表格 / 双栏重建（守 PRD 4.4 边界）。
  夹具 `scripts/make_pdf_fixtures.py` 直接生成 PDF 语法（无额外依赖），5 页含跨页续写。
  证据 `docs/evidence/issue11-pdf-tdd-20260910.md`。**72 tests 通过**。
- **依赖补齐**：`pypdf==6.18.0` 写入 `pyproject.toml` 与 `requirements-vector.lock.txt`。
  核实 pypdf **无运行时依赖**（纯 Python）——最初误写 `pycryptodome` 已纠正。
- **架构发现 ⑤ 确认为真实缺口**：`store.search` 有 body 优先于 metadata 的排序规则，`vector.search` **没有**；
  PDF 页面装饰行成为常规 metadata 片段后更易触发。**已加护栏测试固化期望，未改检索器**，留待 08 前。
- **文档对账**（消除与当前进度冲突的表述）：`README.md`（原停在"当前交付 Issue 01–02 / 仅标准库 / 800 token"）、
  `CONTEXT.md`（"待实现"→已实现）、`docs/development-workflow.md`（TDD 与架构检查时机）、
  `docs/issue05-verification.md`（"Issue 05 未完成"→done）、`docs/live-m0.md`（"验收仍未完成"→done）、
  `ROADMAP.md`、`HANDOFF.md`、`.workbuddy/memory/MEMORY.md`。
- **里程碑**：M0 / M1 / M1D 均已完成。主线 **01–06、11、13、14 done；07/15/08/10/12 open**（09 可选）。
  **当时下一步为 Issue 07**（冻结评测样本与基线报告，HITL）—— 已于同日晚完成，见本文件顶部最新节。
- 本节当时的测试数为 72；07 完成后为 **93 tests**（顶部最新节为准）。
- 本轮**无付费调用**；账本保持 **0.471396** 元 / 可用 9.528604 / 预留 0 / blocked=false。

## 2026-09-10 S01 许可不通过，Q01 替换为库内可答题

- 用户选 A（导入 S01）后核查发现 **S01 不能导入**：Anthropic《Building effective agents》页脚仅 © Anthropic PBC，
  **无开放许可**，条款第 3 条禁止抓取、第 10 条保留全部知识产权。导入语料库会进 git+检索，构成未授权再分发。
  S01 继续仅作外链阅读参考。
- 经沟通，用户裁定 **Q01 换题**：「工作流和 Agent 有什么区别？用容易理解的话说明。」（依赖 S01）
  → **「提示注入与越狱有什么区别？」**（OWASP LLM01 开篇第 1–14 行完整给出定义，检索首命中即该段，
  grounded 可达；且新题只有一个问句，消除原题风格后缀被切分引起的 partial 伪影）。
- 已更新 `examples/acceptance-cases.json` 与 `docs/acceptance-draft.md`；31 tests 通过；
  证据 `docs/evidence/issue05-s01-license-and-q01-replacement-20260910.md`。**尚未真实运行新 Q01**，本轮无付费调用。
- 提交 d894cf8、ad3f9c0。教训：导入任何资料前先核查页脚许可 + 使用条款；公开可读 ≠ 可全文再发布。
- 账本 0.344997 元、可用 9.655003 元、预留 0、blocked=false。Issue 05 仍 in-progress，未进入 06。

**十题当前状态**：Q01（新题，待跑）/ Q02 / Q03 / Q05 / Q08 / Q10 此前符合要求；
Q07、Q09 在 v3.5 已修复并定向复核；Q04、Q06 为**检索未命中**欠项（不改检索器，记入结构适配待办 13/14/11）。

## 2026-09-10 v3.5 定向重跑三题（Q01/Q07/Q09）

- 用户付费跑 `--case Q01 --case Q07 --case Q09`，`complete=True` 无错误。报告
  `docs/evidence/issue05-acceptance-live-v35-targeted-20260910.json`，复核
  `issue05-acceptance-review-v35-targeted-20260910.md`。
- **Q07 → grounded**：v3.5 输出上限（800→1500）修复生效，不再截断，语义完整、引文逐字。
- **Q09 → partial**：题面改写生效，q1 答最小权限概念（引 OWASP 原文），q2 单列缺百分比，符合选项 C 设计。
- **Q01 → partial（预期 grounded，但不再报错）**：**非代码缺陷，是范围/预期问题**——草案与用例均写明
  「S01 未导入则 Q01 暂不可答」，当前无 S01，`expected_status=grounded` 是占位；模型基于 LLM06 降级作答
  属可辩护，q2「用容易理解的话说明」是风格要求被按「？」切成独立问题项而落入 missing（切分伪影）。
- 账本 0.309189 → **0.344997** 元（本批 0.035808），预留 0、blocked=false。提交 5b185e5。

## 2026-09-10 Q09 题面按裁定改写（选项 C）

- 用户裁定选项 C：Q09 原题「资料提到了最小权限。它在我的电脑上能降低多少百分比的风险？」把前提句与
  问句混写，模型可读成纯数值题判 insufficient。改为两个显式小问
  「资料里的最小权限是什么意思？它在我的电脑上能降低多少百分比的风险？」，partial 成为无歧义预期。
- **未改提示词**，以免纯数字题回退。已更新 `examples/acceptance-cases.json` 与 `docs/acceptance-draft.md`；
  31 tests 通过；尚未重跑。提交 22fa8f2、e3af22d。

## 2026-09-10 原始资料验收十题全跑完（v3.4→v3.5）

- 用户付费跑 v3.4 批次，十题**全部执行**（Q01 中断已修）。报告
  `docs/evidence/issue05-acceptance-live-v34-full-20260910.json`，复核
  `issue05-acceptance-review-v34-20260910.md`。状态命中 5/10。
- **已修 2 条生成/契约缺陷**（先失败回归后最小改动）：
  - Q01（call_id=35）：模型把「资料没有提供……」缺失说明写进顶层 `claims`（无引用且未被 coverage 关联），
    触发「问题覆盖存在未关联的结论」。契约正确不放松；提示词升 v3.5 明确缺失说明只能进 `missing`。
  - Q07（call_id=41）：800 token 输出上限截断 JSON（`finish_reason=length`）。输出上限 800→**1500**
    （常量 `OUTPUT_TOKEN_LIMIT`），提示词补 quote 尽量短。
  - 提示词升 **evidence-v3.5**，`cli.py` replay 集合同步。本地 **31 tests 通过**；v3.5 preflight 最大预留 3.159228 元。
- **未修（非生成缺陷）**：Q04/Q06 判 partial 属**检索未命中**（所需片段在库但向量排序第 7，20 行块过粗稀释定义），
  按草案「固定检索器」不中途更换，记入结构适配待办（13/14/11）；Q09 已按裁定改写题面。
- 账本 0.179976 → **0.309189** 元（本批 0.129213）。提交 d4ec180、0250bab、81d659f。

## 2026-09-10 原始资料验收 Q01 中断修复（v3.4）

- 用户付费跑 `scripts/check_acceptance.py --live`，**Q01 即报错停止**（`引用标识无效或重复`），
  Q02–Q10 未执行。根因：模型对**同一证据片段**给出两条**不同**逐字 quote（均真实），而 `validate()`
  用 `cid in verified` 强制每片段最多出现一次——**契约过严**。
- 先写失败回归 `test_two_distinct_quotes_from_one_chunk_are_kept_not_rejected` 与负向守卫
  `test_duplicate_id_with_conflicting_quote_is_still_rejected`，再最小修复：`verified` 改为 `{cid:[entry,…]}`，
  保留同一 id 的多条**不同** quote；仍拒绝未知 id / 非逐字 / 空释义 / **完全相同**重复项。提示词升 **evidence-v3.4**。
- 运行器同步修复：付费批次遇单题 `ValueError` **记录后继续**，仅账本阻塞时停止，不再浪费整批。
- 本地 **29 tests 通过**；诊断 `docs/evidence/issue05-acceptance-q01-fix-v34-20260910.md`。
- 账本 0.166719 → **0.179976** 元（本批 0.013257）；修复轮免费。提交 4bafb17、d2b4a0d。

## 2026-09-10 原始资料开发验收运行器就绪（真实资料 + 检索）

- 按用户选择「原始资料开发题（真实资料+检索）」，把 `docs/acceptance-draft.md` 十题接入**真实知识库 + 本地向量检索**。
  新增 `examples/acceptance-cases.json` 与 `scripts/check_acceptance.py`（默认仅准备，`--live` 才付费）。
- 关键修正：合成 CC0 夹具「Security demo」（`85772b00…`）原本会污染真实资料题（Q07 检索排第三），
  已在用例 `excluded_doc_ids` 中剔除，运行器检索时过滤。
- 准备报告 `docs/evidence/issue05-acceptance-prepared-20260910.json`，说明 `issue05-acceptance-prep-20260910.md`；
  免费 preflight（Q05）通过：12870 字节、最大预留 3.152928 元、`budget_ready=true`、`network_called=false`。
- 欠项：知识库缺 S01，Q01 不能据现有资料断言达标（后经裁定换题，见最新节）。
- 账本 **0.166719** 元（准备与 preflight 均免费）。提交 659cc17、dcd1c72、23c88ad。

## 2026-09-10 v3.3 十题受控场景全部符合要求

- 十题分两批（三题 call 24–26 + 七题 call 27–33），同为 `evidence-v3.3`、同模型、受控证据（非真实检索）：
  **全部有符合要求的观察**，number 为 v3.1/v3.2 连续失败后**首次通过**。
- 要点：agreement 三条结论分别引用两方且不编造分歧；conflict 并列正反不裁决；negation 释义保留否定；
  injection 解释不执行、不拒答；analogy 给出具体生活情境并标注；missing_measurement 不借外部成绩、
  `citation_scope=missing_context`；number 未编造数字。
- **边界**：不等于稳定准确率或正式评测，样本极小；原始资料开发题欠项、03 三类端到端验收欠项、
  用户最终语义验收均保留。报告 `issue05-live-v33-three/seven-20260910.json`。
- 账本 0.125391 → **0.166719** 元（本批七题 0.041328）。

## 2026-09-10 v3.3 number 修复与三题复验

- number 场景按 diagnose 完成离线诊断、先失败回归、最小修复：`apply_coverage` 增加 `answered` 标记
  （只写 missing、无 claims 的问题项不计为已答），提示词升 v3.3 明确「只索取数值的问题项不能由原则凑部分答案」。
  27 tests 通过；详见 `docs/evidence/issue05-number-fix-v33-20260910.md`。
- 定向真实复验三题：number（首次通过，claims 空、insufficient、`citation_scope=missing_context`）、
  partial、conditions 均符合要求。报告 `issue05-live-v33-three-20260910.json`。
- 账本 0.108174 → **0.125391** 元（本次三题 0.017217）。
- 另：本轮发生 **git 对象库损坏**（`git stash push` 导致 11 个历史提交对象被删），经用户确认从完好工作区
  重建基提交 `a08ac81`（分支 `master——ddd`），历史无法逐条还原。见 `.data/git-recovery-20260910T143815/INCIDENT.md`。
  **教训：不要用 `git stash` 演示「修复前失败」，改用临时目录副本 / git worktree / 测试内断言旧行为。**

## 2026-09-10 v3.2 复核与技能时机校准

- analogy 和 missing_measurement 本次符合要求，number 仍 partial（应 insufficient）。报告与复核已保存 docs/evidence/issue05-live-v32-20260910.json、issue05-v32-review-20260910.md。
- 下一步离线检查覆盖记录中直接答案与相关背景的混淆，不再无新改动地要求用户重复付费运行。05 仍进行中。
- 用户再次授权并强调灵活遵守技能时机；已更新 ROADMAP、development-workflow 和 HANDOFF。当前继续 diagnose；06 起正式 TDD；完整架构检查仍在 06 后、13 前，真实接口/职责痛点可提前局部检查，不机械重构。
- 累计保守记账 0.108174 元、可用 9.891826 元、无预留。本轮文档更新，无代码或助手付费调用。

## 2026-09-10 v3.1 十题汇总与 v3.2 定向修复

- 剩余六题：agreement/conflict/negation/injection 本次符合要求；analogy 只是原则复述；missing_measurement 附有效范围引用而被程序拒绝。十题合计七题符合要求，另两项语义未通过、一项程序误拒绝。
- 已先失败测试后允许 insufficient 的有效上下文引用，显式 citation_scope=missing_context，仍无答案结论；25 测试通过，run 50 离线重放通过。原报告不改写。
- v3.2 澄清纯数量缺失不能算部分回答、类比必须有具体情境，真实效果待验。下一步只复验 number/analogy/missing_measurement。详见 docs/evidence/issue05-v31-six-review-20260910.md。
- 账本累计 0.093489 元、余额 9.906511 元、无预留。本轮无助手付费调用；Issue 05 不关闭。

## 2026-09-10 v3.1 四题完整执行后的语义复核

- 四题执行完整；principle、partial、conditions 本次符合需求，引用、释义、数字缺失及条件均已核查。number 仍错误 partial：没有编造数字，但把相关原则当作纯数量问题的部分答案，应 insufficient。
- 报告保存为 docs/evidence/issue05-live-v31-20260910.json，详细复核见 issue05-v31-review-20260910.md；原报告未改写。不把一次三个场景通过当作全面修复。
- 下一步同版本补其余六题，集中处理 number 等语义失败，再定向复验。Issue 05 保持进行中，不进入 06。
- 累计保守记账 0.062625 元、余额 9.937375 元、无预留；本轮仅文档复核，无代码修改及助手付费调用。

## 2026-09-10 v3 真实验证复核与引用格式修复

- 用户最新报告只执行 principle：内嵌引用对象导致校验失败（call 10、run 26）；其余三题未执行。正文还扩大要求、将未问的操作细节判为缺失，语义不通过。
- 先新增失败回归再无损转换与已验证顶层引用完全一致的对象，冲突继续拒绝。24 测试通过；原响应离线重放得到 partial，明确不是语义修复。
- evidence-v3.1 增加完整格式示意与一般建议问题范围说明，真实效果待验；下一步定向四题。报告及复核见 docs/evidence/issue05-v3-review-20260910.md。
- 账本累计 0.042213 元，可用 9.957787 元，无预留；助手未新增付费请求。Issue 05 不关闭。

## 2026-09-10 Issue 05 离线诊断与覆盖契约修复

- 已读取交接顺序中的需求、任务和真实报告，离线复现 partial 漏第二问仍通过、conditions 状态与 missing 矛盾；原始报告保留。
- 先新增失败回归测试，再实现 evidence-v3：输入显式问题片段，模型逐项关联结论/缺失，程序汇总状态；v3 replay 同步校验覆盖。没有将所有 partial 改为 grounded。
- 22 个本地测试通过（包含十个受控场景子测试）。新增覆盖为人工测试输入，不冒充新版真实模型输出；语义覆盖仍不能仅靠结构校验保证。
- 当前进程无 API 密钥，本轮零付费调用；账本仍 spent=0.037608、available=9.962392、reserved=0。Issue 05 保持 in-progress，下一步定向真实验证；未进入 06。
- 完整原因、测试和局限见 `docs/evidence/issue05-offline-diagnosis-20260910.md`。

## 2026-09-10 最新交接与真实失败

- 新窗口入口为根目录 HANDOFF.md；用户最新真实报告已存 docs/evidence/issue05-live-20260909.json，conditions 失败正文及证据已存 docs/evidence/issue05-conditions-failure.json。
- principle/number 状态符合预期；partial 漏答数字却判 grounded；conditions 因 partial 缺 missing 校验失败，后四题未执行。Issue 05 不关闭，下一窗口先诊断已有失败。
- 核对账本累计保守记账 0.037608 元，余额 9.962392 元，无预留。本轮仅整理文档及报告，没有修改产品代码、重跑测试或付费调用。
- Git HEAD 核对为 cfc4563（9.9 23：35），未核对远程同步；早期“未提交”记录已过时。

## 最新进度：Issue 05 本地实现与验收准备

- 已调整 evidence-v2：按问题实际要求判状态，明确比较/冲突/条件/否定/类比规则；真实偏保守问题尚待新响应确认，未声称已修复语义。
- 回答阶段收到工具请求会拒绝，先失败测试后实现；16 个测试通过，包含十个受控场景子测试。
- 新增一次隐藏输入密钥的真实验证脚本及 docs/issue05-verification.md；默认只免费准备，--live 才调用。指定证据隔离生成行为，不冒充检索评测，不把参考答案提供给模型。
- Issue 05 保持 in-progress；原有十道资料题与真实语义验收待补。本轮无付费调用，累计保守记账 0.011334 元。

## 最新需求调整：文档结构适配主线

- 用户要求根据不同文档种类加强处理与切分，作为项目差异化重点；行业反馈仅作定位输入，不扩写为企业普遍结论。
- PRD 更新至 v0.2，新增 US24–29；新增 13 指南结构、14 步骤代码、15 切分对照，11 PDF 提前并扩展报告结构处理。现有编号和已完成结果保留。
- 当前下一步仍为 05，随后 06、架构检查、13/14/11、07/15，最后 08/10/12；09 可选。依赖图、任务链接与 29 条用户故事覆盖已检查。
- 必要验证保留，重点看原文跨度覆盖、前提警告完整性、引用定位与具体失败；不承诺原创算法或提升比例，预算仍为 10 元。
- TDD 触发扩展至 13/14/11，架构检查提前到 13 前；文档规范已同步。此次无代码变更或新增付费调用。

## 最新验收：Issue 04 完成

- 用户提供真实向量问答结果：call_id=3，vector-baseline answer_run_id=8。结论、正文引用和中文释义核对一致，Issue 04 标记 done。
- 原则性问题被判 partial 属于状态偏保守，已记录到 Issue 05；尚未修复，不宣称回答质量全面通过。
- 账本核对累计保守支出 0.011334 元，可用 9.988666 元，无预留；本轮无新增调用。
- 下一项 Issue 05；Issue 03 三类验收欠项保留。

## 最新进度：Issue 04 本地向量基线

- 用户报告重跑无报错；核对 run_id=11 为 live/insufficient、claims=0。结构通过不等于三类语义验收完成；用户要求继续 04，03 验收欠项保留。
- 在 .venv 安装并冻结向量依赖，pip check 通过。本地模型 revision e8f8c211226b894fcb81acc59f3b34ba3efd5f42，384 维 CPU 编码；SQLite 精确余弦检索，无付费 embedding。
- 实现 index、search/ask --retrieval vector，资料变化时拒绝旧索引并提示重建；14 个本地测试通过。
- 两份 OWASP 原文短节选与两道中文题产生实际报告 docs/vector-baseline.json，正文均命中 top5，但 top1 均为说明段；极小样本不能当作正式效果证据。向量检索到模拟回答已跑通，真实生成未运行。
- 模型加载产生 tokenizer regex 警告，影响尚未确定，需后续核对依赖与分词兼容性；记录不隐去。04 保持 in-progress。
- 已记录强制技能触发规则到 docs/development-workflow.md，链接 README、ROADMAP、领域文档和 06/08/10 任务。
- 本轮未增加 API 支出；账本累计保守支出 0.006069 元（来自用户前两次真实调用），无预留。代码未提交或推送。

## 最新诊断：Issue 03 首次真实调用校验失败

- 用户本机已发起一次真实请求。账本 call_id=1 已结算：输入 449、输出 331 token；按保守价格记账 0.004326 元，余额 9.995674 元，无未知预留。该金额不等于已核对的平台实际账单。
- 原回答记录为 run_id=9；旧代码未保存正文及具体校验错误，无法还原该次失败原因。输出未达到 800 token 上限，暂不据此增加额度。
- 已先写失败回归测试，复现错误原因被吞掉的问题，再修复为按响应结构、结束原因、JSON、引用校验分别报告错误。
- 后续失败只保存模型最终正文以支持离线 replay，排除 reasoning_content、请求头并替换当前密钥；不输出无效答案为成功结果。
- 13 个测试通过；本轮没有额外付费调用。原始失败尚未解决，需要用户以隐藏密钥方式重跑一次取得完整诊断。Issue 03 不关闭。

## 最新进度：2026-09-09 Issue 03 准备完成、等待真实验收

- 已核对官方中文价格页，选用 deepseek-v4-flash，保守按高峰未命中输入 3 元/百万 token、输出 9 元/百万 token 计账，配置附来源及日期。
- 输入预留不再使用字符估算，采用官方 1M 上下文的保守上界 1,048,576 token；单次最大暂占 3.152928 元，成功结算释放差额。
- 新增 --preflight 免费预检和 --prompt-key 本机隐藏输入；docs/live-m0.md 包含三类验收命令与人工核查点。
- 12 个本地测试通过，免费预检成功；实际支出 0、预留 0。当前进程没有密钥，真实调用未运行，Issue 03 标记 needs-info/blocked，M0 仍未完成。
- 已将 TDD 和架构技能建议使用时机写入 ROADMAP，本轮未启动这两个技能的实施流程。

## 最新进度：2026-09-09 Issue 02

- 已增加 `ask --demo`、`ask --config`、`budget`；DeepSeek 标准库适配器、中文结构化回答及原文引用校验、独立持久化预算账本已实现。
- 11 个测试通过；验证受控请求成功、预算不足不发请求、重启不清账、超时与未知用量保留预留、并发预留阻断、无效引用仍计费及日志脱敏。
- 已运行免费模拟演示。实际 API 费用 0 元，未知预留 0 元；没有验证真实模型回答、翻译或语义支持质量。
- 单次输出上限 800 token、请求输入 20000 字节、问题 2000 字符、网络超时 30 秒，无自动重试。默认配置禁止真实请求；模型价格和输入 token 预留上界需在 Issue 03 核实。
- 代码仍在工作区，未提交推送。Issue 02 已完成模拟集成验收，下一步 Issue 03；M0 整体仍未完成。

## 最新进度：2026-09-09 Issue 01

- 完成标准库 CLI：导入 Markdown、查看资料、关键词查询、读取原文片段与检索运行记录；SQLite 保存快照、元数据、稳定标识和候选耗时。
- 已运行 2 个 CLI 端到端测试并通过；自建英文样例实际导入 4 个片段，中文“提示注入”命中第 6–10 行。修正 Windows 重定向输出编码为 UTF-8。
- 当前代码在工作区，未提交或推送；Git origin 已配置为用户提供的仓库。远程读取因网络连接失败，尚未核对远程分支或文件。
- 未调用付费 API，费用 0 元。当前不是向量检索或生成式回答，M0 尚未整体完成；下一项 Issue 02。
- 以下为此前阶段的历史记录，涉及未实现的描述以本节和各 Issue 当前 State 为准。

## 2026-09-09：需求澄清

### 已确认

- 用户确认 API 来自 DeepSeek 官方开放平台，采用官方直连端点 `https://api.deepseek.com`；具体模型尚未确定，尚未进行真实调用。
- 用户确认第一阶段开发与小规模评测的 API 总预算上限为 10 元人民币；不是单次或每日额度。不得自动充值或超预算继续调用。

- 本次只推进项目一“安全知识研究助手”；继承 `E:/DSWorking/agent-project-context.md` 中的既有范围。
- 第一批资料聚焦 LLM／Agent 应用安全，覆盖提示注入、工具权限与防护设计。
- 第一版定位为帮助自己读懂资料、能够回到原文核对的学习助手。
- 回答使用容易理解的语言、附具体证据引用，资料没讲清楚时明确说明。
- 第一版事实结论仅依据已导入资料，可以通俗改写或使用明确标注的类比；资料不足时不凭模型自身知识补齐事实。
- 用户希望后续开发可丰富回答；具体扩展方式尚未决定，当前边界适用于第一版。
- 用户表示对许多相关领域和简历中的概念不熟悉。协作时先解释概念，再给出明确建议、理由和例子；不要求用户独立判断陌生技术选项。
- 用户确认可以看懂 Python 代码，开发时只需在复杂部分稍作解释；不需要逐项讲基础语法。该信息不等于已确认独立开发经验或其他工程工具熟练度。
- 用户接受由助手筛选 3–5 份适合入门的公开权威资料，并附中文导读。
- 已确认中文提问、中文回答，引用展示英文原文并附中文释义；原文作为核对依据。
- 已确认部分可回答问题的行为：回答有证据部分，并单独指出缺失信息，不整体拒答或编造缺失事实。
- 已确认资料冲突行为：并列展示说法和引用，检查资料中给出的适用条件；无法解释差异时说明分歧，不擅自裁决。

### 实际进度

- 已读取跨对话交接文档并检查工作目录：此前只有 `.git` 与 `.idea`，没有 Git 提交、实现代码、语料或评测结果。
- 已记录领域术语和已确认需求到 `CONTEXT.md`。
- 已联网核对 4 份官方资料的相关正文，整理来源、阅读重点、中文导读及练习问题到 `docs/starter-reading.md`；尚未下载完整原文、生成版本 hash 或导入索引。
- 尚未编写代码或运行测试；已确认 DeepSeek 官方服务和第一阶段 10 元 API 总预算。CLI 为最快闭环的开发默认方案，具体模型与依赖待确定。
- 已准备 `docs/acceptance-draft.md`：10 个开发验收问题、预期行为、候选证据章节和最小数据流草案；未完成快照证据标注或运行验证，不是保留测试集。
- 跨对话交接文档尚未同步本轮需求决定；本文件保留本轮最新记录。

### 下一项待澄清

- 用户要求越快越好，未给出固定截止日期；按最小 CLI 闭环优先安排。具体模型价格仍需核对，不在对话中收集密钥。

### PRD 交付

- 已根据本次会话生成根目录 `PRD.md`，覆盖用户故事、分阶段范围、模块与数据契约、10 元预算、测试和评测、非目标及实现顺序。
- 已区分用户确认规则与可调整技术默认值；首个闭环不替代完整项目范围。
- 本次仅交付需求文档，未实现或测试产品功能，未调用付费 API，未发布外部 Issue。

### Issue 路线交付

- 已将 PRD 拆成 12 个本地 Markdown Issue，入口为根目录 `ROADMAP.md`，任务位于 `.scratch/security-research-assistant/issues/`。
- 所有任务初始 Status 为 needs-triage、State 为 open；已标注 M0–M3、AFK/HITL、依赖、用户故事及可检查验收标准。没有任务已完成实现。
- 01–03 优先交付真实 M0；09 重排序是可选实验，不阻塞主线；12 负责最终保留评测与演示。
- 本地任务和领域文档约定记录在 `docs/agents/`；未创建远程 Issue，未建立外部平台连接。
- 下一步：对 01 分诊后实现一份 Markdown 原文导入、搜索与证据定位，再进入受预算保护的回答闭环。

### 模型接入核对（2026-09-09）

- 已核对 DeepSeek 官方入门文档 https://api-docs.deepseek.com/ 和工具调用文档 https://api-docs.deepseek.com/guides/tool_calls/ 。官方提供兼容 OpenAI 格式的聊天接口与工具调用；工具实际执行仍由应用程序负责。
- 建议先以现有 DeepSeek 服务承担基于证据的回答生成，具体模型可配置；尚未确认模型选择或验证账户可用性。
- 向量检索所需的文本编码方案独立选择，不能因聊天接口兼容便假定存在可用的 embeddings 接口。
- 预算实施建议（尚未实现）：所有付费模型调用合计计入 10 元上限，包含失败重试和评测；调用前按价格、输入长度及输出上限预留费用，调用后依据实际用量记账。价格或调用费用不明时不启动批量调用。优先以本地检查和少量端到端样例验证，再决定剩余额度内的评测规模，不承诺 10 元足够完成整个项目评测。
- 官方价格页本轮两次获取超时，未确认当前单价；不据此给出可调用次数或实际费用承诺。入门页已确认官方接口地址。
- 环境只读检查：发现 Python 命令位于 `E:/application/study/python/python.exe`；未验证版本。通过系统查询读取内存被拒绝，机器内存尚未知；未安装依赖或调用付费 API。


分词警告复核：检查 transformers 4.57.6 源码确认对重新保存的非 Mistral 配置存在误判。本模型 model_type=bert，已显式禁用不适用的 Mistral regex 修补；中英文样例 token ID 与保存的 tokenizer.json 一致。实际基线已重新运行，结果不变。
