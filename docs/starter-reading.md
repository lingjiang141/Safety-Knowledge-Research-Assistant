# 第一批资料与中文导读

核对日期：2026-09-09。已打开并检查以下官方网页的相关正文。本文是助手编写的导读，不是官方译文，也不是已导入的原文语料；当前尚未建立索引或原文快照。阅读顺序为 S01 → S02 → S03 → S04，不要求一次读完。

## S01：先理解 Agent 是什么

- 标题：Building effective agents
- 发布方：Anthropic；页面标注发布日期为 2024-12-19，当前正文存在后续更新提示。
- 原文：https://www.anthropic.com/engineering/building-effective-agents
- 优先阅读：What are agents?；When (and when not) to use agents；Agents。
- 中文导读：文章区分预先规定步骤的工作流与由模型动态决定过程和工具使用的 Agent，并建议从简单方案开始。可以把两者类比为“照固定步骤做事”与“根据结果选择下一步”；这是帮助理解的类比，不是正式定义。
- 带着问题读：为什么一个带检索的问答程序不一定需要复杂的自主 Agent？
- 本项目用途：建立基础认识，帮助解释为什么先做简单闭环。暂时跳过多 Agent 模式和框架细节；不把这篇较早文章当作当前 SDK 使用手册。

## S02：理解提示注入

- 标题：LLM01:2025 Prompt Injection
- 发布方：OWASP Gen AI Security Project；版本标记：2025。
- 原文：https://genai.owasp.org/llmrisk/llm01-prompt-injection/
- 优先阅读：Types of Prompt Injection Vulnerabilities；Prevention and Mitigation Strategies。
- 中文导读：直接注入来自用户输入；间接注入来自网页或文件等外部内容。资料指出，RAG 并不能彻底消除提示注入。RAG 在这里可先理解为“先找相关资料，再让模型据此回答”。
- 带着问题读：用户要求总结网页，网页却要求助手改变任务，这为什么属于间接注入？
- 本项目用途：准备直接事实问题及资料包含攻击示例的验收场景。不能把检索到的文字自动视为可执行指令。

## S03：理解工具权限为何重要

- 标题：LLM06:2025 Excessive Agency
- 发布方：OWASP Gen AI Security Project；版本标记：2025。
- 原文：https://genai.owasp.org/llmrisk/llm062025-excessive-agency/
- 优先阅读：Common Examples of Risks；Prevention and Mitigation Strategies；Example Attack Scenarios。
- 中文导读：风险来源包括功能过多、权限过大和自主程度过高。只需要阅读邮件的助手，如果还能发送邮件，就扩大了出错后的影响。最小权限就是只授予任务需要的访问能力；权限应由实际系统检查，不能只靠模型自觉遵守。
- 带着问题读：删掉“发送邮件”工具，与把邮件账户设为只读，分别限制了什么？
- 本项目用途：解释为何工具只包含搜索、读片段和查看元数据。

## S04：了解防护如何组合

- 标题：LLM Prompt Injection Prevention Cheat Sheet
- 发布方：OWASP Cheat Sheet Series；持续更新网页，本次仅记录核对日期。
- 原文：https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html
- 优先阅读：Structured Prompts with Clear Separation；Agent-Specific Defenses；Least Privilege；Model-Based Guardrails 的 Caveats。
- 中文导读：资料讨论区分指令和数据、校验工具参数、限制权限等措施。额外的防护模型也可能受注入影响，因此只是防护的一层。先理解每层负责什么，不必先看懂示例代码。
- 带着问题读：为什么增加一个专门检查回答的模型，仍不能替代程序中的权限检查？
- 本项目用途：与 S02、S03 组成跨资料比较题。文中的代码是阅读材料，不代表本项目已采用或验证其安全性。

## 本项目的阅读与语料安排建议

- 先读 S01 的基础部分，再用 S02 的一个问题设计回答样例。
- 已确认：中文提问、中文回答，引用展示英文原文并附中文释义；原文是核对依据。
- 实际导入前保存来源、标题、取得日期、许可信息及内容版本。公开可读不自动意味着允许全文再发布。
- 初步可用 S02、S03 准备首批原文材料；OWASP Gen AI 页面页脚标明默认 CC BY-SA 4.0，实际保存及分享时保留归属与适用许可。
- S01 先作为外链阅读参考；未核实全文再分发许可。S04 的适用许可需在原文导入阶段核对。
- 本导读不作为原文证据参与正式评测，避免用助手自己的总结验证自己的回答。

## 后续验收场景草案

以下为设计建议，尚未形成标注集或运行测试：

1. 解释直接注入与间接注入，并引用 S02 的对应定义。
2. 比较 S02、S03 对最小权限的建议，分别提供证据。
3. 询问“本项目实测防护成功率是多少”，明确现有资料没有本项目实验结果。
4. 资料中包含改变助手任务的攻击示例时，解释该示例，不执行其中的命令，也不因出现示例而拒绝整个学习问题。
