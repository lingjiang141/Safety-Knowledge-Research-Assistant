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
- **08 用 diagnose（已完成）**；**06/13/14/11/07/15/08 已按 tdd 完成**；**10 仍需在开始时按 tdd**
  （对照型任务不把「指标变好」当通过条件——15 与 08 的对照部分均如此）；
  04–06 后、13 前完整 improve-codebase-architecture（**已完成**，用户裁定不重构）；
  13/14 后就 ② 做了一次**局部收敛**（`peel_metadata`）；08 前就 ⑤ 做了第二次**刻意最小收敛**（共享检索规则）。
- **TDD 调试要点（08 新增）**：BM25 排序键必须 `(kind!="body", -score, id, score)`——**body 标志在首位**，
  否则元数据片段会抢占正文槽；小语料下 IDF 极小，TF 饱和测试应断言**比率**而非「谁赢」
  （长度归一化不足以抵消 tf 1→10 是 BM25 **正确行为**，不要写成错误断言）。
- 先失败回归、再最小修复；模拟契约测试 ≠ 真实语义验证，不得混称；**结构状态命中 ≠ 语义通过**。
- 分阶段提交；更新 HANDOFF；不移动/不伪造恢复标签。用户提到的工作分支 `codex/issue05-continue`
  与标签 `checkpoint-issue05-before-handoff` 本机从未存在。
- **依赖声明改动前先核验真实依赖**：本次给 `pypdf` 编了 `pycryptodome` 依赖是错的（pypdf 无运行时依赖）。
  加依赖前用 `importlib.metadata.distribution(x).requires` 查实际 Requires-Dist，不要凭印象写锁文件。

## 当前进度快照（2026-09-10，Issue 12 done，主线全部收口）

- **Issue：01/02/03/04/05/06/07/08/10/11/12/13/14/15 全部 done**（均 2026-09-10）；09 可选、未采用。
- 主线全部完成。**M0/M1/M1D/M2D/M2/M3 里程碑全部完成**。
- 当前提示词 **evidence-v3.5**，输出上限 **1500** token（常量 `OUTPUT_TOKEN_LIMIT`），单次最大预留 3.159228 元。
- 本地 **148 tests 通过**。
- **账本（保守记账，最终）**：`0.5175` 元已用、可用 `9.4825`、预留 0、blocked=false（12 新增 0.046104，4 次生成调用）。
- **12 保留评测与演示（done）**：
  - **先修真实缺陷**：`run_baseline(..., holdout=...)` 加载保留集却**只评 dev**、`sample_kind` 硬编码
    `"development"` → 会把 dev 分数挂在保留集标题下。TDD：先写 `FinalHoldoutEvaluationTest`（4 例，3 红）
    → 最小修复（`kind` 推导/校验、`cases = loaded.holdout if kind=="holdout"`、报告 `sample_kind`/
    `evaluated_case_ids`、过滤过时 `not_run`）→ CLI 传 `kind`。
  - **保留集首次开封**：`docs/evidence/issue12-holdout-baseline-20260910.json`，`sample_kind="holdout"`、
    `evaluated_case_ids=[H01…H10]`、**`recall_at_5=0.75`**（dev 0.85）、`broken_bundles=0`。
    **未因结果改代码或提示词。**
  - **四例检索缺口 = "排序未进前 5"**（覆盖块存在，非"资料没有"），根因 `heading-lines-v1:20` 的 18–20 行粗块：
    保留集 H03 0.50 / H04 0.00 / H09 0.00 + 生成侧 Q06 partial（含「最小权限」的块 `L36-55` 在 Q06 下排第 5、
    `k=3` 门外）。**交接 13/14/11 结构适配，不改固定检索器、不放宽预期。**
  - **切分取舍已定（免费离线）**：保留集三策略对照 `scripts/compare_splitters_holdout.py`，
    基线 0.750 / `heading-block-v2` 0.750（+0.000）/ `heading-procedure-v3` 0.600（−0.150，退化 H02/H03）。
    **无一优于基线 → 维持 `heading-lines-v1:20` 默认**；四例缺口的答案是「段落内部短句 / 清单单条」，
    现有切分无法在不伤其他题的前提下救回 → **当前切分能力的真实边界，记为已知局限**。
  - **演示 `scripts/demo.py`**（约三分钟，免费离线；`--live` 才付费）：切分预览 / 同题前后证据 / 失败复盘 /
    边界 / 生成回执。踩坑：`answer(preflight=True)` 密钥检查在预留分支之前 → 须传已核实 config（可不传 key）；
    中文问句对英文语料 `store.search` 零命中 → 生成步骤用英文问题；③ 措辞「未命中」→「未取全」并逐例打印 `recall_at_5`。
  - **生成侧复核（② 用户裁定通过）**：4 题 Q05/Q06/Q08/Q09（grounded/partial/insufficient/partial）。
    Q05 ✅、Q08 ✅（0 结论无数字）、Q09 ✅；Q06 partial ❌ 归因检索缺口（非生成缺陷）。样本 4 题**不构成指标**。
  - **关键区分（用户主张并确认）**：**行为 vs 度量两条轴**。取到部分时系统照常返回部分答案（`status=partial`）；
    `recall_at_5` 衡量「检索有没有取全」，非「系统有没有作答」。**不在已开封保留集上放宽规则。**
  - **⑤ 三态**：已完成 / 故意可选（09、结构适配移交、正式指标以 4 题行为复核代替）/ **预算所致未完成：无**。
  - 证据：`docs/evidence/issue12-holdout-and-failures-20260910.md`、`issue12-generation-review-20260910.{md,json}`。
- **10 有界补充检索（done，TDD + 对照型）**：
  - 前置针对架构发现 ③④ 局部复核，`answer()` 实测 **120 行**；**结论=新增窄接口 `skra/orchestrate.py`，不重写 `answer()`**。
  - `MAX_SUPPLEMENTARY_ROUNDS = 2`（初次不计）；`StopReason` 六值
    `sufficient`/`no_new_evidence`/`round_limit`/`timeout`/`error`/`budget`。
  - `Orchestrator` 只做迭代与停止判定：`answer_once(evidence, round_no)` 回调 + `is_sufficient` 谓词解耦，
    `last_result` 保存最近回调产物；不生成回答。
  - **参数边界复用 `check_search_args`（不制造第四份守卫，发现 ⑤）**；`_vet_candidates` 拒绝带
    `tool`/`tool_call`/`function_call`/`arguments` 的候选与无 `id` 候选；无联网/写入参数（未知 kwarg → `TypeError`）。
  - `bounded_answer()`（`skra/answer.py`）每轮以**累积证据**作答；`store.amend_run()` 把 supplement 写入
    **答案自己的 run**（不追加新行）。**注意：`answer_run_id` 不写入自身 run 记录（既有行为，`record_run`
    在 id 赋值前序列化），测试按真实行为断言。**
  - **开发集开关对照**（`scripts/compare_supplement.py`，免费离线）：`off` 单次 top-k；
    `on` 同查询静态语料 → **10 题全 `no_new_evidence`、无增益（正确行为：不会凭空造证据）**；
    `widening` 逐轮放宽 k → **10 题全 `round_limit`（两轮上限确实 bind）**；两臂 `lost_cases` 恒空
    （**结构性质，非效果证据**）。生成侧效果**未测**。详见 `docs/evidence/issue10-bounded-search-20260910.md`。
- **08 检索对照（done，TDD + 对照型）**：`scripts/compare_retrievers.py`（免费离线）。
  **一次只改检索器**，三路跑同一 DB、同一份片段。**结果（束级 Recall@5，开发集 D01–D10）**：
  `vector` 0.850 / `bm25` **0.400（−0.450）** / `hybrid-rrf` **0.750（−0.100）**。**有利案例为无。**
  ① 中英词项错配：4/10 用例（D04/D05/D06/D10）纯词项检索**零候选**，是 BM25 −0.450 主因；
  ② 融合失效模式：D09 唯一标注束由单片段 `1e8bc828` 覆盖（向量排第 5），而「词面相似但跨度错误」的
  `e9312b2a` 同时拿 BM25 第 1 + 向量第 9 → 被 RRF 抬到第 2，挤掉正确目标。**一致 ≠ 正确**；
  ③ D04/D07 是切分/跨资料排序问题，融合补不上缺失的束 → 交 11/14 结构适配。
  新增 `skra/bm25.py`（Okapi，`k1=1.5`/`b=0.75`，**body 优先排序键 `(kind!="body", -score, id, score)`**）、
  `skra/fusion.py`（RRF `K=60` 等权，**只读排名不合并分数尺度**、**拒绝融合已失效片段**）。
  **架构发现 ⑤ 前置复核后做了刻意最小收敛**：共享规则收进 `skra/store.py`
  （`check_search_args`/`active_chunk_ids`/`record_run`/`search_terms`/`TOKEN_RE`/`BM25_K1`/`BM25_B`/`RRF_K`），
  `INSERT INTO runs` 实测重复 **5 处**（比记录的 4 处更多）。**等价性逐字节证明**：
  收敛前后 keyword 哈希均为 `010e9ca4a50a37fc936dc11c2dce8bf43b68a5d0cf07c4af3f82df9a8480ea04`。
  详见 `docs/evidence/issue08-retriever-comparison-20260910.md`。
- **15 切分对照（done，对照型 + 一处缺陷修复）**：`scripts/compare_splitters.py`（免费离线，
  `--preview` 导出切分预览与原文前后对照）。**一次只改一个因素（切分器）**，其余全冻结；
  每策略从**同一批快照**建独立 SQLite（不做「重导入基线」这种污染对照的操作）。
  **结果（开发集 D01–D10，向量检索 k=5，每策略内嵌 `k` 与语料哈希）**：
  基线 0.850 / 1979.3 tok；`heading-block-v2` **0.900 / 1920.7**（+0.050，提升 D07，无退化）；
  `heading-procedure-v3` **0.400 / 398.3**（−0.450，退化 D05–D09）；`pdf-pages-v1` **未对照**（语料无 PDF）。
  **修复 procedure 元数据误标缺陷**：正文行被标 `kind=metadata`（元数据 11 → 3）。根因两段在
  `_chunk_procedure`：① 标注阶段无标题续段继承 `(说明性元数据)` 标签；② 合并阶段无条件并入元数据单元。
  **指南策略 `_chunk_structured` 无此 bug**（有 `is_metadata_block` 双重保险）——架构发现 ② 的价值佐证。
  详见 `docs/evidence/issue15-splitter-comparison-20260910.md`。
- **07 评测基线（done，按 tdd）**：新增 `skra/eval.py` + CLI `eval` 子命令。
  标注锚在**原文跨度 + 必须共同出现的条件**（不用片段 id，因为片段 id 随切分策略变化会让 Recall 不可比）；
  `recall_at_5` 分母是**标注的证据束数**；`required_together` 的束被切开记 `broken` **不算命中**；
  开发/保留集四层隔离（分文件 / 文件 `kind` 权威 / 默认入口不可达 / 测试守卫）；
  冻结 `sample_hash`/`corpus_hash`/`splitter`/`encoder`/逐文档 hash。
  开发集 10 题（`examples/eval-dev-cases.json` D01–D10）向量检索 **`recall_at_5 = 0.85`**，
  **D04（0/3 束）、D07（1/2 束）未命中**（与 Q04/Q06 同源）；无 broken 束 = 缺口全来自排序未进前 5。
  `network_called=false`、`billed_calls=0`、`complete=false`、`not_run` 三条、`manual_review="pending"`。
  **保留集 `examples/eval-holdout-cases.json`（H01–H10）封存至 Issue 12，调参期间不得打开。**
  详见 `docs/evidence/issue07-baseline-and-freeze-20260910.md`。
- **11 PDF 导入（done，按 tdd 11 循环）**：新增 `skra/pdf.py`（`pdf-text-v1`，pypdf 纯文本层，不执行文件内容）；
  新策略 `pdf-pages-v1`；chunks 增 **`page` 列**（1 基，Markdown 为 NULL）；重复页眉页脚判
  `kind=metadata`（保留可查、不占正文名额）；跨页段落**不合并**；扫描件/无文本层/阅读顺序混乱
  **明确抛错不静默降级**；无 OCR / 不做复杂表格 / 不做双栏重建（严格守 PRD 4.4 边界）。
  夹具 `scripts/make_pdf_fixtures.py` 直接生成 PDF 语法（无额外依赖）。
  详见 `docs/evidence/issue11-pdf-tdd-20260910.md`。
- **依赖**：`pypdf==6.18.0` 已写入 `pyproject.toml`（`dependencies`）与 `requirements-vector.lock.txt`；
  pypdf **无运行时依赖**（纯 Python），锁文件只加这一行。
- **14 步骤/代码切分（done）**：新增 `heading-procedure-v3`；**围栏代码原子化**（先标记围栏区域
  再识别标题，故代码内 `#` 注释不冒充标题）；围栏片段标签 `代码（…）`；前提/警告与步骤同块；
  无标题文档回退基线 + `splitter_note`。调试中修复 3 个真实缺陷：围栏内 `#` 误判标题、
  标题链合并塌陷（9→1 片段）、peel 循环变量 `start` 遮蔽。
  详见 `docs/evidence/issue14-procedures-tdd-20260910.md`。
- **13 结构切分（done）**：新增 `heading-block-v2`（保留 `heading-lines-v1:20` 基线）；
  标题分块、列表引导行与项不拆；`kind=metadata` 标记 Source/License 前言且默认不占正文检索名额；
  无标题文档自动回退基线 + `splitter_note`；CLI `--splitter` 可覆盖。真实语料 Q04 定义段
  向量排名 **2→1**（L1–18→L9–18）；**Q06 跨资料仍第 4 未改善**（留待 11）。
  详见 `docs/evidence/issue13-structured-guides-tdd-20260910.md`。
- **06 版本一致性（done）**：`update`/`delete` CLI 子命令；chunks 增 `version`/`active` 列；
  更新=新版本失效旧版（PRD 4.3）；`answer.revalidate` 阻止回答期间证据失效的过时答案；
  向量索引仅取 active。旧库自动 `ALTER TABLE` 迁移。详见 `docs/evidence/issue06-version-sync-tdd-20260910.md`。
- **架构检查（done，用户裁定不重构）**：5 项「规则被复制」摩擦点记录于
  `docs/evidence/architecture-review-20260910.md`（①提示词版本白名单漂移 ②切分不变量分散
  ③answer()巨函数 ④revalidate 可注入性 ⑤两检索器规则重复）。
  **13/14 新增两个策略后 ②⑤ 进一步放大**；**2026-09-10 已就 ② 做局部收敛**：
  元数据剥离抽为模块级纯函数 `peel_metadata(lines, units)`，两策略共享，
  等价性经三重证明（160 例对拍 0 不一致 + 142 片段指纹逐字节相同 + 回归护栏实测）。
  ⑤检索规则重复与 ③巨函数**仍保留**，待 08 前按新证据复核。
  见 `docs/evidence/issue14-followup-peel-metadata-20260910.md`。
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
- **② 已部分收敛（2026-09-10）**：元数据剥离抽为 `peel_metadata`，两策略共享（三重等价证明）。
  **15 已验证 ② 的价值**：procedure 的元数据误标正是两条各自演化的标注/合并规则所致。
- **⑤ 已在 08 前收敛（2026-09-10）**：把共享检索规则收进 `skra/store.py`
  （`check_search_args` / `active_chunk_ids` / `record_run` / `search_terms` / `TOKEN_RE` / 参数常量），
  keyword 检索行为**逐字节不变**（哈希证明）；新增防回潮守卫 `tests/test_shared_retrieval_rules.py`（白名单仅 `store.py`）。
  **注意**：`store.search` 有「正文优先于 metadata」排序、`vector.search` 仍**没有**——该差异仍开放
  （融合层已被告知此事，未强行对称化）。
- **07 新增一处待复核**：`skra/eval.py` 的 `resolve_span` 直接读 `chunks` 表（按行范围覆盖 + `active=1`），
  与 `store.search` / `vector.search` 各自维护的 active/装配规则存在耦合。
  **15 与 08 对照中均未观察到需同步改动**；10 前按新证据复核即可。
- ③巨函数、①版本白名单、④revalidate 可注入性**仍保留**。

## 评测契约（Issue 07，务必遵守）

- **标注锚在原文跨度**，形如 `{source, start_line, end_line, must_include, required_together}`；
  **永不用片段 id**。片段 id 是切分策略的函数，锚在它上面会让 Recall 跨策略不可比（PRD 5.3）。
- **Recall@5 分母是标注的证据束数**，不是片段数；切分策略改变时分母不动。
- **`required_together=true` 的束必须全部覆盖片段都被检索到才算命中**；
  只取到一部分 → 记 `broken`，**不算命中**。把被切开的束算命中＝奖励本该抓的失败。
- **开发/保留集四层隔离**：① 分文件；② 文件自身 `kind` 字段权威（保留集改名当开发集也拒）；
  ③ `load_sample(dev)` / `run_baseline(...)` 默认 `holdout=None` 不可达；④ 测试守卫。
- **保留集 `examples/eval-holdout-cases.json` 封存至 Issue 12，调参期间不得打开**；
  如因本体 bug 需要接触，须先记录理由并重跑冻结。
- **失效标注 ≠ 零分**：跨度匹配不上语料时记 `failed_cases`、`recall_at_5=None`、**不进平均**。
- **`estimate_tokens` 是字符数/4 的确定性估算，不是真实分词计数**，报告必须标注。
- **未运行项必须显式声明**（`complete=false` + `not_run`），不得让报告看起来完整而静默跳过。

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
- 测试：`.\.venv\Scripts\python.exe -m unittest discover -s tests -v`（当前 **144 tests**）
- 账本：`python -m skra budget`；离线重放：`python -m skra --db <db> replay <run_id>`
- 受控边界：`python scripts/check_boundaries.py`（免费）/ `--live`（付费）
- 原资料验收：`python scripts/check_acceptance.py`（免费）/ `--live`（付费）/ `--live --case Q01`（定向）
- 资料版本管理（06）：`python -m skra update <file> --source <src>` / `python -m skra delete <src>`
- PDF 导入（11）：`python -m skra import <file.pdf> ...`，需 `.venv`（pypdf）；切分策略自动选 `pdf-pages-v1`，
  可用 `--splitter` 覆盖；`page` 列 1 基、Markdown 为 NULL
- PDF 夹具：`python scripts/make_pdf_fixtures.py`（免费，无额外依赖）
- **评测基线（07，免费离线，不记账）**：
  `./.venv/Scripts/python.exe -m skra eval --exclude <夹具doc_id> --out <报告路径>`
  选项：`--sample`（默认开发集）、`--holdout`（**显式才打开保留集**）、`--retrieval keyword|vector`、
  `--k`（默认 5）、`--exclude`（可重复；剔除项写入报告，否则基线不可复现）
- **切分策略对照（15，免费离线，不记账）**：
  `./.venv/Scripts/python.exe scripts/compare_splitters.py --out <报告> --preview <预览>`
  选项：`--splitter`（可重复；默认三个 Markdown 策略）、`--k`（默认 5）、`--context`（预览前后行数）、`--json`
  注意：`pdf-pages-v1` 不在默认对照集内（语料无 PDF、不能切 Markdown），报告 `not_run` 已声明
- **检索方式对照（08，免费离线，不记账）**：
  `./.venv/Scripts/python.exe scripts/compare_retrievers.py --out <报告>`
  选项：`--mode`（可重复；`vector`/`bm25`/`hybrid-rrf`，默认三种）、`--k`（默认 5）、`--splitter`、`--json`
  中英错配量化：`python scripts/measure_term_mismatch.py`（免费）
- **补充检索开关对照（10，免费离线，不记账）**：
  `./.venv/Scripts/python.exe scripts/compare_supplement.py --out <报告>`
  三臂 `supplement-off` / `supplement-on`（同查询静态语料）/ `supplement-widening`（逐轮放宽 k）；
  选项：`--k`（默认 5）、`--splitter`、`--json`
- **编排模块（10）**：`skra/orchestrate.py` 的 `Orchestrator(search, answer_once, is_sufficient=, budget_guard=, deadline=)`；
  `execute(query, required_ids=(), limit=5)` 返回 `stop_reason`/`stop_detail`/`supplementary_rounds`/`evidence`/`trace`/`elapsed_ms`。
  集成入口 `skra.answer.bounded_answer(...)`；持久化 `skra.store.amend_run(db, run_id, extra)`
- **BM25 参数**：`k1=1.5`、`b=0.75`（`store.BM25_K1`/`BM25_B`）；**RRF**：`K=60` 等权（`store.RRF_K`）
