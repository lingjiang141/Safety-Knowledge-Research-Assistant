# Issue 05 number 场景离线诊断与修复（v3.3）

2026-09-10。使用 diagnose 流程；全程离线、未联网、未产生新费用。原始报告与失败证据未修改。

> 前置说明：本轮执行中出现一次 git 对象库损坏事故（与本修复无关），
> 记录见 `.data/git-recovery-20260910T143815/INCIDENT.md`。工作区与本修复代码未受影响。

## 1. 反馈回路（Phase 1–2）

用公开 `answer` 接口 + 测试注入的模型传输函数离线重放已有报告，无需付费、可重复、确定性：

- 证据：`.data/boundaries.sqlite3` 的检索 run 53（number、controlled-not-retrieval，仅 1 条证据
  `Only grant the tools necessary for the intended task.`）。
- 失败正文：`.data/boundaries.sqlite3` 的 answer run 54（call_id=21，prompt evidence-v3.2），
  已复制到 `docs/evidence/issue05-live-v32-20260910.json`，其 `coverage` 字段完整保留。

复现症状（与用户所报一致）：

```
question : 工具数量最多应设为几项？
coverage : [{"question_id":"q1","claims":[0],"missing":"资料未提供工具数量最多应设为几项的具体数字。"}]
claims   : ["资料未给出工具数量上限的具体数字，仅提出只授予完成任务所必需的工具这一原则。"]
推导状态 : partial      ← 期望 insufficient
```

新增回归 `test_pure_number_question_without_a_number_is_insufficient_not_partial`
在修复前失败，断言报出的正是 `'partial' != 'insufficient'`。

## 2. 假设（Phase 3，按可能性排序）

1. **提示词契约缺口**：提示词只规定“**只问**数量且数量缺失时 claims 为空”，
   没有覆盖“数量与原则/同题并存”这一情况；模型于是沿用 partial 模板。
   预测：补充“只索取数值的问题项不能由原则凑成部分答案”后，该场景转为 insufficient。
2. **程序层缺少结构性守卫**：`apply_coverage` 只能校验索引合法，无法判断结论是否答到了问题。
   预测：只改提示词、不改程序，模型的 `claims:[0]` 映射仍会推导成 partial。
3. **partial 正文串味**：模型照抄 partial 场景的形状。预测：跨版本应随机波动——
   但 v3.1/v3.2 稳定复现同一形状，故非主因。

探针（离线）验证假设 2：把该项 coverage 改为 `claims:[]` + missing，程序即推导 `insufficient`；
保留原则结论映射则推导 `partial`。说明**程序层需要“该项是否真有结论”的信号**，
不能仅靠模型的顶层 status。

## 3. 修改（Phase 5，最小改动）

1. `skra/answer.py` `apply_coverage`：引入 `answered` 标记。
   某一问题项只在“关联了结论、且未声明缺失”或“关联了结论”时才算被回答；
   **只写 missing、没有 claims 的问题项不计为已答**。
   状态推导由 `used and missing` 改为 `missing and answered`：
   - 有结论 + 有缺失 → partial（真正的部分回答）
   - 无任何真实结论、只有缺失 → insufficient（本次 number 场景）
   - 全部有结论、无缺失 → grounded
2. 提示词 `evidence-v3.3`（版本号同步）：补齐两条契约——
   - “即使同一问题里其余部分能由原则回答，只索取具体数量的那个问题项仍不因原则结论算作已答”；
   - coverage 段：“某个问题项若只索取证据中没有的具体数值……该项也不能关联原则结论来凑部分答案”。
3. `skra/cli.py`：replay 的覆盖校验版本集合加入 `evidence-v3.3`。

未使用场景 ID 或题目字符串硬编码，未添加关键词/正则的数量检测，未引入额外付费判题器。

## 4. 回归结果

`python -m unittest discover -s tests`：**27 tests 全部通过**。

新增/覆盖的行为（经公开 `answer` 接口、临时知识库与账本、注入传输函数，未访问 API）：

- number 纯数量题、证据无数字 → insufficient，claims 为空，missing 含“数字”；
- 原则+数量并存（partial 题）→ 仍为 partial，原则结论归 q1、数量项 q2 声明缺失；
- 状态推导边界逐一核对：单题 grounded / 纯缺失 insufficient / 单题内部 partial /
  两题一答一缺 partial / 两题皆缺 insufficient；
- 原有 v3.1/v3.2 回归（conditions 覆盖、missing_measurement 缺失上下文引用、
  partial 漏答拒绝、非法 coverage 拒绝、CLI 离线重放）仍全部通过。

端到端 `validate` 校验 number 正确正文 → `insufficient`。

## 5. 限制与下一步

- 程序只能核对**显式结构**（索引、原文逐字、覆盖记录），不能证明模型语义上真的答到了数字。
  提示词补充是新假设，**真实语义效果仍未验证**；本改动消除了“原则结论被算作数量部分答案”的
  结构性缺口，不等于模型已稳定正确。
- 下一步按用户指示做定向真实复验（离线诊断已完成，不再要求用户重交旧报告）：

```powershell
python scripts/check_boundaries.py --live --case number --case partial --case conditions
```

  以 v3.3 结果确认 number 是否转为 insufficient、partial/conditions 是否保持符合要求，
  再补齐此前未执行的 negation/injection 等场景。原始资料开发题欠项保留。

- 架构痛点记录（供 06 后、13 前的 improve-codebase-architecture）：`skra/cli.py` 的 replay
  按提示词版本逐次维护 coverage 校验版本集合，每次新增提示词版本都要手动同步一处，
  属“同一规则在多入口漂移”的候选检查点。
