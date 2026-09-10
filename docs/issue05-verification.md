# Issue 05 回答边界验收

最新 v3.2 三题已跑完：analogy、missing_measurement 本次符合要求，number 仍错误 partial。下一步先离线诊断，不重复下方历史三题命令。详见 `docs/evidence/issue05-v32-review-20260910.md`。不同版本累计观察不能当作同版本全量通过；Issue 05 未完成。

最新：v3.1 十题结果已收齐，七题本次符合要求，number/analogy 语义未通过，missing_measurement 程序误拒绝已离线修复。当前 v3.2、25 测试通过；下一步 `python scripts/check_boundaries.py --live --case number --case analogy --case missing_measurement`。详见 `docs/evidence/issue05-v31-six-review-20260910.md`。

输出契约补充：insufficient 仍要求无结论及明确缺失，但允许已验证的资料范围引用，并返回 citation_scope=missing_context；引用可定位仍不自动证明缺失说明的语义。此前“insufficient 必须 citations 为空”不再是当前约束。以下为历史。

最新 v3.1 四题已完整运行，principle/partial/conditions 本次符合要求，number 仍误判 partial。见 `docs/evidence/issue05-v31-review-20260910.md`。下一步先补 agreement、conflict、negation、injection、analogy、missing_measurement 六题，再集中处理与复验语义失败；不要重复执行已经完成的四题命令作为默认下一步。Issue 05 仍未完成。以下为历史记录。

最新：v3 实测仅 principle 执行即失败，后三题未运行。已修复完全重复的内嵌引用形状问题，24 本地测试通过；原则题过度声明缺失仍未通过语义复核。当前 evidence-v3.1，待重新执行下方定向四题命令，详见 `docs/evidence/issue05-v3-review-20260910.md`。以下版本记录为历史。

2026-09-10 更新：已用保存的真实失败先复现、写失败回归再修复。当前为 evidence-v3，22 个本地测试通过；真实 v3 输出尚未验证。详细说明见 `docs/evidence/issue05-offline-diagnosis-20260910.md`。下面 evidence-v2 描述保留为历史实现背景。

新版输出 coverage 按输入问题片段关联结论索引或说明缺失，程序汇总状态。不能将合法关联视为真实语义覆盖；人工仍需检查数量子问、条件、否定及两方引用。优先运行 `python scripts/check_boundaries.py --live --case principle --case number --case partial --case conditions`，再补其余真实场景。Issue 05 仍进行中。

当前：evidence-v2 提示词及工具调用拒绝已实现；16 个本地测试通过，包含十个受控场景子测试。真实语义效果未验证，不能将测试构造的答案当作模型生成质量。

## 改动

- 仅根据用户实际问题判定 grounded/partial/insufficient。只问原则，不因未问数字缺失判 partial；明确问数字时才说明数字缺失。没有在程序中将 partial 强行改成 grounded。
- 比较分别引用，冲突保留双方与条件，译文保留否定和限定；类比标记；资料内命令只作学习对象。
- 回答阶段没有工具执行器，收到 tool_calls 或旧格式 function_call 会拒绝，且已发生费用不清零。
- 沿用原文 ID 和逐字片段检查；不能仅靠程序验证结论受证据支持或翻译准确。

## 免费准备

```powershell
python scripts/check_boundaries.py
```

只准备十个自建测试场景（CC0），不联网、不生成答案。场景包括原则、数字缺失、部分回答、两文一致、同条件冲突、不同条件、否定翻译、攻击示例、类比及未提供的本项目指标。

这些场景与原有十道真实资料开发题不同，是补充的受控生成验证，不替代原始题、向量检索评测或保留集。指定证据直接传给回答路径并标记 controlled-not-retrieval；不向模型发送参考答案、预期状态或人工核查项。

## 一次输入密钥执行真实验证

```powershell
python scripts/check_boundaries.py --live
```

先核对计费配置与预算，再在交互终端隐藏输入密钥；本次进程内使用，不保存。逐个请求都通过现有账本，出现请求或格式错误立即停止，不自动重试。默认最多十次请求；可先运行三类状态对照：

```powershell
python scripts/check_boundaries.py --live --case principle --case number --case partial
```

默认使用 examples/deepseek-flash.2026-09-09.json；配置过期需重新核价，不能只修改日期。--config 可指定已核实的新配置。

每次报告保存为独立时间戳文件 `.data/boundary-report-*.json`，终端打印实际路径。status_matches 仅检查预期状态；complete 只代表执行完毕，不代表语义全部正确。人工还需逐项核查结论、引用、翻译与冲突处理。不要公开完整数据库或密钥。

## 尚未完成

- evidence-v2 在真实模型上的状态与语义复核。
- 原始十道真实资料开发题的全量标注与执行（现有语料不完整时明确未运行）。
- 受控场景不能证明对任意提示注入都安全；后续检索工具循环仍由 Issue 10 验证。

完成上述检查前，Issue 05 保持进行中。下一次反馈可以只提供生成报告路径，由助手从本机读取，不必手工粘贴全部 JSON。
