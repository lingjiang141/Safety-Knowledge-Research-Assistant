# 原始资料开发验收：运行器与准备报告（2026-09-10）

## 目标

按用户选择“原始资料开发题（真实资料+检索）”，把 `docs/acceptance-draft.md` 的十个开发验收题
接入**真实知识库 + 本地向量检索**运行，检验回答管线在检索参与下的端到端行为。

## 与受控边界测试的区别

| | 受控边界测试 `check_boundaries.py` | 原始资料验收 `check_acceptance.py` |
| --- | --- | --- |
| 证据 | oracle 受控片段（隔离生成） | 真实 OWASP 资料 + 向量检索 |
| 检索 | 不参与（直接给证据） | 参与（`VectorSearch.search`） |
| 用途 | 生成契约与边界 | 端到端开发验收 |

两者都**不是**保留测试集，也**不代表**正式评测或稳定准确率。程序只校验结构、原文匹配与显式
问题覆盖记录，**不判定语义**；`expected_status` 与 `human_review` 是人工复核提示。

## 新增文件

- `examples/acceptance-cases.json`：十题用例（题面取自 `docs/acceptance-draft.md`），含
  `excluded_doc_ids` 与逐题 `human_review` 提示。
- `scripts/check_acceptance.py`：运行器。默认仅准备（不联网、不付费）；`--live` 才付费，
  密钥从环境变量或交互隐藏输入取得，与边界运行器一致。

## 关键设计：剔除合成夹具

知识库里除三份真实 OWASP 资料外，还有一份**合成 CC0 夹具 “Security demo”**
（`85772b00…`）。准备阶段实测：Q07“为什么既要区分资料和指令，又要限制工具权限？”的向量检索
原本把该夹具的 `Tool permissions` 片段排进第三名（score 0.550）——即**合成夹具会污染真实资料题**。

运行器因此在 `acceptance-cases.json` 中列出 `excluded_doc_ids`，`make_search` 先向向量检索多取
候选、再剔除被排除文档、最后截到 limit，并把过滤后的结果持久化为 run 记录（重放与模型所见一致）。
复测：十题不再命中该夹具。

## 准备报告与观测（未付费）

准备报告 `docs/evidence/issue05-acceptance-prepared-20260910.json`
（源 `.data/acceptance-report-20260910T070823737743Z.json`）。要点：

- 十题在真实资料下均能返回 3 条向量候选；被剔除夹具不出现在任何一题。
- 免费 preflight（Q05）通过：请求 12870 字节 < 20000 上限，最大预留 3.152928 元，
  `budget_ready=true`，`network_called=false`，`key_configured=false`。
- 账本未变：累计 0.166719 元、可用 9.833281 元、预留 0、blocked=false。

## 已知欠项：S01 未导入

`docs/acceptance-draft.md` 指明 S01（What are agents?）若未导入，Q01 暂不作为可回答题。
当前知识库**没有 S01**，Q01 的检索落到 LLM06（Excessive Agency，其中确提到 agent 动态选择
extension）与其他资料，**不能**据此断言 Q01 语义达标。Q01 需在 S01 导入后另行复核，或作为
“资料缺失”题单独处理。

## 下一步

准备已就绪。真实运行需用户在本机交互终端执行（付费、需本地密钥）：

```bash
.\.venv\Scripts\python.exe scripts\check_acceptance.py --live
```

运行后由助手复核正文语义（逐题对照 `human_review`），不将 `status_matches` 等同于语义通过。
Issue 05 保持进行中，不进入 06。
