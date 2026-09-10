# 安全知识研究助手

开发每个 Issue 前阅读 [技能触发规则](docs/development-workflow.md)。已授权 TDD 的阶段：06/13/14/11/07/15/08 均已完成，
后续 10 开始时按 TDD 推进；04–06 后、13 前的架构检查已完成（用户裁定不重构），13/14 后就切分规则的
元数据剥离做了一次局部收敛，08 前就检索规则重复（发现 ⑤）做了第二次刻意最小收敛（等价性逐字节证明）。

**当前进度（2026-09-10）：Issue 01–08、11、13、14、15 已完成**（M0 / M1 / M1D 里程碑均完成，M2D 的 15 与 M2 的 08 完成），
下一步 Issue 10（有限补充检索）。整条主线见 [ROADMAP](ROADMAP.md)。
当前支持：Markdown / 文本型 PDF 导入、四种切分策略、关键词 / 本地向量 / **BM25 / RRF 混合检索**、
DeepSeek 真实调用（含预算保护）、资料更新删除、逐字引用校验、开发集检索基线（`skra eval`，免费离线）、
切分策略对照（`scripts/compare_splitters.py`）与检索方式对照（`scripts/compare_retrievers.py`，均免费离线）。
真实模型效果已在 Issue 03/05 做过端到端验收，**但样本小、不代表稳定准确率**；
未做 OCR、复杂表格与双栏重建。

## 运行

需要 Python 3.11+。**纯 Markdown 与关键词检索只用标准库**；导入 PDF 需 `pypdf`，
向量检索需单独的 `.venv`（见 [向量基线](docs/vector-usage.md)）。在仓库根目录执行：

```powershell
python -m skra import examples/security-demo.md --title "Security demo" --source "urn:skra:security-demo" --license "CC0-1.0"
python -m skra docs
python -m skra search "提示注入"
python -m skra search "tool permissions"
python -m skra read <搜索结果中的完整片段ID>
python -m skra run 1
python -m unittest discover -s tests -v
```

导入 PDF 时用虚拟环境（含 pypdf）：

```powershell
.\.venv\Scripts\python.exe -m skra import <file.pdf> --title "<标题>" --source "<来源>" --license "<许可>"
```

PDF 会自动选用 `pdf-pages-v1` 策略，片段带 1 基**页码**；重复页眉页脚标为元数据（保留可查、不占正文名额）；
扫描件或没有文本层的 PDF **会明确报错**而不是静默给出空内容。已导入资料用
`python -m skra update <file> --source <src>` 更新、`python -m skra delete <src>` 删除。

示例为本项目自建英文测试资料，非权威资料或真实实验。导入真实资料前**先核查页脚许可与使用条款**
（公开可读 ≠ 可全文再发布），使用 UTF-8 编码，并通过 `--acquired YYYY-MM-DD` 指定取得日期。

默认数据库为 `.data/knowledge.sqlite3`（Git 忽略）。可在子命令前指定 `--db 路径` 创建独立知识库。数据库保存原文快照，原文件改变不会静默改变已导入证据。

返回 JSON 包含标题、来源、许可、资料版本、章节、从 1 开始的起止行号（PDF 另有页码）和英文原文；
分数仅为匹配词项数，不是置信度。关键词检索只内置提示注入、工具权限、最小权限、间接注入四个术语映射，
无法提供通用跨语言检索；跨语言查询请用向量检索。无结果不能证明资料没有答案。

同来源同内容重复导入保持原标识；相同来源不同内容用 `update` 更新（旧版本证据失效，不再进入新回答）。
Markdown 默认切分器为按标题及最多 20 行（`heading-lines-v1:20`）；结构清晰时自动选用 `heading-block-v2`
（指南）或 `heading-procedure-v3`（步骤/代码），PDF 用 `pdf-pages-v1`；可用 `--splitter` 覆盖。

## 评测基线（免费、离线、不记账）

评测题以**原文跨度 + 必须共同出现的条件**标注（不用片段 id，因为片段 id 随切分策略变化会让 Recall 不可比）。
开发集与保留集分文件且双重隔离：文件自身的 `kind` 字段权威，把保留集当开发集传入会被拒绝；
普通运行默认不打开保留集。报告记录冻结哈希（`sample_hash` / `corpus_hash`）、逐题行与未运行项。

```powershell
.\.venv\Scripts\python.exe -m skra eval --exclude <合成夹具的doc_id> --out <报告路径>
```

`--exclude` 剔除的 doc_id 会写入报告（否则基线不可复现）。`Recall@5` 的分母是**标注的证据束数**，
不随切分策略改变；`required_together` 的束被切开时记 `broken`，不算命中。
`evidence_tokens` 是字符数/4 的**估算，不是真实分词计数**，仅用于在同一把尺子下比较策略。
`examples/eval-holdout-cases.json` 为保留集，封存至最终评测，**不要在调参期间打开**。

## 切分策略对照（免费、离线）

在同一批语料、问题、编码器、top-k 与证据预算下对照切分策略，**一次只改切分器**：

```powershell
./.venv/Scripts/python.exe scripts/compare_splitters.py `
  --out docs/evidence/issue15-splitter-comparison-20260910.json `
  --preview docs/evidence/issue15-splitter-preview-20260910.json
```

`--preview` 另存**切分预览与原文前后对照**，用于逐字查看每个策略把同样的行切成了什么。
`pdf-pages-v1` 不在默认对照集内（语料中没有 PDF，且该策略不能切 Markdown），报告 `not_run` 会声明这一点。

## 检索方式对照（免费、离线）

在同一批语料、切分器、问题、编码器、top-k 与证据预算下对照检索方式，**一次只改检索器**：

```powershell
./.venv/Scripts/python.exe scripts/compare_retrievers.py `
  --out docs/evidence/issue08-retriever-comparison-20260910.json
```

三路为 `vector`（余弦基线）/ `bm25`（Okapi BM25，`k1=1.5`/`b=0.75`）/ `hybrid-rrf`（倒数排名融合，`K=60` 等权）。
RRF **只读各路的排名，不合并余弦与 BM25 两种尺度的分数**；候选卡片带 `contributions` 显示每路给的名次，融合可审计。
**实测结论：本语料上混合检索无净提升**（BM25 −0.450、RRF −0.100），原因是中文问题与英文语料存在词项错配、
且融合会放大「词面相似但跨度错误」的候选；**如实记录为负面结果，未做参数拟合**。
详见 `docs/evidence/issue08-retriever-comparison-20260910.md`。

可选安装命令：`python -m pip install -e .`，之后使用 `skra` 命令；构建需要 setuptools，离线环境可直接使用上述模块入口。

## 开发路线

见 [PRD](PRD.md) 和 [ROADMAP](ROADMAP.md)。已完成 01–08、11、13、14、15；**下一步 Issue 10**（有限补充检索）。
不要提交密钥、数据库或个人配置。

## 测试回答路径（免费）

先按上述步骤导入样例，再执行：

```powershell
python -m skra ask "提示注入" --demo
python -m skra budget
```

`--demo` 不联网，输出明确标记 `mode: demo`，中文结论和释义是占位内容，不能当作模型翻译或真实知识回答。它用于查看引用、资料版本和预算如何呈现。`answer_run_id` 可传给 `run` 查看记录。

## 真实调用配置（Issue 03 验证）

将示例计费配置复制到 `.data` 内，在核对官方可用模型、人民币每百万 token 价格与日期后填写。输入单价使用缓存未命中价，按该价格保守记账（可能高于实际平台账单）。默认配置禁止调用；不要仅为通过检查而把 verified 改为 true。

输入预留已改为官方上下文窗口上限，采用 1,048,576 token 的保守上界，不再使用字符估算。价格核对日期最多七天有效。该预算是本地防误操作控制，无法限制其他程序或用户直接调用账户的支出。

密钥只从本机 `DEEPSEEK_API_KEY` 环境变量读取，不放入计费配置。调用入口为 `python -m skra ask "问题" --config .data/model-config.json`。当前未验证真实 API 的 JSON 输出契约和具体模型适配，不应提前宣称可正常付费生成。

全项目账本固定在安装源码目录的 `.data/budget.sqlite3`，更换 `--db` 不重置额度；不要删除或移动账本以刷新预算。总额度 10 元（**当前累计 0.471396 元，可用 9.528604 元**），单次输出最多 **1500** token、输入最多 20000 UTF-8 字节、问题最多 2000 字符，网络等待超时为 30 秒。不自动重试（零次，低于一次上限）。

请求失败或用量缺失时费用未知，会保留预留并暂停后续请求；目前没有自动核销功能，需核对平台账单后在后续任务提供明确的核销流程。已取得用量但引用校验失败仍记账，不展示无效答案。结构和原文匹配测试不代表语义正确，真实引用支持与中文释义需人工复核。

GitHub 仓库：https://github.com/lingjiang141/Safety-Knowledge-Research-Assistant


真实调用验收步骤见 [Issue 03 本机指南](docs/live-m0.md)，支持 --preflight 免费预检和 --prompt-key 隐藏输入密钥。


PRD v0.2 新增文档结构适配主线（13–15 及提前的 11），**均已实现**：指南按标题/定义/列表切分、
步骤代码保留前提与警告、文本型 PDF 按页定位并识别提取异常。复杂表格、OCR、多模态与无限联网研究
仍在范围外（见 PRD 第 6 节）。
