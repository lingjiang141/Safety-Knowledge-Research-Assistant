# S01 许可核查与 Q01 替换（2026-09-10）

## 背景

用户裁定选项 A（导入 S01 使 Q01 可答）。S01 指 `docs/starter-reading.md` 所列
Anthropic《Building effective agents》。导入前依项目规则「实际导入前保存来源、标题、取得日期、
许可信息」核查许可，结果如下。

## 许可核查（不通过）

- 页面：`https://www.anthropic.com/engineering/building-effective-agents`
- 页脚仅有版权声明：**© 2026 Anthropic PBC**。
- **无任何 Creative Commons 或其他开放许可**，亦无 "All rights reserved" 字样。
- Anthropic 消费者服务条款（`https://www.anthropic.com/legal/consumer-terms`）：
  - 第 10 条：保留全部知识产权，**除条款明确授予外不授予任何权利**；
  - 第 3 条：**禁止** "crawl, scrape, or otherwise harvest data or information from our Services"；
  - 第 12 条：未经书面许可不得使用其名称/商标暗示背书。
- 结论：**不能将 S01 全文导入语料库**。这与 OWASP 三份资料（页脚明确 CC BY-SA 4.0）形成对比。
  导入会进入检索与 git，构成未经许可的再分发，且与用户条款的抓取禁令冲突。

**因此选项 A「导入 S01 全文」不可行。** 与用户沟通后，用户改选「Q01 改用本项目已有资料可答的题」。

## Q01 替换

- 原题：`工作流和 Agent 有什么区别？用容易理解的话说明。`（依赖 S01）
- 新题：`提示注入与越狱有什么区别？`
- 依据：OWASP LLM01 开篇定义段（第 1–14 行）**完整**给出二者关系——
  "prompt injection and jailbreaking are related concepts ... Jailbreaking is a form of prompt injection
  where the attacker provides inputs that cause the model to disregard its safety protocols entirely."
  （越狱是提示注入的**一种形式**，注入是更大范畴。）
- 检索确认：新题首命中即 LLM01 第 1–14 行；预期 `grounded` 可达。
- 附带收益：新题只含一个问句，不再出现原题末尾风格后缀被切分引起的 partial 伪影。

已更新 `examples/acceptance-cases.json`（Q01 题面、expected_sources=S02、human_review、note）与
`docs/acceptance-draft.md`（Q01 行 + 修订说明）。

## 边界

- 本轮**未新增付费调用**；Q01 新题只做了免费准备与检索验证，**尚未真实运行**。
- S01 仍保留为**外链阅读参考**（starter-reading.md），不作为原文证据参与评测。
- 不可用助手导读写入语料冒充原文——该规则依旧成立。
