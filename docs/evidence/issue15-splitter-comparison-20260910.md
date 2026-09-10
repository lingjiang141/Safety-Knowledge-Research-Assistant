# Issue 15 验收证据：用实际问题验证文档切分改良

日期：2026-09-10
状态：**done（检索结构对照完成；生成侧与保留集按设计未运行）**
付费调用：**无**（`network_called=false`、`billed_calls=0`、`cost_rmb=0`，账本未变动）

## 1. 交付物

| 交付物 | 路径 |
| --- | --- |
| 对照脚本 | `scripts/compare_splitters.py` |
| 对照报告（原始 JSON） | `docs/evidence/issue15-splitter-comparison-20260910.json` |
| 切分预览 + 原文前后对照 | `docs/evidence/issue15-splitter-preview-20260910.json`（215 片段） |
| 缺陷回归测试 | `tests/test_split_labels.py`（4 例，新增）、`tests/test_procedures.py`（+1 例） |
| 修复的实现 | `skra/store.py`（`_chunk_procedure` 标注与合并两处） |

复现命令（免费、离线，无需密钥）：

```bash
.venv/Scripts/python.exe scripts/compare_splitters.py \
  --out docs/evidence/issue15-splitter-comparison-20260910.json \
  --preview docs/evidence/issue15-splitter-preview-20260910.json
```

全量测试：**98 tests 通过**（原 93 + 本题新增 5）。

## 2. 对照设计（对应验收项 3：固定不变的因素）

一次只改一个因素 —— **切分策略**。其余全部冻结：

| 因素 | 取值 |
| --- | --- |
| 语料 | 工作库中 `source LIKE 'https://%'` 的 OWASP 真实快照（排除合成夹具 `Security demo`） |
| 编码器 | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`，revision `e8f8c211…`，384 维 |
| 检索器 | 本地精确余弦向量检索 `VectorSearch`（不加重排序、不加翻译） |
| top-k | 5 |
| 证据预算 | 固定 top-k=5；同一切分下用同一把尺子 |
| 问题与标注 | 开发集 D01–D10，标注与 Issue 07 冻结一致 |

**每个策略从同一批快照建独立 SQLite**（`materialise`），因此不做「把基线重导入」这种会污染对照的操作；
每个策略的语料哈希独立记录（见报告 `strategies[].freeze.corpus_hash`），不同策略哈希必然不同 ——
这正是切分改变了语料的证据，而不是语料被换掉。

## 3. 对照结果（开发集，向量检索，k=5）

| 策略 | recall@5 | 证据估算 token | 元数据片段占用槽 | broken 束 | 相对基线 |
| --- | --- | --- | --- | --- | --- |
| `heading-lines-v1:20`（基线） | 0.850 | 1979.3 | 0 | 0 | — |
| `heading-block-v2`（指南结构） | **0.900** | 1920.7 | 0 | 0 | **+0.050**（提升 D07，无退化） |
| `heading-procedure-v3`（步骤/代码） | **0.400** | 398.3 | 0 | 1 | **−0.450**（退化 D05/D06/D07/D08/D09） |

逐题表：

| 用例 | 问题要点 | 基线 | 指南结构 | 步骤/代码 |
| --- | --- | --- | --- | --- |
| D01 | 提示注入 vs 越狱 | 1.00 | 1.00 | 1.00 |
| D02 | 直接/间接注入来源 | 1.00 | 1.00 | 1.00 |
| D03 | RAG 是否消除风险 | 1.00 | 1.00 | 1.00 |
| **D04** | 三个过度代理概念 | **0.00** | **0.00** | **0.00** |
| D05 | complete mediation | 1.00 | 1.00 | **0.00** |
| D06 | 两份资料的限制权限建议 | 1.00 | 1.00 | **0.00** |
| D07 | 区分资料/指令 + 限权 | 0.50 | **1.00** | **0.00** |
| D08 | 本项目防护成功率（无答案） | 1.00 | 1.00 | **0.00** |
| D09 | 最小权限含义 + 百分比（部分有据） | 1.00 | 1.00 | **0.00** |
| D10 | 忽略之前指令攻击示例 | 1.00 | 1.00 | 1.00 |

## 4. 关键设计点：跨策略不用 chunk 数或 chunk ID 比较 Recall（验收项 4）

切分策略一变，片段数量与 id 就全变（同一份 LLM06：基线 6 片段 → 指南 7 → 步骤 37）。
若把标注锚在片段 id 上，Recall 的分母会随策略漂移，数字不可比（PRD 5.3）。
因此本题的 Recall **锚在原文行跨度**上，由 `resolve_span` 把「行范围」映射到当前策略产出的片段，
**分母恒为标注的证据束数**。报告里 `annotated_bundles` 对每个策略是同一个值（D04 恒为 3），
这就是分母没动的证明。

三类核查都在报告里可见：
- **原文跨度覆盖率**：`retrieved_bundles / annotated_bundles`。
- **证据完整性**：`required_together` 的束只有**所有覆盖片段都被取回**才算命中；只取到一部分记 `broken`。
- **元数据占位**：`metadata_chunks`（本对照全为 0，见 §7 关于元数据的说明）。
- **原文定位正确性**：`must_include` 逐字子串在预览文件的片段文本中可自查。

## 5. 修复的真实缺陷：procedure 策略把正文误标为元数据

### 5.1 现象

对照首跑时，`heading-procedure-v3` 下 LLM01 快照的**正文散文行（第 9/11/13 行）被标成 `kind=metadata`**，
元数据片段数 11（应为 3，每文档 1 个）。这会直接把真实正文挤出 body 搜索槽。

### 5.2 根因（两段，都在 `store._chunk_procedure`）

`peel_metadata` 把标题块（如 1–8 行）剥成独立元数据单元后，余下的正文单元（9–14）**没有自己的标题行**：

1. **标注阶段**：原逻辑「无标题续段继承上一单元的标签」让正文继承了上一单元的 `(说明性元数据)` 标签。
2. **合并阶段**：原逻辑「无标题续段并入上一单元」又把这些正文**无条件**并入元数据单元。

指南策略 `_chunk_structured` **没有这个 bug** —— 它有双重保险
（`kind = "metadata" if section==METADATA_SECTION or is_metadata_block(text) else "body"`），
所以这个缺陷只出现在 procedure 策略。这个不对称本身就是值得记录的发现。

### 5.3 修复

- 标注阶段：仅当「上一单元标签不是元数据」时才继承；否则**回溯到最近的非元数据标签**。
- 合并阶段：禁止把无标题续段并入 `METADATA_SECTION` 单元，改为自成一个单元。

修复后 procedure 的元数据数 **11 → 3**。

### 5.4 回归护栏（先失败、再修复）

- `tests/test_procedures.py::test_body_following_a_peeled_title_block_is_not_called_metadata` —— 先失败的红。
- `tests/test_split_labels.py`（4 例）对**两个策略**跑子测试：正文是 body、出处行仍是 metadata、
  正文仍可被 body 查询命中、元数据不抢占正文命中。后两条防止「把 bug 从一个位置搬到另一个位置」。

## 6. 至少一项退化或局限（验收项 5）

### 6.1 退化一：procedure-v3 的 −0.450（真退化，非虚构）

`heading-procedure-v3` 把 LLM06 从 7 片段切成 37（平均 233 字符），
虽然候选仍是**真实 body 证据**（如 D05 命中的 L42/L40、D08 的 L46–49 guardrail 注意事项），
但切得太碎、排序竞争不过更完整的段落，D05–D09 全部掉出 top-5。

### 6.2 局限二：D04 在三策略下都是 0.00 —— 标注单元与切分粒度的错配（诚实缺口）

D04 标注三个束，每束是「编号行 + 空行 + 定义句」（如 `S03:21-23`）：

| 策略 | 21–23 | 33–35 | 41–43 |
| --- | --- | --- | --- |
| 基线 | 覆盖 1 片段（19–38）✓ 完整 | 1 片段（19–38）✓ | 1 片段（39–44）✓ |
| 指南结构 | 同上 ✓ | 同上 ✓ | 同上 ✓ |
| 步骤/代码 | **2 片段**（19–21 + 23）✗ | **2 片段**（33 + 35）✗ | **2 片段**（41 + 43）✗ → broken |

原文：

```
19| ## Common Examples of Risks
21| 1. Excessive Functionality
23| An LLM agent has access to extensions which include functions that are not needed …
33| 4. Excessive Permissions
35| An LLM extension has permissions on downstream systems that are not needed for …
41| 6. Excessive Autonomy
43| An LLM-based application or extension fails to independently verify and approve …
```

procedure 策略把编号行独立成片段，于是「编号 + 定义句」被切开 —— 跨度跨两片段。
这不是 bug，而是**标注假设（编号行与定义句必须同现）与 procedure 粒度不匹配**的真实信号，
也正是「跨策略不能用 chunk 数比较 Recall」的具体例证。
在基线与指南结构下 D04 的 0.00 则是**排序未进前 5**（定义段向量排名第 2，但被同片段的其他内容稀释），
已记入 Issue 13/14/11 的结构适配范围。**两种 0.00 的原因不同，报告里分开写明，没有混称。**

### 6.3 采样局限（验收项 1）

本题语料仅 3 份 OWASP Markdown，**均小于 90 行**：

| 文档 | 行数 | 字符数 | 围栏代码块 |
| --- | --- | --- | --- |
| LLM01 Prompt Injection | 81 | 6583 | 0 |
| LLM06 Excessive Agency | 86 | 8678 | 0 |
| Cheat Sheet | 50 | 4406 | 0 |

因此如实记录：

- **「步骤/代码」一类只能用编号措施（如 LLM06 第 1–8 条预防措施）代表，语料中没有任何围栏代码块**，
  不能声称已在真实代码切分上验证。
- **「文本型报告」一类由 3 份指南型 Markdown 的散文段落代表，没有独立的长篇报告样本。**
- 虽然每份都超过短节选规模且是完整合法文本（非摘录），但**行数偏小**，长文档的切分行为未被覆盖。

## 7. 未运行项与元数据说明

报告 `complete=false`，逐条声明未运行：

1. **PDF 策略对照（`pdf-pages-v1`）**：语料中没有 PDF，且该策略按页切分、不能处理 Markdown。**未纳入本次对照**。
2. **生成侧指标**（引用支持率、无答案正确说明率、误拒答率）：需付费调用与人工语义复核，未运行。
3. **保留集执行**：按设计延后到 Issue 12，本任务只用开发集。
4. **人工语义复核**：`manual_review="pending"`，本题只做检索结构指标。

**关于元数据占位全为 0**：本对照的 `metadata_chunks` 三策略皆 0。这说明**当前语料下出处样板并未被误当作正文检索到**，
但不等于「元数据从不干扰」—— procedure 首跑时的 11 个误标正是干扰的实例，只是修复后被消除。
更广义的元数据干扰（不同文档的出处格式差异）在本语料规模下尚不可观测。

## 8. 开发集用于调整、保留集未打开（验收项 6）

- 本题**只用** `examples/eval-dev-cases.json`（`kind=development`）。
  报告 `sample_kind="development"`，`deltas_vs_baseline` 全部基于开发集。
- **保留集 `examples/eval-holdout-cases.json` 全程未打开**。对照脚本只接受开发集文件路径，
  且 `load_cases` 的 `kind` 校验会在传入保留集时抛错（Issue 07 的隔离，有测试守卫）。
- **选择规则**：本题结论是**指南结构调整为零风险采用**（指标升、无退化）、
  **步骤/代码结构在本语料下不采用**（−0.450 的实测退化）。规则有具体证据：
  D07 从 0.50 升到 1.00 是指南结构的收益，D05–D09 的 0 是 procedure 的代价。
  最终「保留 / 回退 / 局部启用」的取舍在 Issue 12 用保留集验收后再定。

## 9. 工程改良的定性（验收项 7）

本对照演示的是**可解释的工程改良**：把「固定 20 行」换成「按标题结构切」，
在**同一把尺子**下让证据更完整（D07 命中率 +0.050，证据 token 同时下降 3%）。
**不声称学术首创，也不声称普遍企业需求**：样本仅 3 份 OWASP Markdown，
结论限定在「本语料 + 本编码器 + top-k=5」。

## 10. 遗留与交接

- **架构发现 ⑤ 仍开放**：`store.search` 有 body 优先排序、`vector.search` 无（本题用向量检索，故未观测到差异）。
- **`eval.py` 跨度解析直接读 `chunks` 表**，与两检索器各自维护的 active/装配规则耦合 —— 08 前复核点。
- **D04/D05–D09 的检索缺口**记入 Issue 13/14/11 结构适配范围，**不改固定检索器**。
- 保留集**不得**在 12 之前打开。
