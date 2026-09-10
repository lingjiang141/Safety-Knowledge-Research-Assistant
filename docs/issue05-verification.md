# Issue 05 回答边界验收

## 结论（2026-09-10 收尾）

**Issue 05 已完成（done）**。当前提示词 `evidence-v3.5`，输出上限 1500 token，本地 **98 tests 通过**
（收尾当时为 72；07 新增评测 21 例、15 新增切分标签 5 例）。
两条验收路径均达标：

1. **受控场景（`check_boundaries.py`，非检索）**：v3.3 下十题**全部有符合要求的观察**（number 首次通过）。
   报告 `docs/evidence/issue05-live-v33-three/seven-20260910.json`。**不等于稳定准确率**。
2. **原始资料开发题（`check_acceptance.py`，真实资料+向量检索）**：v3.4 全跑（状态命中 5/10）→ 修 2 条生成缺陷
   升 v3.5 → v3.5 全批重跑（`complete=True`，8/10 命中）→ 用户最终语义验收达标。
   - **已符合要求**：Q02/Q03/Q05/Q07/Q08/Q09/Q10（Q07 grounded、Q09 partial 由 v3.5 复核确认）。
   - **Q01 已换题**（原依赖 S01，S01 无开放许可不能导入）→「提示注入与越狱有什么区别？」，全批中 **grounded**。
   - **Q04/Q06 检索未命中欠项**：已转 **Issue 13/14/11 结构适配**处理，**13 使 Q04 定义段排名 2→1**；
     Q06 跨资料比较仍为第 4，**如实记录未改善**，不改检索器、不改预期蒙对。
   - 报告与复核：`issue05-acceptance-live-v34-full-*` / `issue05-acceptance-review-v34-*` /
     `issue05-acceptance-live-v35-targeted-*` / `issue03-acceptance-review-v35-full-20260910.md`。

**后续**：主线已进入 **Issue 07**（冻结评测样本与基线报告）。以下为历史记录。

## 历史（v3.2 及以前，均为过时状态，勿据此执行下一步）

v3.2 三题已跑完：analogy、missing_measurement 本次符合要求，number 仍错误 partial。不同版本累计观察不能当作同版本全量通过。

v3.1 十题结果已收齐，七题本次符合要求，number/analogy 语义未通过，missing_measurement 程序误拒绝已离线修复。

输出契约补充：insufficient 仍要求无结论及明确缺失，但允许已验证的资料范围引用，并返回 citation_scope=missing_context；引用可定位仍不自动证明缺失说明的语义。此前“insufficient 必须 citations 为空”不再是当前约束。以下为历史。

v3.1 四题已完整运行，principle/partial/conditions 本次符合要求，number 仍误判 partial。见 `docs/evidence/issue05-v31-review-20260910.md`。以下为历史记录。

最新：v3 实测仅 principle 执行即失败，后三题未运行。已修复完全重复的内嵌引用形状问题，24 本地测试通过；原则题过度声明缺失仍未通过语义复核。当前 evidence-v3.1，待重新执行下方定向四题命令，详见 `docs/evidence/issue05-v3-review-20260910.md`。以下版本记录为历史。

2026-09-10 更新：已用保存的真实失败先复现、写失败回归再修复。当前为 evidence-v3，22 个本地测试通过；真实 v3 输出尚未验证。详细说明见 `docs/evidence/issue05-offline-diagnosis-20260910.md`。下面 evidence-v2 描述保留为历史实现背景。

新版输出 coverage 按输入问题片段关联结论索引或说明缺失，程序汇总状态。不能将合法关联视为真实语义覆盖；人工仍需检查数量子问、条件、否定及两方引用。

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

- **十题整体重跑**：新 Q01 与 v3.5 修复尚未在全批下验证（定向三题已过，不等同全批）。
- **Q04/Q06 检索未命中**：不改固定检索器，记入结构适配待办（未来 13/14/11 的切分粒度调整）。
- **用户最终语义验收**：助手复核不等同用户验收。
- 受控场景不能证明对任意提示注入都安全；后续检索工具循环仍由 Issue 10 验证。

完成上述检查前，Issue 05 保持进行中。下一次反馈可以只提供生成报告路径，由助手从本机读取，不必手工粘贴全部 JSON。

## 原始资料开发题命令（真实资料 + 检索）

```powershell
# 免费准备：只检索、不联网不付费
.\.venv\Scripts\python.exe scripts\check_acceptance.py
# 付费执行：密钥来自环境变量或交互隐藏输入
.\.venv\Scripts\python.exe scripts\check_acceptance.py --live
# 定向重跑（省钱）
.\.venv\Scripts\python.exe scripts\check_acceptance.py --live --case Q01 --case Q07 --case Q09
```

用例 `examples/acceptance-cases.json`；运行器付费批次遇单题错误**记录后继续**，仅账本阻塞时停止。
