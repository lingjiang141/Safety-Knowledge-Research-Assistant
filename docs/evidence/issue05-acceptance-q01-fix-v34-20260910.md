# Issue 05：原始资料验收 Q01 中断诊断（同一片段多引用被误拒）

## 现象

用户在本机付费运行 `scripts/check_acceptance.py --live`，报告
`docs/evidence/issue05-acceptance-live-halted-q01-20260910.json`
（源 `.data/acceptance-report-20260910T071149270502Z.json`）。**Q01 就报错停止**，
Q02–Q10 未执行：

- Q01 错误：`回答结构或引用校验失败：引用标识无效或重复。 已发生费用仍保留（call_id=34）。`
- 账本：0.166719 → **0.179976** 元（本批新增 0.013257 元），预留 0，blocked=false。

> 注意：运行器当时遇第一个错误即 `break`，所以十题只跑了 Q01。这也是本轮一起修的运行器缺陷。

## 复现（离线，不付费）

失败正文保存在 run 91（`answer_run_id`），证据来自 run 90。离线 `validate` 复现同一拒绝：

```
REJECTED: 引用标识无效或重复。
```

模型实际输出（节选）：顶层 `citations` 有 **两条**，`id` 相同（`2d61fd19…`，即 LLM06 片段），
分别引用该片段内 **两句不同的原文**：

1. `Agent-based systems will typically make repeated calls to an LLM using output from previous invocations…`
2. `The decision over which extension to invoke may also be delegated to an LLM 'agent'…`

两条 quote 都是该 chunk 的真实连续子串，**不是编造**。

## 根因

`validate()` 用 `cid in verified` 强制「一个证据片段在顶层 citations 最多出现一次」。
但提示词从未声明这条规则，模型从同一段落取两句不同原文是合法行为。
结果：一个合法回答被整条丢弃，且阻断整个批次。

**这是契约过严，不是模型错误。** 关键是修复时不能走到另一个极端——静默丢弃第二条 quote
会违反项目既定原则「不得静默丢弃冲突/内嵌引用」。

## 修复（最小、先失败回归）

1. 新增失败回归 `tests/test_question_coverage.py`：
   - `test_two_distinct_quotes_from_one_chunk_are_kept_not_rejected`（修复前 ERROR，复现原拒绝）；
   - `test_duplicate_id_with_conflicting_quote_is_still_rejected`（负向守卫：重复 id 若 quote
     不是逐字子串仍必须拒绝，确保没有放宽校验）。
2. `skra/answer.py` `validate()`：
   - `verified` 由 `{cid: entry}` 改为 `{cid: [entry, …]}`，允许同一 id 的多条**不同** quote；
   - 仍拒绝：未知 id、非逐字子串 quote、空释义、以及**完全相同**的重复条目；
   - 内嵌 `claims[].citations` 的 `canonical` 改为 `{cid: [entries]}`，按 id 与任一条目精确匹配；
   - 返回 `citations` 展平为列表，保留所有已验证 quote。
3. 提示词补一行：同一片段可用多条不同 quote 各列一条，同一 id 不得出现完全相同的重复条目；
   版本升到 **evidence-v3.4**，`skra/cli.py` replay 版本集合同步加入 v3.4。
4. 运行器 `scripts/check_acceptance.py`：付费批次遇单题 `ValueError` **记录后继续**，
   仅在账本被阻塞时停止，避免一题失败浪费整批。

## 结果

- 本地 **29 tests 全部通过**（原 27 + 新增 2）。
- 离线复验真实 Q01 正文：现被接受，`status=partial`，两条 quote 均保留，`claims[0].citations` 正常。
  Q01 判 partial 是因为缺 S01（What are agents?）——属既定欠项，**不是**本次 bug。
- 免费 preflight 仍通过（12870 字节、最大预留 3.152928 元、budget_ready=true）。本次无新增付费调用。

## 限制

- 程序只校验显式结构（id 存在、quote 为逐字子串、无完全重复条目）；**不判语义**，
  不保证 quote 真的支持结论。
- v3.4 真实效果未验证，不宣称已修复；需用户重跑批次确认 Q01–Q10 端到端。
- `excluded_doc_ids` 仍只剔除合成夹具；S01 未导入的 Q01 欠项保留。

## 下一步

用户在本机重跑：

```bash
.\.venv\Scripts\python.exe scripts\check_acceptance.py --live
```

预期：Q01 不再中断，十题均产出结果（个别题若语义不合要求，由助手复核，不因结构通过即称达标）。
Issue 05 保持进行中，不进入 06。
