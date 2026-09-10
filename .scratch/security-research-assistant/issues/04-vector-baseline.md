# 04 — 中文问题检索多份英文资料并建立向量基线

Status: done
State: done
Type: AFK
Milestone: M1
User stories: US1, US3, US9, US14, US18, US21
Source: [PRD](../../../PRD.md)

## What to build

导入已筛选且许可核对过的少量资料，选定单一多语言编码模型及向量索引，从中文问题获得原文候选和带引用答案。

## Acceptance criteria

- [x] 核查本机资源与依赖；优先本地编码，锁定版本；不能假定 DeepSeek 提供 embeddings。
- [x] 向量检索与 M0 原型可明确区分；新增资料后查询可见，CLI 显示有效版本。
- [x] 保存固定语料、问题、检索参数、候选分数、证据及模型信息。
- [x] 用中英跨语言样例验证；付费生成通过预算守卫，未运行的真实部分如实标记。

## Blocked by

- [03 — 验证 DeepSeek 真实调用和三类回答](03-live-m0.md)

## Completion evidence

完成时填写：代码版本、演示命令、测试结果、真实与模拟验证的区分、费用与未知预留、未解决问题。不得仅凭复选框关闭任务。

## Comments

尚未开始实现。遵守 PRD 的资料边界及 10 元总预算；AFK 表示常规实现无需逐项确认，不表示允许跳过密钥、预算或人工语义复核。


## 2026-09-09 实际验证

用户明确要求继续 Issue 04；Issue 03 三类语义验收保留为欠项，不据此关闭。

已安装依赖并锁定 requirements-vector.lock.txt，CPU 本地模型 revision e8f8c211226b894fcb81acc59f3b34ba3efd5f42；纯向量索引/搜索/回答入口已接入。14 个本地测试通过，pip check 无依赖冲突。

真实模型对两份 OWASP 原文短节选、两道中文开发题运行，均在 top5 命中对应正文；总片段少，结果不能代表正式质量。两个 top1 都是说明段，记录为当前基线的排序失败。报告见 docs/vector-baseline.json。

ask --retrieval vector --demo 完成整条引用展示路径，未调用付费生成；真实向量证据回答与释义尚未复核，因此最后一项验收保留未完成。依赖运行时出现 tokenizer regex 警告，尚未确认其对本模型的影响，不能将其隐藏或将当前分数视作可靠模型评测。


分词警告复核：检查 transformers 4.57.6 源码确认对重新保存的非 Mistral 配置存在误判。本模型 model_type=bert，已显式禁用不适用的 Mistral regex 修补；中英文样例 token ID 与保存的 tokenizer.json 一致。实际基线已重新运行，结果不变。


## 真实生成验收补充

用户提供并核对 vector-baseline 数据库 answer_run_id=8、retrieval_run_id=7、call_id=3 的真实结果。中文结论有据，引用 Minimize extensions 第 9–11 行，英文原文与中文释义一致。真实向量检索至回答路径通过，Issue 04 完成。

质量欠项：仅问限制原则却返回 partial，并将未问的具体数值作为缺失，状态偏保守；移入 Issue 05 的回答边界验收，不代表完整语义质量通过。累计保守记账 0.011334 元，无预留；Issue 03 的三类验收仍单独保留。
