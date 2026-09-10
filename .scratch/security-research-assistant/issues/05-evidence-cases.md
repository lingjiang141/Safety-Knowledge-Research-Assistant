# 05 — 验证比较、冲突和攻击示例的回答边界

Status: ready-for-agent
State: in-progress
Type: AFK
Milestone: M1
User stories: US5, US6, US8, US9, US10, US11, US12, US13
Source: [PRD](../../../PRD.md)

## What to build

让已有回答路径覆盖两份资料比较、条件差异、无法裁决的冲突和资料内攻击命令，并给出各自证据。

## Acceptance criteria

- [ ] 比较题分别引用两方，不能编造分歧；冲突题展示条件，无法判定则保留分歧。
- [ ] 中文释义保留否定与条件；类比显式标注，重要事实无依据不能输出为定论。
- [ ] 攻击示例作为学习对象解释，不执行其命令；工具仅允许搜索、读取片段和元数据。
- [ ] 用受控资料测试越权工具、非法片段和资料注入；测试资料独立标注，不冒充官方结论。
- [ ] 保存十道开发题与冲突样例的实际行为；模拟契约测试与真实语义检查分开报告。

## Blocked by

- [04 — 中文问题检索多份英文资料并建立向量基线](04-vector-baseline.md)

## Completion evidence

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
