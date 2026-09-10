# 13 — 按指南结构切分并展示完整证据

Status: done
State: done
Type: AFK
Milestone: M1D
User stories: US24, US27, US28
Source: [PRD](../../../PRD.md)

> **2026-09-10 完成**：按 **tdd** 逐条红→绿实现，**46 tests 通过**，无付费调用。
> 真实语料对比显示 Q04 定义段检索排名第 2→第 1。详见
> `docs/evidence/issue13-structured-guides-tdd-20260910.md`。

## What to build

将标题、段落、列表识别为可定位的内容块；导入结构化安全指南后，用原有向量检索查询定义或防护建议，返回带标题路径的完整证据。

## Acceptance criteria

- [x] 保留现有 heading-lines-v1:20 作为固定基线；新增显式策略标识、版本及选择理由，支持人工覆盖。
      （`SPLITTERS=(heading-lines-v1:20, heading-block-v2)`；CLI `--splitter` 显式覆盖。）
- [x] 说明性元数据与正文区分；来源、许可不丢失，但不默认作为正文候选挤占检索名额；不能仅靠关键词删除含义相近的正文。
      （`kind=metadata` 标记 Source/License 前言；`search` 正文优先排序；元数据仍可读、不删除。）
- [x] 标题路径补充到检索表示，但引用只来自真实原文跨度；不把补充上下文伪装为逐字引文。
      （`section` 暴露标题路径；evidence text 与原文行跨度逐行相等，测试固化。）
- [x] 定义与限定语、列表引导句与列表项尽量共存；超预算时按块边界拆分并保留父块关联，不静默截断。
      （`_split_block` 在列表引导行与其项之间不拆；按空行边界拆分。）
- [x] CLI 导入→索引→中文查询→证据展示可复现；重复导入与策略变更后的版本失效通过 TDD 测试。
      （`test_splitter_change_retires_old_chunk_ids`、CLI `--splitter` 测试；复用 06 版本失效机制。）
- [x] 准备正常、混合结构、结构不明三类样例；结构不明回退通用策略并记录原因，不猜成高置信分类。
      （无标题文档自动回退基线 + `splitter_note="结构不明…"`。）

## Blocked by

- [06-version-sync](06-version-sync.md) —— 已完成（version/active 机制由 13 复用）。

## Completion evidence

- **代码版本**：无提示词改动；`store.py`（结构切分 + kind 列 + 回退）、`cli.py`（`--splitter`）有实现变更。
- **语料版本**：`examples/corpus/` 五份 OWASP 指南（CC BY-SA 4.0），`heading-block-v2`。
- **测试结果**：**46 tests 通过**（`.\.venv\Scripts\python.exe -m unittest discover -s tests -v`）。
- **演示命令**：见 `docs/evidence/issue13-structured-guides-tdd-20260910.md`。
- **失败/边界案例**：Q06（跨资料）排名未改善，留待 14/11；结构不明回退已实现并测试。
- **真实与模拟区分**：程序行为测试 + 本地向量检索对比，**无真实模型调用**；
  排名改善为本地纯向量结果，样本小，**不构成正式评测或稳定收益**，未声称创新算法。
- **费用与未知预留**：0 新增；账本 **0.471396** 元（用户已核对平台账单一致），预留 0、`blocked=false`。
- **未解决问题**：Q06 跨资料欠项；架构检查 ①②⑤ 保留现状（用户裁定）。

## Comments

2026-09-10（完成）：**按 tdd 完成，Status → done**。用户确认接口（新增结构策略 + 可覆盖、
元数据默认排除）。TDD 六循环：定义/列表共存→元数据不挤占→标题路径不冒充引文→未知结构回退→
策略变更失效→CLI 覆盖，均先失败后最小实现。真实语料 Q04 定义段排名第 2→第 1，诚实记录 Q06 未改善。
账本未重置，无付费调用。**下一步：Issue 14（检索操作步骤时保留前提、代码与警告），按 tdd。**

