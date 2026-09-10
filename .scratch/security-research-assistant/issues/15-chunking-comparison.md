# 15 — 用实际问题验证文档切分改良

Status: done
State: closed
Type: HITL
Milestone: M2D
User stories: US24, US25, US26, US27, US28, US29
Source: [PRD](../../../PRD.md)

## What to build

在同一组原文、查询与检索器上对照固定行数基线和结构适配方案，展示正文证据是否更完整、是否更少被元数据干扰，以及哪些文档仍处理不好。

## Acceptance criteria

- [x] 分别覆盖指南、步骤/代码、文本型报告三类；使用超过短节选规模的合法全文或代表性长片段，记录采样局限。
      → 指南（3 份 OWASP 指南散文段）、步骤/代码（LLM06 第 1–8 条编号措施）、文本型报告（指南散文段代表）。
      **采样局限已记录：语料仅 3 份 Markdown（81/86/50 行）、无围栏代码、无独立长篇报告**；见证据文档 §6.3。
- [x] 人工先标注原文证据跨度及必须一同出现的前提/警告；标注不依赖任何策略生成的 chunk ID。
      → 复用 07 冻结的 `examples/eval-dev-cases.json` 行跨度标注（`start_line/end_line/must_include/required_together`）。
- [x] 固定编码模型、检索器、top-k、生成配置及总证据 token 预算；切分改变之外不同时加重排序或翻译。
      → 编码器（MiniLM-L12-v2, `e8f8c211…`）、本地向量检索、k=5、开发集问题/标注全部冻结；
      每策略从同一批快照建独立 DB（`materialise`），报告记录每策略语料哈希。
- [x] 按原文跨度覆盖率、证据完整性、元数据占位及原文定位正确性核查；跨策略不能用 chunk 数或 chunk ID 直接比较 Recall。
      → Recall 锚在**原文行跨度**，分母恒为标注**证据束数**；`required_together` 束部分取回记 `broken` 不算命中；
      报告含 `metadata_chunks`；`--preview` 导出切分预览与原文前后对照供逐字自查。
- [x] 保存切分预览、查询、候选与原文前后对照；报告至少一项退化或局限，不以虚构失败凑数，没有观察到退化则说明样本不足。
      → `docs/evidence/issue15-splitter-preview-20260910.json`（215 片段含前后文）。
      **两项局限**：① procedure-v3 的 −0.450（真退化）；② D04 三策略皆 0.00（标注单元与切分粒度错配）。
- [x] 开发集用于调整；保留集不在此调参或提前查看，最终验收在 12。选择保留、回退或局部启用的规则有具体证据。
      → 全程只用开发集；**保留集未打开**。规则：指南结构零风险采用（+0.050 无退化）/ 步骤结构本语料不采用（−0.450）。
- [x] 演示突出可解释工程改良，不声称学术首创或普遍企业需求；预算不足则继续本地检索验证，真实生成部分标记未运行。
      → 对照全程免费离线（`network_called=false`、`billed_calls=0`）；生成侧指标与保留集写入 `not_run`；
      结论限定在「本语料 + 本编码器 + top-k=5」。

## Blocked by

- [x] [07-eval-split](07-eval-split.md)（done）

## Completion evidence

**已实现并交付。** 证据：`docs/evidence/issue15-splitter-comparison-20260910.md`（验收证据）、
`issue15-splitter-comparison-20260910.json`（原始对照报告）、`issue15-splitter-preview-20260910.json`（切分预览）。

- **代码**：`scripts/compare_splitters.py`（新增，含 `--preview`）；`skra/store.py`
  （修复 `_chunk_procedure` 标注与合并两处，正文不再被误标为元数据）。
- **语料版本**：3 份 OWASP 快照（LLM01 81 行 / LLM06 86 行 / cheatsheet 50 行）；
  编码器 `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` revision `e8f8c211…`。
- **演示命令**：
  ```bash
  .venv/Scripts/python.exe scripts/compare_splitters.py \
    --out docs/evidence/issue15-splitter-comparison-20260910.json \
    --preview docs/evidence/issue15-splitter-preview-20260910.json
  ```
- **测试**：**98 tests 通过**（93 → 98；新增 `tests/test_split_labels.py` 4 例 +
  `tests/test_procedures.py` 1 例回归）。修复前先失败、修复后转绿。
- **费用**：**0 元**（`billed_calls=0`、`cost_rmb=0`，账本未变动，仍 0.471396 / 9.528604）。
- **结果**：`heading-block-v2` recall@5 0.850 → **0.900**（提升 D07，无退化）；
  `heading-procedure-v3` 0.850 → **0.400**（退化 D05–D09）；`pdf-pages-v1` 未对照（语料无 PDF）。
- **失败/局限案例**：procedure-v3 的 −0.450；D04 三策略皆 0.00；语料无围栏代码与独立长篇报告。
- **不声称创新**：仅为可解释的工程改良，结论限定在本语料与固定检索配置下。

## Comments

用户已授权将文档类型适配加入主线。13/14 开始时直接使用 tdd；13 前执行已授权的架构检查，详见 docs/development-workflow.md。

15 为**对照型**任务（见 `docs/development-workflow.md`）：不把「指标变好」当作通过条件，也不预设提升比例。
本轮发现 procedure 策略的真实缺陷（正文误标元数据），已按「先失败回归 → 最小修复」处理并固化测试。

