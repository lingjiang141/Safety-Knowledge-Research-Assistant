# Issue 06 完成证据：更新/删除资料后阻止旧证据进入新回答

日期：2026-09-10｜技能：**tdd**（一个外部行为测试 → 最小实现 → 回归，逐条红→绿）
本轮**无付费调用**（全部为本地测试与 CLI 演示）；账本保持 **0.471396** 元未变。

## 接口（用户确认）

- **更新语义**：同一来源（source 相同）重新导入不同内容 → **发布新版本，旧版本失效**（PRD 4.3）。
- **管理入口**：CLI 显式子命令 `update` / `delete`（与 `import` 并列，程序强制管理权限）。
- **测试范围**：以“更新后旧证据不再返回”为主，逐步扩展至删除、回答期间变更、标识稳定、历史失效提示。

## TDD 循环（先失败后通过）

| # | 行为测试 | RED 证据 | 最小实现 |
| --- | --- | --- | --- |
| 1 | 更新后检索不返回旧版本文本 | `ValueError: ...更新功能将在 Issue 06 实现` | `ingest` 支持同源更新：`_chunk` 抽公共切分；旧 chunks `active=0`，新版本原子发布 |
| 2 | 删除后检索为空、`read` 拒绝 | `AttributeError: 'Store' object has no attribute 'delete'` | 新增 `Store.delete(source)`：删除文档 + 停用其 chunks |
| 3 | 回答期间证据被删除 → 阻止过时答案 | `ValueError not raised` | 新增 `revalidate(store, evidence)`，在返回前复核版本/有效性 |
| 4 | CLI `update`/`delete` 显式管理 | `invalid choice: 'update'` | `cli.py` 增子命令；update 缺省沿用原 title/license |
| 5 | 片段标识按版本稳定、不复用 | —（随 1 的 digest 含 content_hash 已满足，测试固化） | 无需额外实现 |
| 6 | 向量索引排除失效片段 | `ValueError: 片段属于已失效的历史版本`（原会崩溃） | `vector.corpus/search` 仅取 `active=1` |
| 7 | 历史 run 保留旧版本 + 失效提示 | —（随 2 语义） | `read` 对已失效片段给出“失效”提示而非“不存在” |

**测试结果：39 tests 全部通过**（原 33 + 新增 6）。

## 关键改动

- `skra/store.py`：chunks 增 `version`/`active` 列 + 旧库 `ALTER TABLE` 迁移；
  `ingest` 支持同源更新（原子发布）；新增 `delete`；`read`/`search` 按 `active` 过滤；
  失效片段读取报“失效”而非“不存在”。
- `skra/answer.py`：新增 `revalidate`，回答返回前复核证据仍为当前有效版本（PRD 4.3 的“回答期间变更”）。
- `skra/vector.py`：索引与检索仅取 `active=1`，杜绝失效片段再入回答。
- `skra/cli.py`：新增 `update` / `delete` 子命令。

## 真实库兼容性

`.data/knowledge.sqlite3`（4 份资料、25 个片段）在打开时自动迁移，`active=1` 全部有效，未损坏既有数据。

## 演示命令（本地、免费）

```bash
python -m skra --db <db> import  a.md --title G --source urn:demo:guide --license CC0-1.0
python -m skra --db <db> update  b.md --source urn:demo:guide      # status=updated
python -m skra --db <db> search "alpha policy"                     # 旧文本不再出现
python -m skra --db <db> delete  urn:demo:guide                    # status=deleted
python -m skra --db <db> docs                                      # []
```

## 真实与模拟区分

- 本轮为**程序行为测试与本地 CLI 演示**，**不含真实模型调用**；回答契约的真实语义由 Issue 05/03
  的付费批次负责，未混称。
- `revalidate` 覆盖的是“证据失效”这一程序可判定行为，不等于语义正确性验证。

## 未解决问题

- 无阻塞项。切分粒度（`heading-lines-v1:20`）仍待 13/14/11 结构适配。
- 费用：0 新增；账本 0.471396 元（用户已核对平台账单一致）。
