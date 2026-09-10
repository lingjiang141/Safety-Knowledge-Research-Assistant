# 11 — 导入文本型 PDF 并按页核对回答

Status: done
State: done
Type: AFK
Milestone: M1D
User stories: US1, US2, US6, US7, US14, US15, US26, US27, US28
Source: [PRD](../../../PRD.md)

## What to build

扩展既有导入到问答路径，使文本型 PDF 的回答可追溯到正确页码和原文片段。

新增重点：文本型报告中的章节/段落恢复、跨页连续段落、重复页眉页脚处理，以及无法可靠提取时的显式回退。不要以 PDF 扩展名自动决定语义切分，沿用内容块策略。

## Acceptance criteria

- [x] 正文与重复页眉页脚分离，保留原页坐标或可复核定位；重复正文不得误删。
- [x] 多页报告可展示章节路径、原文定位与切分预览；阅读顺序混乱、复杂表格等明确提示不支持，不隐性丢失内容。
- [x] 使用 TDD 覆盖跨页段落、页眉正文同词、策略变更和提取失败；附实际页面对照。


- [x] 保存原文件 hash、来源、许可和提取版本，页码定义明确。
- [x] CLI 展示页码及原文；沿用同一版本、预算与引用校验机制。
- [x] 扫描件无正文、损坏文件和明显提取异常给出失败原因，不自动 OCR 或伪装成功。
- [x] 自建多页样例验证跨页定位及更新删除，真实 PDF 样例完成检索到引用演示。

## Blocked by

- [06-version-sync](06-version-sync.md)
- [13-structured-guides](13-structured-guides.md)

## Completion evidence

**状态：done（2026-09-10）**。按 **tdd** 完成，11 个红→绿循环；本地 **72 tests 通过**。

- **接口（用户确认）**：`pypdf` 纯文本层（不执行文件内任何内容）；chunks 增 **`page` 列**（1 基，
  Markdown 为 NULL）；重复页眉页脚→`kind=metadata`（**保留可查、不占正文名额**）；
  严格守 PRD 4.4 边界（**不做 OCR / 复杂表格 / 双栏重建**）。
- **代码**：新增 `skra/pdf.py`（`EXTRACTOR="pdf-text-v1"`、`PdfError`、阅读顺序异常检测）；
  `store.py` 新增 `PDF_SPLITTER="pdf-pages-v1"`、`_chunk_pdf`、`_page_furniture`、
  `_peel_pdf_provenance`、`_as_row`、按扩展名分派、`page` 列 + 旧库迁移；
  `cli.py` 的 `--splitter` 改为可选（默认按格式自动选）。
- **测试**：`tests/test_pdf_import.py` 12 例（正文带页码、引用落回真实页、装饰行标 metadata、
  正文重复句不误删、跨页两半可检索、扫描件失败、损坏文件给原因、提取版本+hash、更新/删除契约、
  CLI 页码、向量检索正文档先于装饰行）。
- **夹具**：`scripts/make_pdf_fixtures.py` 直接生成 PDF 语法（无额外依赖），5 页报告含重复页眉、
  仅页码不同的页脚、**第 3→4 页跨页续写段落**；引用与页内文本逐行相等。
- **调试暴露 3 个问题**：① 页码索引 off-by-one（装饰行未标 metadata，`at + i - 1` 修正）；
  ② 装饰行与正文粘连致正文继承 metadata 标签（装饰行强制独立成片段）；
  ③ 标题页前言未剥离（`peel_metadata` 规则正确拒绝，**保留现状并如实记录**，未放宽规则凑测试）。
- **依赖**：`pypdf==6.18.0` 已写入 `pyproject.toml` 与 `requirements-vector.lock.txt`；
  核实 pypdf **无运行时依赖**。
- **费用**：本轮**无付费调用**；账本保持 **0.471396** 元、可用 9.528604、预留 0、blocked=false。
- **未解决 / 转出**：
  - **架构发现 ⑤（两检索器规则重复）确认为真实缺口**：`store.search` 有正文优先于 metadata 的排序，
    `vector.search` 没有；PDF 页面装饰行成为常规 metadata 片段后更易触发。已加护栏测试固化期望，
    **未顺手改检索器**，留待 08 前处理。
  - **端到端语义未验证**：本次为本地测试 + CLI 演示，**未做真实付费调用**，PDF 按页定位的语义效果
    未经真实模型验证（与 Issue 03 的验收性质不同，不得混称）。
  - Q06 跨资料比较仍未改善（13/14 遗留），不改检索器。
- **证据**：`docs/evidence/issue11-pdf-tdd-20260910.md`。

## Comments

**已完成（2026-09-10）**。遵守 PRD 的资料边界及 10 元总预算。切分为工程改良，不声称创新或效果提升比例。

