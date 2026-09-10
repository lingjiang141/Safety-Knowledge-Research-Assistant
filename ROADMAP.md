# 项目推进路线

依据 [PRD v0.2](PRD.md)。现有 Issue 编号保留，新增 13–15，编号不代表执行顺序。任务仍为本地 Markdown，未迁移至 GitHub。

## 当前主线

**05 → 06 → 架构检查 → 13 → 14 → 11 → 07 → 15 → 08 → 10 → 12**。09 为可选重排序实验，不阻塞主线；
**03 三类端到端验收已于 2026-09-10 完成**（用户账单核对 + 最终语义验收达标）。

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
| [03 验证 DeepSeek 真实调用和三类回答](.scratch/security-research-assistant/issues/03-live-m0.md) | M0 | HITL | 02 | done | US4, US6, US7, US11, US12, US19, US20 || [04 中文问题检索多份英文资料并建立向量基线](.scratch/security-research-assistant/issues/04-vector-baseline.md) | M1 | AFK | 03 | done | US1, US3, US9, US14, US18, US21 |
| [05 验证比较、冲突和攻击示例的回答边界](.scratch/security-research-assistant/issues/05-evidence-cases.md) | M1 | AFK | 04 | in-progress | US5, US6, US8, US9, US10, US11, US12, US13 |
| [06 更新和删除资料后阻止旧证据进入新回答](.scratch/security-research-assistant/issues/06-version-sync.md) | M1 | AFK | 04 | open | US2, US14, US15, US16 |
| [13 按指南结构切分并展示完整证据](.scratch/security-research-assistant/issues/13-structured-guides.md) | M1D | AFK | 06 | open | US24, US27, US28 |
| [14 检索操作步骤时保留前提、代码与警告](.scratch/security-research-assistant/issues/14-procedures-code.md) | M1D | AFK | 13 | open | US25, US27, US28 |
| [11 导入文本型 PDF 并按页核对回答](.scratch/security-research-assistant/issues/11-pdf.md) | M1D | AFK | 06, 13 | open | US1, US2, US6, US7, US14, US15, US26, US27, US28 |
| [07 冻结评测样本并保存可复查的基线报告](.scratch/security-research-assistant/issues/07-eval-split.md) | M1 | HITL | 05, 06, 13, 14, 11 | open | US18, US19, US21, US22 |
| [15 用实际问题验证文档切分改良](.scratch/security-research-assistant/issues/15-chunking-comparison.md) | M2D | HITL | 07 | open | US24, US25, US26, US27, US28, US29 |
| [08 用混合检索回答同一批问题并比较基线](.scratch/security-research-assistant/issues/08-hybrid.md) | M2 | AFK | 15 | open | US3, US9, US18, US21 |
| [09 评估重排序是否值得加入回答流程](.scratch/security-research-assistant/issues/09-rerank.md) | M2 | AFK | 08 | open | US18, US19, US21 |
| [10 证据不足时最多补充检索两轮](.scratch/security-research-assistant/issues/10-bounded-search.md) | M3 | AFK | 08 | open | US11, US12, US13, US17, US18, US19, US20 |
| [12 运行保留评测并交付演示与失败复盘](.scratch/security-research-assistant/issues/12-final-eval-demo.md) | M3 | HITL | 10, 11, 15 | open | US18, US19, US21, US22, US23 |

## 阶段完成标准

- M0：01–03；**已完成**。01/02 的模拟通过不替代 03 三类真实验收，03 已于 2026-09-10 由真实端到端验收完成。
- M1：04–06；已有基线和版本一致性。04 已完成；05 进行中（受控场景已达标，原始资料题 Q01 已在 v3.5 全批通过，Q04/Q06 检索未命中欠项保留）。
- M1D：13、14、11；三类结构从导入到证据展示的完整路径。
- 07：原文跨度标注、开发/保留集冻结与基线入口。
- M2D：15；切分改良对照和适用范围，是项目展示重点。
- M2：08；09 可选。M3：10、12，最终保留评测与演示。

## 执行约定

每项完成需有演示、测试、版本和费用证据。AFK 表示常规实现可自主推进；HITL 表示需要人工核查。03 三类真实验收已于 2026-09-10 完成（含用户账单核对与最终验收）；不能以模拟通过替代真实验收，此原则继续适用于后续任务。

10 元总预算不重置；付费调用条件不具备时保留待办，不宣称完成。新切分任务目前均为 needs-triage/open；先分诊再实施。后续先读 [技能触发规则](docs/development-workflow.md)，按授权直接调用。

技能时机：06/13/14/11/10 使用 TDD；04–06 后、13 前先做 improve-codebase-architecture；08 前复核是否出现新的结构问题，不机械重复重构。

2026-09-10 再确认：上述是默认检查点，不是机械日程。当前 05 仍有原始资料题欠项（Q01 待跑、Q04/Q06 检索未命中），
继续 diagnose；可复现程序问题先写失败回归，提示词效果用真实语义验证，不能把模拟通过称为语义修复。
**用户已指示进入 03 三类端到端验收收尾**；06 仍需在实际开始时按「一个外部行为测试→最小实现→回归」的 TDD 节奏推进。

架构检查默认仍在 06 后、13 前；若修复已出现缺乏可测接口、职责耦合导致反复跨文件改动、版本规则在多个入口漂移，则提前做局部 improve-codebase-architecture 检查，不必等编号。检查不等于重构，无实际痛点时保留现状。08/10 前按新增证据复核。常规时机调整自主执行并记录依据，无需重复询问技能授权；不借此改变产品范围、预算或未完成的验收。

29 条用户故事均有任务映射。已完成 01、02、04 保留历史事实；本次只更新需求和流程，未实现新切分功能。
