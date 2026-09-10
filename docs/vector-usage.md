# 本地向量基线

## 方案

使用 sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2（Apache-2.0，384 维），只在初始化下载模型，检索时 CPU 本地运行；SQLite 保存向量，精确余弦排序，当前资料规模不部署额外向量数据库。

模型：[官方模型卡](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2)。模型最大序列长 128 token；代码将原文按 100 token 窗口编码后归一化均值聚合，避免长片段被静默截断。这一策略是基线选择，尚未证明最优。

## 初始化

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-vector.lock.txt
.\.venv\Scripts\python.exe scripts/setup_vector.py
```

依赖已在 Windows/Python 3.13 安装，锁文件保存精确版本。下载模型后 provenance.json 保存实际 commit revision 与编码策略，检索日志同样保留，避免实验版本不明。初始化需网络，模型文件在 .data 内，不提交 Git。

## PDF 导入（Issue 11）

PDF 导入需要 `pypdf`（纯 Python、无运行时依赖），已在 `pyproject.toml` 的 `dependencies` 与
`requirements-vector.lock.txt` 中声明 `pypdf==6.18.0`，随上面的安装步骤一并装入 `.venv`：

```powershell
.\.venv\Scripts\python.exe -m skra import <file.pdf> --title "<标题>" --source "<来源>" --license "<许可>"
```

- 只读**文本层**，不执行文件内任何内容；不做 OCR。
- 自动选用 `pdf-pages-v1` 策略，片段带 1 基**页码**；跨页段落不合并。
- 重复页眉页脚判为 `kind=metadata`：保留可查、不占正文检索名额。
- 扫描件无文本层、文件损坏或阅读顺序明显混乱时**报错**，不静默给出空内容。
- 夹具可用 `python scripts/make_pdf_fixtures.py` 免费生成（同样无额外依赖）。

## 两份资料的开发基线

```powershell
.\.venv\Scripts\python.exe scripts/vector_baseline.py
.\.venv\Scripts\python.exe -m skra --db .data/vector-baseline.sqlite3 search "应该给智能助手配备多少工具？" --retrieval vector
.\.venv\Scripts\python.exe -m skra --db .data/vector-baseline.sqlite3 ask "应该给智能助手配备多少工具？" --retrieval vector --demo
```

报告写入 docs/vector-baseline.json。资料为两份已标注来源的 OWASP 短原文节选，不是全文。两道公开开发问题仅作连通性验证，样本少且 Recall@5 容易饱和，不能当作正式评测或项目效果提升证据。

## 自己的资料库

使用 import 导入资料后，执行 `python -m skra index` 再 `search --retrieval vector`。务必使用安装了依赖的 .venv Python。增加资料后索引会判定过期，需再次 index。资料的**更新与删除**已由 **Issue 06 完成**：`python -m skra update <file> --source <src>` / `python -m skra delete <src>`；索引与检索只取 `active` 片段，旧版本证据不会进入新回答。

默认检索仍是 keyword；vector 显式启用，不使用中文术语映射。ask 可与 --retrieval vector、--preflight 或 --prompt-key 组合，仍走同一 10 元预算账本。demo 不是真实翻译或语义回答。

不要因向量总会返回近邻就认定问题有答案；无答案行为由证据与生成验收检查。正式中文生成与释义核对需实际 API 响应，本任务不使用密钥或额外付费调用。

## 评测与切分对照（免费、离线）

**检索基线（Issue 07）**——在冻结的开发集上跑向量检索，报告冻结哈希与逐题结果：

```powershell
.\.venv\Scripts\python.exe -m skra eval --exclude 85772b0052029e9b3edb20fe43f7f80f896aa9c0e6703d1ff049e7b8bc8aeb97
```

`Recall@5` 的分母是**标注的证据束数**，不随切分策略改变；`required_together` 的束被切开记 `broken`，
不算命中。`examples/eval-holdout-cases.json` 为保留集，封存至 Issue 12，**调参期间不要打开**。

**切分策略对照（Issue 15）**——同一批语料/问题/编码器/top-k 下对照切分策略，一次只改切分器：

```powershell
.\.venv\Scripts\python.exe scripts/compare_splitters.py `
  --out docs/evidence/issue15-splitter-comparison-20260910.json `
  --preview docs/evidence/issue15-splitter-preview-20260910.json
```

`--preview` 另存**切分预览与原文前后对照**（每个片段带 line span、kind、前后各 N 行原文）。
实测（开发集 D01–D10，k=5）：基线 0.850；`heading-block-v2` 0.900（+0.050）；`heading-procedure-v3` 0.400
（−0.450，粒度过碎）；`pdf-pages-v1` 未对照（语料无 PDF）。详见
`docs/evidence/issue15-splitter-comparison-20260910.md`。
