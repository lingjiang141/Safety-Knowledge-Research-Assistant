# Issue 13 完成证据：按指南结构切分并展示完整证据

日期：2026-09-10｜技能：**tdd**（一个外部行为测试 → 最小实现 → 回归，逐条红→绿）
本轮**无付费调用**（本地测试 + 本地向量检索对比）；账本保持 **0.471396** 元未变。

## 接口（用户确认）

- **切分策略**：新增 `heading-block-v2` 结构切分；保留 `heading-lines-v1:20` 为固定基线；
  导入时可用 `--splitter` 显式覆盖。
- **说明性元数据**：识别 `Source/License/Publisher/Retrieved` 及「adapted excerpt」注记，
  标记为 `kind=metadata`、**默认不占正文检索名额**（仍可读到，不删除）。

## TDD 循环（先失败后通过）

| # | 行为测试 | RED 证据 | 最小实现 |
| --- | --- | --- | --- |
| 1 | 定义句与其列表项共存同一片段（不被 20 行截断） | `TypeError: unexpected keyword 'splitter'` | `ingest(splitter=)` + `_chunk_structured`（按标题分块、列表引导行与其项不拆） |
| 2 | 元数据不挤占正文检索名额 | `AssertionError: 含 License 片段必须标记 metadata` | chunks 增 `kind` 列；剥离标题块的元数据前言；`search` 正文优先排序 |
| 3 | 标题路径用于检索表示、引用仍是逐字原文 | —（已满足，测试固化） | `section` 暴露标题路径；evidence text 与原文跨度逐行相等 |
| 4 | 结构不明回退通用策略并记录原因 | `'heading-block-v2' != 'heading-lines-v1:20'` | 无标题文档自动回退基线 + `splitter_note="结构不明…回退…"` |
| 5 | 策略变更后旧片段标识失效 | —（复用 06 机制） | 策略变更视为新版本，旧 chunk 退役 |
| 6 | CLI `--splitter` 显式覆盖 | `unrecognized arguments: --splitter` | `cli.py` import/update 增 `--splitter` |

**测试结果：46 tests 全部通过**（原 40 + 新增 6，`tests/test_structured_guides.py`）。

## 真实语料对比（`examples/corpus/` 五份 OWASP 指南）

向量检索（同编码器、同 top-5）**Q04「三概念区别」的命中排名从第 2 提升到第 1**：

| 策略 | Q04 定义段排名 | 证据块 |
| --- | --- | --- |
| v1 `heading-lines-v1:20` | 第 2（score 0.4599） | `LLM06…` **L1–18**（标题+元数据+定义混杂） |
| v2 `heading-block-v2` | **第 1**（score 0.4780） | `LLM06…` **L9–18**（纯定义段） |

根因改善：结构切分把定义段与标题/版权前言分离，**去掉了元数据对定义段向量的稀释**
（`L1–18` → `L9–18`），正对应 Issue 05 遗留的 Q04 检索欠项。

**诚实的边界**：Q06（跨两份资料比较）仍为第 4 名——跨资料比较要同时召回两方证据，
结构切分单资料内有效，跨资料排序留待 **14/11**。**不宣称全面解决检索欠项。**

## 关键改动

- `skra/store.py`：`STRUCTURED_SPLITTER`/`SPLITTERS`；`_chunk_structured` + `_split_block`；
  `is_metadata_block`/`META_LINE`/`ADAPT_NOTE`/`METADATA_SECTION`；chunks 增 `kind` 列（含旧库迁移）；
  `ingest` 支持 `splitter` 与未知结构回退；`search` 正文优先于元数据。
- `skra/cli.py`：`import`/`update` 增 `--splitter`。

## 演示命令（本地、免费）

```bash
python -m skra --db <db> import <guide.md> --title G --source urn:x --license "CC BY-SA 4.0" \
    --splitter heading-block-v2          # status=imported, splitter=heading-block-v2
python -m skra --db <db> search "root cause excessive functionality"   # 定义段为一整块
```

## 真实与模拟区分

- 本轮为**程序行为测试 + 本地向量检索对比**，**不含真实模型调用**；
  检索排名的改善是**本地纯向量**结果，样本极小（5 份资料），**不构成正式评测或稳定收益**。
- 结构切分为**工程改良**，不声称原创算法或效果提升比例；固定检索器未更换。

## 未解决问题

- Q06 跨资料比较排名未改善（待 14/11）。
- 架构检查发现（①提示词版本白名单 ②切分不变量分散 ⑤检索规则重复）仍存在；
  13 按 ②⑤ 评估了影响面，未顺手重构（用户裁定保留现状）。
- 费用：0 新增；账本 0.471396 元（用户已核对平台账单一致）。
