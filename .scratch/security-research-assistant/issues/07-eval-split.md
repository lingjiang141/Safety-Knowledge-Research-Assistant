# 07 — 冻结评测样本并保存可复查的基线报告

Status: done
State: done
Type: HITL
Milestone: M1
User stories: US18, US19, US21, US22
Source: [PRD](../../../PRD.md)

## What to build

把开发问题绑定实际语料证据，另建保留测试集，运行评测入口产生检索、引用和无答案行为报告。

## Acceptance criteria

- [x] 人工核对可回答性、相关片段和等价证据规则；未导入 S01 时不能将相关题标为可回答。
      → S01 因许可未通过，问题已换题；开发集 10 题、15 个跨度全部人工标注并带 `why` 字段说明标注理由。
- [x] 开发集与保留集分开，保留答案不进入调参上下文；正式冻结记录 hash 和版本。
      → 双重隔离（分文件 + 文件自身 `kind` 权威 + 默认入口不可达 + 测试守卫），
      `freeze` 记录 `sample_hash` / `corpus_hash` / `splitter` / `encoder` / 逐文档 hash。
- [x] Recall@5 按片段定义；重要结论含无引用结论均纳入支持情况检查，分别报告拒答与误拒答。
      → **部分完成**：Recall 已改为按**证据束**定义（分母为标注束数，切分策略改变时不动），
      比「按片段」更稳定；但**生成侧指标（拒答率、误拒答率、引用支持率）本次未运行**，
      已作为 `not_run` 在报告中逐条声明。
- [x] 报告样本量、配置、延迟、费用、失败和未运行项；预算不够时保留付费评测待办，不虚构完整报告。
      → `case_count` / `freeze` / `elapsed_ms` / `cost_rmb=0` / `failed_cases` / `not_run` / `complete=false`。
- [x] 小样本规模可按余额安排；约 60 题是扩展建议。此任务只用开发集调试入口并保存基线，保留集最终执行留至最终评测。
      → 开发集 10 题已跑基线；保留集 10 题已创建但**未运行**。

## Blocked by

- [05-evidence-cases](05-evidence-cases.md)
- [06-version-sync](06-version-sync.md)
- [13-structured-guides](13-structured-guides.md)
- [14-procedures-code](14-procedures-code.md)
- [11-pdf](11-pdf.md)

## Completion evidence

**代码版本**：`skra/eval.py`（新增）、`skra/cli.py`（新增 `eval` 子命令）、
`examples/eval-dev-cases.json`、`examples/eval-holdout-cases.json`、`tests/test_eval.py`。
证据文档 `docs/evidence/issue07-baseline-and-freeze-20260910.md`，
原始报告 `docs/evidence/issue07-baseline-20260910.json`。

**演示命令**（免费、离线）：

```bash
.venv/Scripts/python.exe -m skra eval \
  --exclude 85772b0052029e9b3edb20fe43f7f80f896aa9c0e6703d1ff049e7b8bc8aeb97 \
  --out docs/evidence/issue07-baseline-20260910.json
```

**测试结果**：`tests/test_eval.py` 21 例通过；全量 **93 tests 通过**（原 72 + 21）。

**真实与模拟验证的区分**：
- **真实**：检索与跨度解析全部在真实语料（3 份 OWASP 资料）与真实本地向量编码器上运行；
  `freeze.encoder` 记录真实模型 revision。
- **本次未验证**：生成侧语义（引用支持、无答案正确说明、误拒答）——`manual_review="pending"`、
  `complete=false`、`not_run` 三条。**不声称回答质量已改善。**

**基线结果**：开发集 10 题，向量检索 k=5，`recall_at_5 = 0.85`，
`failed_cases = []`，`broken_bundles = 0`，`mean_evidence_tokens = 1979.3`（估算），
`total_metadata_chunks = 0`，耗时 936.5 ms。
未命中：D04（0/3 束）、D07（1/2 束）——与 Issue 13/14 已记录的检索缺口一致，属诚实缺口。

**费用与未知预留**：`network_called=false`、`billed_calls=0`、`cost_rmb=0`。
账本未变动：累计 0.471396 元 / 可用 9.528604 元 / 预留 0 / blocked=false。
无未知预留。生成侧付费评测待办保留，留待需要时在本机交互终端运行。

**未解决问题**：
1. 生成侧指标（拒答率、误拒答率、引用支持率）未运行 —— 本任务范围外，需付费 + 人工复核。
2. 架构发现 ⑤（`store.search` 有 body 优先排序、`vector.search` 无）仍开放，留待 08。
3. 保留集 H01–H10 未执行，按设计推迟到 12。

## Comments

完成于 2026-09-10。遵守 PRD 的资料边界及 10 元总预算；AFK 表示常规实现无需逐项确认，不表示允许跳过密钥、预算或人工语义复核。

新主线要求：标注以原文跨度及条件完整性为准，之后才映射各切分结果；开发/保留数据划分要覆盖指南、步骤代码和文本报告。保留集延后到 12 使用。新增切分对照在 15 执行，混合检索排在其后。

**实施说明**：`load_cases` 以文件自身的 `kind` 字段为权威，因此「把保留集改名当开发集」也会被拒绝；
`required_together` 的束被切分切开时记 `broken` 而非静默算命中。
`estimate_tokens` 是字符数/4 的确定性估算，**不是真实分词计数**，报告内已标注，仅用于同一把尺子下比较策略。
`--exclude` 剔除的 doc_id 会写入报告，否则基线不可复现。
