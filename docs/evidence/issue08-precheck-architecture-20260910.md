# Issue 08 前置架构检查复核：⑤ 检索规则重复（有真实新证据）

日期：2026-09-10｜技能：**improve-codebase-architecture**（按 08 卡片要求执行）
范围：`skra/store.py`、`skra/vector.py`、`skra/answer.py`、`skra/cli.py`、`skra/boundaries.py`、
`tests/test_question_coverage.py`
**结论：⑤ 在本任务中会成为真实阻塞，做一次刻意最小的局部收敛（只抽共享规则，不重写检索器）。**

## 1. 为什么这次要动（与上次裁定的区别）

04–06 后的完整架构检查（`docs/evidence/architecture-review-20260910.md`）已记录 5 项发现，
用户裁定**当时**不重构。那次裁定正确：当时没有新代码要写进这些重复点。

**本任务改变了这个前提。** Issue 08 要新增 **BM25** 与 **RRF 融合**两条检索路径。
架构检查对 ⑤ 的原话就是：

> 摩擦：`runs` 表列签名改动需同步 4 处，无单点守卫；**新增检索后端（BM25/混合）会再复制。**

现在正是那个时刻。若直接实现，`limit 校验`、`active 过滤`、`runs 持久化` 三处规则
会从 **2 份变成 4 份**，且没有任何单点守卫。这是「为新代码而收敛」，不是「为重构而重构」。

## 2. 复核证据（实测，非印象）

同一组规则在各入口的实际分布：

| 入口 | limit 校验 | active 过滤 | runs 持久化 | 候选装配 |
| --- | --- | --- | --- | --- |
| `store.search`（`store.py:668-695`） | ✓ | ✓ | ✓ | `self.read(cid)` |
| `vector.search`（`vector.py:73-99`） | ✓ | ✓ | ✓ | `store.read(cid)` |
| `boundaries.py`（受控适配器） | — | — | ✓ | — |
| `tests/test_question_coverage.py` | — | — | ✓ | — |

逐字重复的规则：

- **limit 校验**：`if not query.strip() or not 1 <= limit <= 20: raise ValueError("问题不能为空；limit 必须为 1–20。")`
  —— 两处**逐字相同**。
- **active 过滤**：`store.search` 用 `WHERE active=1`；`vector.search` 用
  `{r["id"] for r in ... WHERE active=1}` 再过滤循环。**语义相同、写法不同**（这就是漂移的土壤）。
- **runs 持久化**：`INSERT INTO runs(created,query,result,elapsed_ms) VALUES (?,?,?,?)`
  —— 4 处写同样的列签名，无单点守卫。改列需同步 4 处。

### 2.1 附带发现：body 优先排序只在一边（⑤ 的另一半）

- `store.search` 有 `(-score, row["kind"] != "body", row["id"])` —— 正文片段优先于出处样板
  （Issue 13 加的护栏，防止 License 行占正文名额）。
- `vector.search` **没有**这个规则，只按 `(-score, id)` 排。

Issue 11 已确认为真实缺口并加了护栏测试。**本任务新增 BM25 时，这个差异必须被明确决定**：
BM25 是否沿用 body 优先？若沿用而向量不沿用，融合时两路对「同一分数谁先」的判断不一致，
RRF 的排名输入就带着未声明的不对称。

## 3. 收敛范围（刻意最小）

**只抽三条共享规则，不重写任何检索器、不改排序算法、不动 ③。**

新增到 `skra/store.py`（检索规则的单一出处）：

1. `check_search_args(query, limit)` —— limit 校验，4 处复用。
2. `record_run(db, query, result, elapsed)` —— runs 持久化，4 处复用；返回 `run_id`。
3. `active_chunk_ids(db)` —— active 片段 id 集合，供各路检索统一过滤。

**刻意不动**：

- ③ `answer()` 巨函数：本任务不改它的职责划分。它只依赖 `search(query, limit)` 一个签名，
  收敛后该签名不变，因此**不需要动 `answer()`**（这是收敛成本低的关键）。
- ① 提示词版本白名单：与检索无关。
- ④ `revalidate` 可注入性：与检索无关。
- 各检索器的**排序算法本身**：`store.search` 的 body 优先、`vector.search` 的纯余弦
  保持原样，只在融合层显式声明两路的差异（见 §2.1），**不擅自把 body 优先强加给向量**。

## 4. 不做什么（防止重写陷阱）

- 不引入检索器基类/插件框架 —— 当前只有 3–4 路检索，框架的成本大于收益。
- 不统一排序算法 —— 各路检索的排序差异是**设计选择**，不是重复；只有「校验/过滤/持久化」
  是真正的重复。
- 不改 `answer()` 的公共签名 —— 契约稳定优先。
- 不为「以后可能加第五路」预留抽象 —— 只在第三、四路真正要复制时才抽。

## 5. 验收方式（可复核）

- 收敛后 **既有 98 tests 必须全绿**（不改变任何外部行为）。
- 新增回归：**runs 列签名只在一处**（构造一个 fake db 计数 `INSERT INTO runs` 的调用点，
  或断言公开入口都经 `record_run`）。
- 新增回归：**limit 校验只在一处**（两路检索对 `limit=0`/`limit=21`/空问题抛同样错）。
- 收敛前后**检索结果逐字节相同**（同 15 的等价性做法：对拍候选 id 序列 + 分数）。

## 6. 结论

**做局部收敛**（范围见 §3），理由是「本任务必然要复制第三、四份」这一**新的代码证据**，
而非「到了某个编号」。收敛后立即按 TDD 实现 BM25 与 RRF。
