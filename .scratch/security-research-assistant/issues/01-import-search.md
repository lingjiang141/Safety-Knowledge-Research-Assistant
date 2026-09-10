# 01 — 导入一份 Markdown 并查询原文

Status: ready-for-agent
State: done
Type: AFK
Milestone: M0
User stories: US1, US2, US3, US7, US18, US23
Source: [PRD](../../../PRD.md)

## What to build

从合法原文快照出发，通过 CLI 导入、搜索并查看真实片段；建立可安装运行的最小工程。暂不调用付费模型，关键词检索仅标记为连通性原型。

## Acceptance criteria

- [x] 记录来源、许可、取得日期、hash、资料版本、切分配置和稳定片段标识；不把导读作为原文。
- [x] 同一内容重复导入不重复创建有效片段；输入错误和空文档有明确反馈。
- [x] CLI 可搜索并展示标题、章节和英文原文；保存候选和耗时。
- [x] 用自建小型资料测试导入到检索的完整路径；附可复现运行步骤。

## Blocked by

None - can start immediately

## Completion evidence

2026-09-09：工作区实现，尚无 Git 提交版本。入口为 `python -m skra`，运行步骤见根目录 README。

- `python -m unittest discover -s tests -v`：2 个 CLI 端到端测试通过，包含重复导入、原文行号、中文术语命中、检索记录、空文档、无匹配及修改内容拒绝。
- 实际导入自建英文样例得到 4 个片段，搜索“提示注入”命中 Prompt injection 章节第 6–10 行。
- 真实本地检索，无模拟模型、无 API 调用，费用 0 元；没有未知付费预留。
- 当前仅术语映射与关键词原型；官方资料未导入、向量检索和回答生成未实现。安装式入口尚未验证，已验证标准库模块入口。

## Comments

任务已完成本地验收。下一项为 Issue 02，M0 整体仍未完成。
