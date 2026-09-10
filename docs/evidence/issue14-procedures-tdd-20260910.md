# Issue 14 完成证据：操作步骤携带前提、代码与警告

日期：2026-09-10｜技能：**tdd**（一个外部行为测试 → 最小实现 → 回归，逐条红→绿）
本轮**无付费调用**（本地测试 + 本地语料验证）；账本保持 **0.471396** 元未变。

## 接口（用户确认）

- **切分策略**：新增 `heading-procedure-v3` 步骤/代码策略；保留 `heading-lines-v1:20`
  固定基线与 `heading-block-v2` 指南策略；导入时 `--splitter` 显式覆盖。
- **前提/警告与步骤同块**：紧邻步骤的前置条件、警告必须与步骤一起可检索。
- **关联契约**：步骤、前提、代码、警告之间保持结构关联（代码围栏不得被切碎或冒充标题）。

## TDD 循环（先失败后通过）

| # | 行为测试 | RED 证据 | 最小实现 |
| --- | --- | --- | --- |
| 1 | 步骤携带其前置条件与相邻警告 | `AttributeError: 'Store' object has no attribute '_chunk_procedure'` | `PROCEDURE_SPLITTER` + `_chunk_procedure` + `_procedure_pieces` |
| 2 | 围栏代码为一整块、`#` 不被当标题 | `AssertionError: 'Run the following' not found`（围栏被 `#` 注释切碎） | 先扫描围栏区域再识别标题；围栏原子化（开/闭围栏+引入句同一片段） |
| 3 | 紧随步骤的警告归属该步骤小节 | `TypeError: tuple indices must be integers`（测试助手返回元组） | 无标题延续单元继承前一小节标签 |
| 4 | 结构不明回退通用策略并记录原因 | `'heading-procedure-v3' != 'heading-lines-v1:20'` | 无标题文档自动回退基线 + `splitter_note="结构不明…回退…"` |
| 5 | 引用来自真实原文跨度 | —（已满足，测试固化） | 每个片段 `start_line/end_line` 与源文件逐行相等 |
| 6 | CLI `--splitter heading-procedure-v3` | —（复用 13 的 `--splitter`） | `SPLITTERS` 增第三项，`choices` 自动接受 |

**测试结果：52 tests 全部通过**（13 后 46 + 新增 6，`tests/test_procedures.py`）。

## 实现要点与踩坑（诚实记录）

调试中暴露三个真实缺陷，均已修复并固化为测试：

1. **`#` 注释被当成标题**：原按行扫描标题时不区分围栏，`` ```bash `` 内的
   `# this comment is not a heading` 被误判为标题，把围栏拦腰切断。
   修复：**先标记围栏区域**（开围栏、围栏内全部行、闭围栏），再在非围栏行上识别标题。
2. **标题链塌陷**：合并守卫写成 `if headed and merged:`，导致第 2 个单元之后
   每个带标题单元都并入前一单元，整篇文档塌成 **1 个片段**（9 → 1）。
   修复：改为「带标题单元一律另起小节，只有无标题延续才并入前一小节」。
3. **peel 循环变量遮蔽**：剥离元数据的循环复用变量名 `start`，覆盖了后续
   `fenced_blocks` 计算所依赖的单元起点，导致标签判断整体错位。
   修复：循环改用 `unit_start/unit_end`，消除遮蔽。

另修正两处设计：**标签按片段而非整单元**判定（只有真正含围栏的片段才加
`代码（…）` 标签，避免整个小节被误标）；**引入句不重复**（`Run …:` 归入代码片段，
不再同时出现在前一散文片段）。

## 真实语料验证（`examples/corpus/owasp-prevention-cheatsheet-full.md`）

步骤策略对该资料切出 **13 片段**，小节名正确解析（`Structured Prompts with Clear
Separation`、`Agent-Specific Defenses`、`Least Privilege`、`Model-Based Guardrails`），
标题/版权前言归入 `(说明性元数据)`，无标签错位。

## 关键改动

- `skra/store.py`：新增 `PROCEDURE_SPLITTER` 与 `SPLITTERS` 第三项；
  `_chunk` 增加分派；`_chunk_procedure`（围栏感知分节 → 元数据剥离 → 标签 →
  合并 → 逐片段装配）；`_procedure_pieces`（围栏原子化、引入句归入代码、空行分片）；
  `ingest` 增步骤策略的未知结构回退。
- `tests/test_procedures.py`：新增 6 例（含 `PROCEDURE` 夹具）。

## 演示命令（本地、免费）

```bash
python -m skra --db <db> import <runbook.md> --title R --source urn:x --license "CC0-1.0" \
    --splitter heading-procedure-v3      # status=imported, splitter=heading-procedure-v3
python -m skra --db <db> search "rotate deploy key warning"   # 步骤与警告各自可检索
```

## 真实与模拟区分

- 本轮为**程序行为测试 + 本地语料切分**，**不含真实模型调用**；未产生费用。
- 语料验证仅用 **1 份本地资料**（该资料无围栏代码），**不构成正式评测**；围栏行为的
  覆盖来自测试夹具，不声称对全量资料普遍生效。

## 未解决问题

- Q06（跨两份资料比较）检索排名仍未改善（13 记录为第 4），待 **11** 处理跨资料召回。
- 架构检查发现（②切分不变量分散 ⑤检索规则重复）因新增第三个策略而进一步放大：
  三个策略共用 `_split_block`/元数据剥离逻辑但各自实现，13/14 均未重构（用户裁定保留）。
- 费用：0 新增；账本 0.471396 元（用户已核对平台账单一致）。
