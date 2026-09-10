# 安全知识研究助手

开发每个 Issue 前阅读 [技能触发规则](docs/development-workflow.md)。用户已授权在 Issue 06/13/14/11/10 使用 TDD，在 04–06 完成后、13 前直接进行架构检查。

当前交付 Issue 01–02：Markdown 原文检索、引用校验、DeepSeek 适配器及持久化预算保护。已验证模拟回答路径，未验证真实模型效果；仍为关键词检索，实际 API 支出为 0。

## 运行

需要 Python 3.11+。运行时仅使用标准库，不需要安装第三方依赖。在仓库根目录执行：

```powershell
python -m skra import examples/security-demo.md --title "Security demo" --source "urn:skra:security-demo" --license "CC0-1.0"
python -m skra docs
python -m skra search "提示注入"
python -m skra search "tool permissions"
python -m skra read <搜索结果中的完整片段ID>
python -m skra run 1
python -m unittest discover -s tests -v
```

示例为本项目自建英文测试资料，非权威资料或真实实验。导入真实 Markdown 时自行核对来源与许可，使用 UTF-8 编码，并通过 `--acquired YYYY-MM-DD` 指定取得日期。

默认数据库为 `.data/knowledge.sqlite3`（Git 忽略）。可在子命令前指定 `--db 路径` 创建独立知识库。数据库保存原文快照，原文件改变不会静默改变已导入证据。

返回 JSON 包含标题、来源、许可、资料版本、章节、从 1 开始的起止行号和英文原文；分数仅为匹配词项数，不是置信度。只内置提示注入、工具权限、最小权限、间接注入四个术语映射，无法提供通用跨语言检索。无结果不能证明资料没有答案。

同来源同内容重复导入保持原标识；相同来源不同内容暂时拒绝，更新删除由 Issue 06 实现。切分器按标题及最多 20 行切分，是后续可替换的基础实现。

可选安装命令：`python -m pip install -e .`，之后使用 `skra` 命令；构建需要 setuptools，离线环境可直接使用上述模块入口。

## 开发路线

见 [PRD](PRD.md) 和 [ROADMAP](ROADMAP.md)。下一步 Issue 03 核实计费配置、真实调用及人工核对。不要提交密钥、数据库或个人配置。

## 测试回答路径（免费）

先按上述步骤导入样例，再执行：

```powershell
python -m skra ask "提示注入" --demo
python -m skra budget
```

`--demo` 不联网，输出明确标记 `mode: demo`，中文结论和释义是占位内容，不能当作模型翻译或真实知识回答。它用于查看引用、资料版本和预算如何呈现。`answer_run_id` 可传给 `run` 查看记录。

## 真实调用配置（Issue 03 验证）

将示例计费配置复制到 `.data` 内，在核对官方可用模型、人民币每百万 token 价格与日期后填写。输入单价使用缓存未命中价，按该价格保守记账（可能高于实际平台账单）。默认配置禁止调用；不要仅为通过检查而把 verified 改为 true。

输入预留已改为官方上下文窗口上限，采用 1,048,576 token 的保守上界，不再使用字符估算。价格核对日期最多七天有效。该预算是本地防误操作控制，无法限制其他程序或用户直接调用账户的支出。

密钥只从本机 `DEEPSEEK_API_KEY` 环境变量读取，不放入计费配置。调用入口为 `python -m skra ask "问题" --config .data/model-config.json`。当前未验证真实 API 的 JSON 输出契约和具体模型适配，不应提前宣称可正常付费生成。

全项目账本固定在安装源码目录的 `.data/budget.sqlite3`，更换 `--db` 不重置额度；不要删除或移动账本以刷新预算。总额度 10 元，单次输出最多 800 token、输入最多 20000 UTF-8 字节、问题最多 2000 字符，网络等待超时为 30 秒。不自动重试（零次，低于一次上限）。

请求失败或用量缺失时费用未知，会保留预留并暂停后续请求；目前没有自动核销功能，需核对平台账单后在后续任务提供明确的核销流程。已取得用量但引用校验失败仍记账，不展示无效答案。结构和原文匹配测试不代表语义正确，真实引用支持与中文释义需人工复核。

GitHub 仓库：https://github.com/lingjiang141/Safety-Knowledge-Research-Assistant


真实调用验收步骤见 [Issue 03 本机指南](docs/live-m0.md)，支持 --preflight 免费预检和 --prompt-key 隐藏输入密钥。


PRD v0.2 新增文档结构适配主线，见 ROADMAP 的 13–15 及提前的 11。当前代码仍为原切分基线，尚未实现新策略。
