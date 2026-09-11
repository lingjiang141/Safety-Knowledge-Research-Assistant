# 项目推进路线

依据 [PRD v0.2](PRD.md)。现有 Issue 编号保留，新增 13–15，编号不代表执行顺序。任务仍为本地 Markdown，未迁移至 GitHub。

## 当前主线

**05 → 06 → 架构检查 → 13 → 14 → 11 → 07 → 15 → 08 → 10 → 12**。09 为可选重排序实验，不阻塞主线；
**03、05、06、13、14、11、07、15、08、10 均已于 2026-09-10 完成**；**架构检查已完成（用户裁定本次不重构，见
`docs/evidence/architecture-review-20260910.md`）**。**12 已完成（done）**：保留集首次开封评测 `recall_at_5=0.75`（dev 0.85），
演示脚本跑通，三例真实失败（+ Q06）已定位；**生成侧 4 题经用户逐题裁定通过**；
五项验收全部满足，**无预算耗尽**。证据见 `docs/evidence/issue12-holdout-and-failures-20260910.md`
与 `issue12-generation-review-20260910.md`。**主线 12 条 Issue 全部完成（09 为可选，未采用）。**

优先突出文档处理：指南保留定义与条件，步骤/代码保留前提与警告，文本报告保留章节与页码。先固定检索器验证切分，再考虑混合检索。必要验证保留，不堆指标、不预设创新或提升。

### 03 收尾结果（2026-09-10 已完成）

03 的三类端到端验收 = 有据 / 无据 / 部分有据三类真实回答，已完成：

- 全批 `check_acceptance.py --live` 十题跑完（`complete=True`，8/10 状态命中）。
- 三类代表题通过：Q02/Q05（有据 grounded）、Q08（无据 insufficient，未编造数字）、
  Q09（部分有据 partial，概念按原文、百分比单列缺失）。
- 助手逐题语义复核 + 用户平台账单核对（一致，0.471396 元）+ 用户最终语义验收达标。
- 证据：`docs/evidence/issue03-acceptance-live-v35-full-20260910.json`、
  `issue03-acceptance-review-v35-full-20260910.md`。
- 遗留 Q04/Q06 检索未命中欠项转 Issue 05 与 13/14/11 结构适配。

## 任务清单

| Issue | 阶段 | 类型 | 依赖 | 状态 | 用户故事 |
| --- | --- | --- | --- | --- | --- |
| [01 导入一份 Markdown 并查询原文](.scratch/security-research-assistant/issues/01-import-search.md) | M0 | AFK | 无 | done | US1, US2, US3, US7, US18, US23 |
| [02 在预算保护下生成带引用的中文回答](.scratch/security-research-assistant/issues/02-budget-answer.md) | M0 | AFK | 01 | done | US4, US5, US6, US7, US8, US19, US20 |
| [03 验证 DeepSeek 真实调用和三类回答](.scratch/security-research-assistant/issues/03-live-m0.md) | M0 | HITL | 02 | done | US4, US6, US7, US11, US12, US19, US20 |
| [04 中文问题检索多份英文资料并建立向量基线](.scratch/security-research-assistant/issues/04-vector-baseline.md) | M1 | AFK | 03 | done | US1, US3, US9, US14, US18, US21 |
| [05 验证比较、冲突和攻击示例的回答边界](.scratch/security-research-assistant/issues/05-evidence-cases.md) | M1 | AFK | 04 | done | US5, US6, US8, US9, US10, US11, US12, US13 |
| [06 更新和删除资料后阻止旧证据进入新回答](.scratch/security-research-assistant/issues/06-version-sync.md) | M1 | AFK | 04 | done | US2, US14, US15, US16 |
| [13 按指南结构切分并展示完整证据](.scratch/security-research-assistant/issues/13-structured-guides.md) | M1D | AFK | 06 | done | US24, US27, US28 |
| [14 检索操作步骤时保留前提、代码与警告](.scratch/security-research-assistant/issues/14-procedures-code.md) | M1D | AFK | 13 | done | US25, US27, US28 |
| [11 导入文本型 PDF 并按页核对回答](.scratch/security-research-assistant/issues/11-pdf.md) | M1D | AFK | 06, 13 | done | US1, US2, US6, US7, US14, US15, US26, US27, US28 |
| [07 冻结评测样本并保存可复查的基线报告](.scratch/security-research-assistant/issues/07-eval-split.md) | M1 | HITL | 05, 06, 13, 14, 11 | done | US18, US19, US21, US22 |
| [15 用实际问题验证文档切分改良](.scratch/security-research-assistant/issues/15-chunking-comparison.md) | M2D | HITL | 07 | done | US24, US25, US26, US27, US28, US29 |
| [08 用混合检索回答同一批问题并比较基线](.scratch/security-research-assistant/issues/08-hybrid.md) | M2 | AFK | 15 | done | US3, US9, US18, US21 |
| [09 评估重排序是否值得加入回答流程](.scratch/security-research-assistant/issues/09-rerank.md) | M2 | AFK | 08 | open | US18, US19, US21 |
| [10 证据不足时最多补充检索两轮](.scratch/security-research-assistant/issues/10-bounded-search.md) | M3 | AFK | 08 | done | US11, US12, US13, US17, US18, US19, US20 |
| [12 运行保留评测并交付演示与失败复盘](.scratch/security-research-assistant/issues/12-final-eval-demo.md) | M3 | HITL | 10, 11, 15 | done | US18, US19, US21, US22, US23 |

## 阶段完成标准

- M0：01–03；**已完成**。01/02 的模拟通过不替代 03 三类真实验收，03 已于 2026-09-10 由真实端到端验收完成。
- M1：04–06；**已完成**。04、05、06 均于 2026-09-10 完成（05 受控十题 v3.3 全部符合要求；原资料十题 v3.5 全批通过主要题项，Q04/Q06 检索欠项转 13/14/11；06 版本一致性按 tdd 完成）。
- M1D：13、14、11；三类结构从导入到证据展示的完整路径。13 已完成（结构切分 + 元数据区分 +
  未知结构回退；Q04 定义段排名 2→1）。14 已完成（步骤/代码策略：围栏原子化、前提与警告
  与步骤同块；修复围栏内 `#` 误判标题、标题链塌陷、变量遮蔽三个缺陷）。11 已完成
  （PDF 文本层按页提取，chunk 带 1 基 `page` 字段；重复页眉页脚判为 `metadata` 保留可查、
  不占正文名额；跨页段落不合并；扫描件/无文本层/解析失败明确报错而非静默降级；无 OCR、
  不做复杂表格与双栏重建，严守 PRD 边界）。
- 07：已完成（2026-09-10）。评测锚在**原文跨度 + 必须共同出现的条件**，不锚片段 id；
  开发集/保留集双重隔离；`skra eval` 跑开发集基线，报告含冻结 hash、逐题行、未运行项。
  开发集 10 题向量检索 `recall_at_5 = 0.85`（D04/D07 未命中，属已知检索缺口），
  `network_called=false`、`billed_calls=0`、`complete=false`。
  生成侧指标与保留集执行按设计未运行；保留集 H01–H10 已创建但封存至 12。
  证据：`docs/evidence/issue07-baseline-and-freeze-20260910.md`。
- M2D：15（**已完成**）；切分改良对照和适用范围，是项目展示重点。
  `heading-block-v2` recall@5 0.850 → 0.900（提升 D07，无退化）；`heading-procedure-v3` 0.850 → 0.400
  （退化 D05–D09，粒度过碎）；`pdf-pages-v1` 未对照（语料无 PDF）。修复 procedure 元数据误标缺陷。
  证据：`docs/evidence/issue15-splitter-comparison-20260910.md`。
- M2：**08、10（均已完成）**——08 在可用问答与评测路径增加 BM25 与 RRF，保持纯向量模式可选，
  对固定开发集比较效果。**结果：无净提升**——BM25 recall@5 0.850 → 0.400（−0.450，4/10 用例中英词项错配零候选），
  RRF 融合 0.850 → 0.750（−0.100，修回 BM25 的 D05/D06/D10，但 D09 被「词面相似但跨度错误」的片段挤掉）。
  如实记录为负面结果，未做参数拟合。09 可选重排序实验。
  10 有界补充检索（最多两轮 + 六种停止原因）——开发集开关对照：同查询静态语料下 10 题全
  `no_new_evidence`、无增益（**正确行为：不会凭空造证据**）；加宽臂 10 题全 `round_limit`
  （**两轮上限确实 bind**）；两臂 `lost_cases` 恒空为结构性质。生成侧效果未测。
  证据：`docs/evidence/issue10-bounded-search-20260910.md`、`issue10-supplement.json`。
  M3：12，最终保留评测与演示。08 的证据表明：**瓶颈在切分粒度与跨资料排序（D04/D07），
  不在检索路数**；10 的对照进一步表明补充检索亦非本语料的增益来源。
  **12 已完成**：修复 `run_baseline` 保留集误评缺陷后，保留集首次评测 `recall_at_5=0.75`（dev 0.85）、
  `broken=0`；四例检索未取全（H03/H04/H09 + Q06）均为"覆盖块存在但排序未进前 5"，交接 13/14/11 结构适配；
  演示脚本跑通；生成侧 4 题经用户裁定通过；五项验收全满足、无预算耗尽。
  证据 `docs/evidence/issue12-holdout-and-failures-20260910.md`、`issue12-generation-review-20260910.md`。

## 执行约定

每项完成需有演示、测试、版本和费用证据。AFK 表示常规实现可自主推进；HITL 表示需要人工核查。03 三类真实验收已于 2026-09-10 完成（含用户账单核对与最终验收）；不能以模拟通过替代真实验收，此原则继续适用于后续任务。

10 元总预算不重置；付费调用条件不具备时保留待办，不宣称完成。**01–08、10、11、13、14、15 及 12 全部 done；09 为可选、未采用**。后续先读 [技能触发规则](docs/development-workflow.md)，按授权直接调用。

技能时机：TDD 阶段为 06/13/14/11/07/15/10（**06/13/14/11/07/15 已完成，均按 tdd**；10 继续按 tdd）；04–06 后、13 前先做 improve-codebase-architecture（**已完成**，2026-09-10，用户裁定保留现状，见 `docs/evidence/architecture-review-20260910.md`）；**13/14 后已做一次局部收敛**（②切分不变量中的元数据剥离抽为共享纯函数 `peel_metadata`，见 `docs/evidence/issue14-followup-peel-metadata-20260910.md`），**08 前就 ⑤ 做了第二次刻意最小收敛**（共享检索规则 `check_search_args`/`active_chunk_ids`/`record_run`/`search_terms` 收进 `store.py`，等价性逐字节证明，见 `docs/evidence/issue08-retriever-comparison-20260910.md`）；③巨函数仍保留；**10 前按新增证据复核，不机械重复重构**。
**15 已验证 ② 的价值**：`_chunk_procedure` 的元数据误标正是两条各自演化的标注/合并规则所致（指南策略有
`is_metadata_block` 双重保险，procedure 没有），已按「先失败回归 → 最小修复」处理并固化测试。
**07 新增一处待复核**：`skra/eval.py` 的跨度解析直接读 `chunks` 表（按行范围覆盖），与 `store.search` / `vector.search`
各自维护的 active/装配规则存在耦合；15 对照中未观察到随切分策略变化而需要同步改动，08 前再确认。

**最新发现（2026-09-10，Issue 11 期间）**：`store.search` 有正文优先于元数据的排序规则，`vector.search` 没有；
PDF 的页面装饰行成为常规 `metadata` 片段后更容易触发这个差异。已加护栏测试固化当前期望，未顺手改检索器，
留待 **08 前**与⑤一并按新增证据处理。

2026-09-10 再确认：上述是默认检查点，不是机械日程。05 的原始资料题欠项（Q04/Q06 检索未命中）已在 03 全批
`--live` 与 07 基线中复现（D04 0/3、D07 1/2），是**同一处已知检索缺口**，已转 15 的切分对照处理：
**D07 被指南结构救回（0.50 → 1.00），D04 在三策略下均为 0.00**（procedure 下是标注单元与切分粒度错配，
基线/指南下是排序未进前 5），仍记为诚实缺口，转 12 前的结构适配复核；
可复现程序问题先写失败回归，提示词效果用真实语义验证，不能把模拟通过称为语义修复。
**08 已完成**（2026-09-10）：架构发现 ⑤ 复核后做刻意最小收敛（共享检索规则，等价性逐字节证明）；
  新增 BM25 与 RRF 融合，三路对照**无净提升**（BM25 −0.450、RRF −0.100），如实记录为负面结果。
  证据：`docs/evidence/issue08-retriever-comparison-20260910.md`。
**10 已完成**（2026-09-10）：前置针对发现 ③④ 的局部复核，结论为新增窄接口 `skra/orchestrate.py`
  （`MAX_SUPPLEMENTARY_ROUNDS=2` + `StopReason` 六值），**不重写 `answer()`**；复用 `check_search_args`
  不制造第四份参数守卫（发现 ⑤）。开发集开关对照如实记录同查询无增益、加宽臂两轮上限 bind。
  证据：`docs/evidence/issue10-bounded-search-20260910.md`、`issue10-precheck-orchestration-20260910.md`。
  **下一步进入 12**（最终保留评测与演示）；12 依赖 10/11/15，**均已 done**。

架构检查默认仍在 06 后、13 前；若修复已出现缺乏可测接口、职责耦合导致反复跨文件改动、版本规则在多个入口漂移，则提前做局部 improve-codebase-architecture 检查，不必等编号。检查不等于重构，无实际痛点时保留现状。08/10 前按新增证据复核。常规时机调整自主执行并记录依据，无需重复询问技能授权；不借此改变产品范围、预算或未完成的验收。

PRD 中 29 条用户故事均有任务映射。已完成 01、02、04 保留历史事实；本次只更新需求和流程，未实现新切分功能。
