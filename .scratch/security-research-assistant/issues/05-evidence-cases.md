# 05 — 验证比较、冲突和攻击示例的回答边界

Status: done
State: done
Type: AFK
Milestone: M1
User stories: US5, US6, US8, US9, US10, US11, US12, US13
Source: [PRD](../../../PRD.md)

> **2026-09-10 完成**：受控十题（v3.3）与原资料十题（v3.5 全批，随 03 收尾一并完成）
> 两条验收路径均达标，用户已做最终语义验收。**遗留 Q04/Q06 检索未命中欠项**转 13/14/11 结构适配，
> 不阻塞本任务收尾（按验收草案「固定检索器」不中途更换）。

## What to build

让已有回答路径覆盖两份资料比较、条件差异、无法裁决的冲突和资料内攻击命令，并给出各自证据。

## Acceptance criteria

- [x] 比较题分别引用两方，不能编造分歧；冲突题展示条件，无法判定则保留分歧。
      （受控 agreement/conflict/conditions 三题符合要求；Q02 两类注入分别引自对应定义段。）
- [x] 中文释义保留否定与条件；类比显式标注，重要事实无依据不能输出为定论。
      （受控 negation/analogy 通过；原资料题 quotes 全部逐字命中原文、释义保留条件。）
- [x] 攻击示例作为学习对象解释，不执行其命令；工具仅允许搜索、读取片段和元数据。
      （受控 injection 题解释不执行、不拒答；Q10 将“忽略之前指令”示例作为分析对象，未执行。）
- [x] 用受控资料测试越权工具、非法片段和资料注入；测试资料独立标注，不冒充官方结论。
      （边界契约测试覆盖 tool_calls 拒绝、未知引用拒绝；合成夹具 85772b00… 在真实题中剔除。）
- [x] 保存十道开发题与冲突样例的实际行为；模拟契约测试与真实语义检查分开报告。
      （受控十题报告与复核、原资料十题报告与复核均已落盘，分开记录，见 Completion evidence。）

## Blocked by

- [04 — 中文问题检索多份英文资料并建立向量基线](04-vector-baseline.md)

## Completion evidence

- **代码版本**：提示词 `evidence-v3.5`，输出上限 1500（常量 `OUTPUT_TOKEN_LIMIT`）；无未提交产品代码改动。
- **演示命令**：
  - 受控场景：`python scripts/check_boundaries.py`（免费）/ `--live`（付费）
  - 原资料题：`.\.venv\Scripts\python.exe scripts\check_acceptance.py`（免费）/ `--live`（付费）
- **测试结果**：本地 **31 tests 通过**。
- **真实输出与复核**：
  - 受控十题（evidence-v3.3）：报告 `issue05-live-v33-three-20260910.json`、`issue05-live-v33-seven-20260910.json`；
    复核 `issue05-v33-three-review-20260910.md`、`issue05-v33-seven-review-20260910.md`。
    **十题全部有符合要求的观察**（number 为 v3.1/v3.2 连续失败后首次通过）。
  - 原资料十题（evidence-v3.5 全批，2026-09-10）：报告 `issue03-acceptance-live-v35-full-20260910.json`
    （`complete=True`、状态命中 8/10）；复核 `issue03-acceptance-review-v35-full-20260910.md`。
    Q01 grounded（换题生效）、Q02/Q03/Q05/Q07/Q10 grounded、Q08 insufficient、Q09 partial；
    修复确认：v3.5 全批生效（Q07 不截断、无未关联 claims 报错）。
- **真实与模拟区分**：受控十题是**受控证据（非真实检索）**，仅证明契约与生成边界；
  原资料十题是**真实资料 + 真实检索 + 真实模型**。两者分开报告，不混称，不用受控结果代替真实验收。
- **费用与未知预留**：账本累计 **0.471396** 元（用户已核对平台账单一致），预留 0、`blocked=false`。
- **未解决问题（转出，不阻塞收尾）**：**Q04/Q06 检索未命中**——`heading-lines-v1:20` 切分过粗
  稀释定义段（所需片段向量排序第 7），模型诚实降级、无编造；**不改固定检索器、不改题面预期蒙对**，
  记入 **Issue 13/14/11 结构适配**。

## Comments

2026-09-10（完成）：**两条验收路径均达标，Status → done**。受控十题（v3.3）全部符合要求；
原资料十题在 v3.5 全批通过主要题项，Q04/Q06 检索欠项转出。随 03 收尾一并完成用户最终语义验收。
本轮无产品代码改动，账本未重置，未动任何标签。下一步进入 **06**（按 tdd）。

2026-09-10 原始资料开发题（真实资料 + 向量检索）验收：新增 `examples/acceptance-cases.json` 与
`scripts/check_acceptance.py`，十题接入真实知识库。v3.4 全跑（状态命中 5/10）后修 2 条生成缺陷升
**evidence-v3.5**（缺失说明不入顶层 claims；输出上限 800→1500），定向重跑确认：
**Q07 → grounded、Q09 → partial**。**Q01 已换题**（原题依赖 S01，S01 无开放许可不可导入）为
「提示注入与越狱有什么区别？」，**待真实运行**。**Q04/Q06 为检索未命中欠项**（所需片段向量排序第 7），
按「固定检索器」不改，记入结构适配待办（13/14/11）。
报告/复核：issue05-acceptance-live-v34-full / issue05-acceptance-review-v34 /
issue05-acceptance-live-v35-targeted / issue05-acceptance-review-v35-targeted-20260910。
**十题全批重跑与用户最终语义验收仍保留**，State 保持进行中。账本 0.344997 元。

2026-09-10 v3.3 十题受控复验：三题（number/partial/conditions）+ 七题
（principle/agreement/conflict/negation/injection/analogy/missing_measurement）在同一 evidence-v3.3 下
**全部有符合要求的观察**，number 为 v3.1/v3.2 连续失败后首次通过。
报告 issue05-live-v33-three-20260910.json 与 issue05-live-v33-seven-20260910.json；
复核 issue05-v33-three-review / issue05-v33-seven-review-20260910.md。
**不等于稳定准确率或正式评测**，原始资料开发题欠项、03 欠项、用户最终语义验收保留。
账本累计 0.166719 元。State 保持进行中。

2026-09-10 v3.3 真实复验（三题）：number/partial/conditions 三题全部符合要求（number 首次通过），
报告 docs/evidence/issue05-live-v33-three-20260910.json，复核 docs/evidence/issue05-v33-three-review-20260910.md。
账本累计 0.125391 元。State 保持进行中。

2026-09-10 v3.3 修复：number 场景按 diagnose 完成离线诊断、先失败回归、最小修复。`apply_coverage` 增加
`answered` 标记（只写 missing、无 claims 的问题项不计为已答），提示词升 v3.3 明确“只索取数值的问题项
不能由原则凑部分答案”。27 tests 通过。详见 docs/evidence/issue05-number-fix-v33-20260910.md。
本轮另发生 git 对象库损坏并按用户选择从工作区重建基提交 a08ac81，见 .data/git-recovery-20260910T143815/INCIDENT.md。
无新增助手侧付费调用；State 保持进行中。

2026-09-10 v3.2：analogy/missing_measurement 本次符合要求；number 仍误判 partial，见 docs/evidence/issue05-v32-review-20260910.md。下一步先离线诊断覆盖契约，不重复无改动付费测试。25 个程序测试的历史结果不证明语义全部通过；State 保持进行中。累计保守记账 0.108174 元。

2026-09-10 十题汇总：七题本次符合要求，number/analogy 语义未通过；missing_measurement 原程序误拒绝，已先失败测试后允许有效缺失上下文引用（claims 仍为空），25 测试通过。当前 v3.2，待上述三题真实复验，未关闭。详细证据见 docs/evidence/issue05-v31-six-review-20260910.md。累计记账 0.093489 元。

2026-09-10 v3.1 四题：principle/partial/conditions 本次符合需求；number 仍将相关原则算作纯数量问题的部分答案，返回 partial 而非 insufficient，未通过。详见 docs/evidence/issue05-v31-review-20260910.md。先补同版本其余六题，再集中修复与复验；原资料开发题欠项保留，State 不变。累计保守记账 0.062625 元。

2026-09-10 v3 实测更新：principle 因内嵌引用对象停止，number/partial/conditions 未执行。已先失败回归后加入完全相同引用的无损转换；24 测试通过。原则题扩大要求的语义误判仍在，evidence-v3.1 提示词调整待实测。累计保守记账 0.042213 元。见 docs/evidence/issue05-v3-review-20260910.md；不关闭任务。

2026-09-10 后续：已离线复现并加入先失败后修复的回归；evidence-v3 使用显式问题覆盖记录汇总状态，拒绝漏项。22 个本地测试通过。测试中的 coverage 为人工输入，不能证明真实语义修复。无新增付费调用，当前进程无密钥；等待定向真实验证，State 仍 in-progress。详见 docs/evidence/issue05-offline-diagnosis-20260910.md。

2026-09-09：已实现 evidence-v2 提示词、禁止回答阶段工具调用、十个受控生成场景及 check_boundaries.py（免费准备/真实执行）。16 个测试通过，其中十个受控答案只验证契约，不证明真实模型效果。已按先失败后通过验证 tool_calls 不能被静默接受。

真实生成待运行；累计账本保持 0.011334 元，本轮未付费。详见 docs/issue05-verification.md。原有十道真实资料开发题未全部运行，不据受控测试关闭任务。

完成时填写：代码版本、演示命令、测试结果、真实与模拟验证的区分、费用与未知预留、未解决问题。不得仅凭复选框关闭任务。

## Comments

尚未开始实现。遵守 PRD 的资料边界及 10 元总预算；AFK 表示常规实现无需逐项确认，不表示允许跳过密钥、预算或人工语义复核。



## 已观察到的回归场景

输入：根据资料，应该如何限制智能助手可调用的工具数量？证据已支持最小必要原则，但真实模型返回 partial，missing 提到用户未要求的具体数量和操作规则。应按用户实际提问判定覆盖程度，不主动扩大问题后再宣告缺失。在 Issue 05 中补充原则问题应 grounded、明确询问未提供数值时才 partial/insufficient 的对照验收；不要把所有 partial 强改为 grounded。


## 2026-09-10 最新真实结果

报告见 docs/evidence/issue05-live-20260909.json。partial 错判 grounded 且漏答数量；conditions 因缺失 missing 校验失败（call_id=9、boundaries run_id=14），后四题未执行。不得以状态匹配题数或本地测试关闭本任务。新窗口继续步骤见 HANDOFF.md；原失败响应已导出供离线复现。
