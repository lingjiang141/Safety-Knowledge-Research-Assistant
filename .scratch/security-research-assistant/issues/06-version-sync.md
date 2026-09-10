# 06 — 更新和删除资料后阻止旧证据进入新回答

Status: done
State: done
Type: AFK
Milestone: M1
User stories: US2, US14, US15, US16
Source: [PRD](../../../PRD.md)

> **2026-09-10 完成**：按 **tdd** 逐条红→绿实现，**39 tests 通过**，无付费调用。
> 详情见 `docs/evidence/issue06-version-sync-tdd-20260910.md`。

## What to build

通过管理 CLI 更新或删除资料，贯通有效版本发布、检索过滤、回答前复核及历史引用提示。

## Acceptance criteria

- [x] 同版本同配置片段标识稳定，新版本不复用旧标识指向不同文本。
      （片段 id 的 digest 含 content_hash；`test_chunk_id_is_stable_per_version_and_never_reused`。）
- [x] 构建失败不发布半成品；切换后检索不返回旧内容，删除后新回答不可引用已删除片段。
      （`ingest` 在单事务内先停用旧 chunks 再发布新版本；`read`/`search` 按 active 过滤；
      `test_update_replaces_old_evidence_in_search`、`test_delete_removes_source_from_search_and_read`。）
- [x] 回答生成期间更新或删除证据时阻止过时答案并提示重新查询。
      （新增 `answer.revalidate`，返回前复核证据版本；`test_answer_blocked_when_evidence_retired_during_generation`。）
- [x] 历史引用保留版本与失效提示；程序强制限制管理操作，不授予回答模型写入工具。
      （历史 run 保留旧 version；`read` 对失效片段报“失效”；管理操作仅在 CLI 子命令，
      回答模型无任何写入工具；`test_history_keeps_old_version_but_marks_it_stale`。）
- [x] 完整测试新增、重复导入、修改、删除、失败恢复与回答期间变更场景。
      （`tests/test_version_sync.py` 5 例 + `test_cli.py` 更新 + `test_vector.py` 失效排除，共 39 tests。）

## Blocked by

- [04 — 中文问题检索多份英文资料并建立向量基线](04-vector-baseline.md)

## Completion evidence

- **代码版本**：无提示词改动；`store.py` / `answer.py` / `vector.py` / `cli.py` 有实现变更。
- **测试结果**：**39 tests 通过**（`.\.venv\Scripts\python.exe -m unittest discover -s tests -v`）。
- **演示命令**：见 `docs/evidence/issue06-version-sync-tdd-20260910.md`（import→update→search→delete）。
- **真实与模拟区分**：本轮为程序行为测试 + 本地 CLI 演示，**无真实模型调用**；
  回答语义由 Issue 05/03 付费批次负责，未混称。
- **费用与未知预留**：0 新增；账本 **0.471396** 元（用户已核对平台账单一致），预留 0、`blocked=false`。
- **未解决问题**：无阻塞项；切分粒度待 13/14/11。
- **真实库兼容**：`.data/knowledge.sqlite3`（4 资料/25 片段）自动迁移，未损坏既有数据。

## Comments

2026-09-10（完成）：**按 tdd 完成，Status → done**。用户确认接口（更新=新版本失效旧版、CLI 显式子命令）。
TDD 逐条循环：更新→删除→回答期间变更→CLI→标识稳定→向量失效排除→历史失效提示，均先失败后最小实现。
账本未重置，无付费调用。**下一步：04–06 后的架构检查（06 后、13 前），再进入 13。**
