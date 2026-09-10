# Issue 07 验收证据：冻结评测样本与可复查基线报告

日期：2026-09-10
状态：done（生成侧指标与保留集按设计未运行，见「未运行项」）
付费调用：**无**（`network_called=false`、`billed_calls=0`，账本未变动）

## 1. 交付物

| 交付物 | 路径 |
| --- | --- |
| 评测模块 | `skra/eval.py` |
| CLI 子命令 | `python -m skra eval`（`skra/cli.py`） |
| 开发集（10 题 D01–D10） | `examples/eval-dev-cases.json` |
| 保留集（10 题 H01–H10，本题不运行） | `examples/eval-holdout-cases.json` |
| 基线报告（原始 JSON） | `docs/evidence/issue07-baseline-20260910.json` |
| 测试 | `tests/test_eval.py`（21 例） |

全量测试：**93 tests 通过**（原 72 + 本题 21）。

## 2. 关键设计决定（用户已确认四项）

### 2.1 标注锚在原文跨度，不锚在片段 id

证据标注形如 `{source, start_line, end_line, must_include, required_together}`。
**不使用 fragment id**：fragment id 是切分策略的函数，锚在它上面会让 Recall 在策略之间不可比
（PRD 5.3 明确要求切分策略可对照）。跨度按「行范围覆盖」映射到当前策略产出的片段，
**分母是标注的证据束数**，因此切分策略改变时分母不动。

### 2.2 `required_together` 与 broken 的区分

- `required_together=true` 的束：**所有覆盖该跨度的片段都被检索到**才算命中。
- 只取到其中一部分 → 记 `broken`，这是「束被切分开」的可见信号，不是命中。
- `required_together=false`（如无答案题的限定句）：取到任一覆盖片段即可。

若把被切开的束算作命中，就等于奖励这个标注本来要抓的失败。

### 2.3 开发集与保留集双重隔离

1. **分文件**：`eval-dev-cases.json`（`kind=development`）与 `eval-holdout-cases.json`（`kind=holdout`）。
2. **代码拦截**：文件自身的 `kind` 字段权威。把保留集文件当开发集传入 → 抛 `EvalError`；
   `load_cases(path, kind="holdout")` 遇到非保留文件也抛错。
3. **默认不可达**：`load_sample(dev)` / `run_baseline(...)` 默认 `holdout=None`，
   报告里 `holdout_loaded=false`、`holdout_path=null`。
4. **测试守卫**：有测试实际在磁盘上放一个保留集文件，断言普通基线运行**不打开它**；
   另有两集编号与问题**均不重叠**的断言。

CLI 实测：

```
$ python -m skra eval --sample examples/eval-holdout-cases.json
错误：该文件声明为保留集（kind=holdout）：examples\eval-holdout-cases.json。
保留集不能进入调参上下文；如需在最终评测中运行，请使用显式的 holdout 入口。
```

### 2.4 冻结与可复查

报告记录 `freeze.sample_hash` / `freeze.corpus_hash`（项目自带 SHA-256 digest）、
`freeze.splitter`、`freeze.encoder`、每份文档的 `id/title/hash/splitter`。
同输入两次运行哈希一致（有测试断言）。

本次冻结值：

- `sample_hash` = `b8f592e6c5379e4f…`
- `corpus_hash` = `99a98b76a8656451…`
- `splitter` = `heading-lines-v1:20`
- `encoder` = `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
  （revision `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`，384 维）

### 2.5 成本口径

- 报告含 `evidence_tokens`（每个用例检索到的证据字符数/4 的**估算**）与 `metadata_chunks`（元数据片段占用证据槽数）。
- 该估算**不是真实分词计数**，报告内以 `evidence_tokens_estimate_note` 明确标注，
  仅用于在**同一把尺子**下比较策略。
- 本次 `mean_evidence_tokens = 1979.3`，`total_metadata_chunks = 0`。

## 3. 基线结果（开发集，向量检索，k=5）

命令（免费、离线）：

```bash
.venv/Scripts/python.exe -m skra eval \
  --exclude 85772b0052029e9b3edb20fe43f7f80f896aa9c0e6703d1ff049e7b8bc8aeb97 \
  --out docs/evidence/issue07-baseline-20260910.json
```

`--exclude` 剔除合成夹具 `Security demo`（`85772b00…`），并在报告中记录该剔除，
否则基线不可复现。总耗时 936.5 ms。

| 用例 | 问题要点 | 命中束/标注束 | Recall@5 | broken | 证据估算 token |
| --- | --- | --- | --- | --- | --- |
| D01 | 提示注入 vs 越狱 | 1/1 | 1.0 | 0 | 1616 |
| D02 | 直接/间接注入来源 | 2/2 | 1.0 | 0 | 2007 |
| D03 | RAG 是否消除注入风险 | 1/1 | 1.0 | 0 | 1975 |
| **D04** | 三个过度代理概念 | **0/3** | **0.0** | 0 | 2067 |
| D05 | complete mediation | 1/1 | 1.0 | 0 | 2037 |
| D06 | 两份资料的限制权限建议 | 2/2 | 1.0 | 0 | 2149 |
| **D07** | 区分资料/指令 + 限权 | **1/2** | **0.5** | 0 | 1847 |
| D08 | 本项目防护成功率（无答案） | 1/1 | 1.0 | 0 | 2406 |
| D09 | 最小权限含义 + 百分比（部分有据） | 1/1 | 1.0 | 0 | 1714 |
| D10 | 忽略之前指令攻击示例 | 1/1 | 1.0 | 0 | 1975 |

**聚合：`recall_at_5 = 0.85`，`scored_cases = 10`，`failed_cases = []`，`broken_bundles = 0`。**

### 3.1 对 0.85 的正确解读（重要）

**这是检索可达性的结构指标，不是回答质量。**

- **没有 `broken` 束**：当前 `heading-lines-v1:20` 下，所有标注跨度都落在单个片段内，
  不存在「一个束被切分切开」的情况。因此本次 `recall_at_5` 的缺口**全部**来自排序未进前 5，
  而不是切分破坏。
- D04 三个概念定义各成一束，均排在 top-5 之外（已知：基线切分下定义段向量排名第 2 —— 
  但同一切分把三个概念压进同一片段，其余相关段落在别处竞争，故整体未进前 5）。
  与 Issue 13/14 记录的「结构切分后定义段升到第 1」互证。
- D07 命中「资料/指令分离」束，未命中「限制扩展权限」束（`S03:51`）。
- 命中 ≠ 回答正确；D08/D09 命中同样不能说明系统会正确降级。
  无答案/部分有据的正确性只能由生成侧指标与人工复核判定，见下节。

## 4. 未运行项（不虚构完整报告）

报告 `complete = false`，`not_run` 逐条声明：

1. **生成侧指标**（引用支持率、无答案正确说明率、误拒答率）：需付费调用与人工语义复核，本任务未运行。
2. **保留集执行**：按设计延后到 Issue 12 最终评测，本任务只用开发集。
3. **切分对照与混合检索比较**：属于 Issue 15 / 08。

`manual_review = "pending"`：本题不代替人类语义验收。

## 5. 保留集构成（已创建，本题不运行）

`examples/eval-holdout-cases.json`，`kind=holdout`，10 题 H01–H10，与开发集**编号与问题均不重叠**。
按 Issue 卡片要求覆盖三类文档结构：

| 结构类 | 用例 | 落点 |
| --- | --- | --- |
| 长段落散文 | H01、H04 | LLM01 多模态风险段；LLM06 代理机制与注入因果段 |
| 项目符号清单 | H02 | LLM01 注入后果清单（25–32 行，跨片段边界） |
| 编号措施/步骤 | H03、H06、H07、H09 | LLM01 第 4/6/7 条措施；LLM06 第 5 条措施 |
| 要点式文本段落 | H05、H08 | cheatsheet 护栏模型要点（34、46 行） |
| 示例场景短文 | H10 | LLM01 RAG 文档污染场景（78–80 行） |

H03 特意跨 `55/56` 片段边界、H02 跨 `25–32`，用于在最终评测中观察切分策略对**清单与编号块**的影响。

## 6. 遗留与交接

- **架构发现 ⑤ 仍开放**：`store.search` 有 body 优先于 metadata 的排序，`vector.search` 无。
  本基线用向量检索，`metadata_chunks = 0`，说明当前语料元数据未被检索到；该缺口留待 08 前处理
  （已有护栏测试）。参见 `docs/evidence/architecture-review-20260910.md`。
- **D04/D07 是本基线的诚实缺口**，已记入 Issue 13/14/11 的结构适配范围，不改固定检索器。
- 保留集**不得**在 12 之前打开；如因本体 bug 需要接触，须先记录理由并重跑冻结。
