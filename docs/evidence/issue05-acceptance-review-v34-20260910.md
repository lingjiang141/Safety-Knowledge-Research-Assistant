# 原始资料开发验收：十题全跑复核（evidence-v3.4，2026-09-10）

## 批次

用户本机付费运行 `scripts/check_acceptance.py --live`，十题全部执行完（上次 Q01 中断已修复）。
报告 `docs/evidence/issue05-acceptance-live-v34-full-20260910.json`
（源 `.data/acceptance-report-20260910T072225121789Z.json`），prompt_version=`evidence-v3.4`。
账本：0.179976 → **0.309189** 元（本批新增 0.129213），预留 0，blocked=false。

## 逐题结论

| 编号 | 预期 | 实测 | 判定 |
| --- | --- | --- | --- |
| Q01 | grounded | **错误**（问题覆盖存在未关联的结论） | 生成/契约缺陷（已修，见下） |
| Q02 | grounded | grounded | 通过 |
| Q03 | grounded | grounded | 通过 |
| Q04 | grounded | partial | **检索未命中**（非生成缺陷） |
| Q05 | grounded | grounded | 通过 |
| Q06 | grounded | partial | **检索未命中**（非生成缺陷） |
| Q07 | grounded | **错误**（输出达到长度限制） | 输出上限过小（已修，见下） |
| Q08 | insufficient | insufficient | 通过 |
| Q09 | partial | insufficient | **预期值本身可争议**，见下 |
| Q10 | grounded | grounded | 通过 |

状态命中 5/10；另 5 题中 2 题为生成/契约缺陷、2 题为检索未命中、1 题为预期争议。

## 缺陷一：Q01 把缺失说明写进顶层 claims（call_id=35）

失败正文 `docs/evidence/issue05-acceptance-q01-unlinked-claim-failure.json`（run 137）。
模型在 `claims[1]` 写入「资料没有直接给出工作流定义……」，**citations 为空**，且没有任何
coverage 项引用索引 1，触发 `used != set(range(len(claims)))` → 拒绝。

- 契约正确：`claims` 只放有引用支撑的结论，缺失说明归 `missing`。**不放松校验**（放松会放过无引用结论）。
- 修复：提示词明确「缺失/无依据说明只能写进 missing，绝不能放进顶层 claims；每条结论 citations
  不得为空；每条顶层结论必须被至少一个问题项的 claims 索引关联」。
- 回归：`test_absence_statement_in_claims_is_rejected_as_unlinked`（保留契约，防止悄悄接受）。

## 缺陷二：Q07 输出被截断（call_id=41）

失败正文 `docs/evidence/issue05-acceptance-q07-truncation-failure.json`（run 155）。
`finish_reason=length`，正文在 JSON 字符串中途被切断，根本无法解析。原因：800 token 输出上限
不足以容纳「3 条结论 + 每条 quote 与中文释义」。**这是输出上限问题，不是模型语义错误。**

- 修复：输出上限 800 → **1500**（提取为常量 `OUTPUT_TOKEN_LIMIT`，四处同步），提示词补
  「quote 只取最短必要片段、每条结论一条最相关 quote」以控制长度。版本升 **evidence-v3.5**。
- 代价：单次最大预留因输出上界提高而增大（1048576×1/M + 1500×2/M）。生产价格配置下由
  3.152928 元升至 **3.159228 元**（preflight 实测，`budget_ready=true`，13519 字节）。
- 回归：`test_request_asks_for_the_raised_output_ceiling`；`test_answer` 预留金额断言同步更新。
- 注意：**v3.5 的真实效果尚未验证**，不得据本地回归宣称 Q07 已解决。

## 缺陷三（非生成）：Q04 / Q06 检索未命中

两题所需片段都在库里，但**排序太低**：

- Q04 需要 LLM06 第 19–38 行「Common Examples of Risks」（三个概念的并列定义），向量排序第 **7**；
  实际取到 LLM06 第 1–18 行（导语）与 LLM01 无关片段，故模型只能说「资料未分别定义」→ partial。
- Q06 需要 LLM06 第 45–82 行「Minimize extension permissions」等，排序第 **7**；
  实际取到导语与 LLM01 片段，故模型称「过度代理资料未给具体建议」→ partial。

根因：`heading-lines-v1:20` 的 20 行块过粗，定义性内容被同段大量无关行稀释；384 维 MiniLM
对这类细粒度语义区分不足。**这是检索/切分问题，不是生成缺陷。**

**本轮不改检索器**：`docs/acceptance-draft.md` 明确要求「固定检索器和证据 token 预算」，
中途换检索会混淆验收结论；结构适配属未来 13/14/11 范围。此发现记入待办，供架构检查。

## Q09 预期值可争议

问题「资料提到了最小权限。它在我的电脑上能降低多少百分比的风险？」的**实际索取是一个百分比**。
资料无该数字，模型返回 `insufficient`（claims 为空）——从「只索取具体数值的问题项」契约看是**自洽**的；
但草案预期 `partial`（先答「最小权限是什么」再说明缺百分比）。两种理解都说得通，**需用户裁定**：
是要求先答概念部分（则 hint 与提示词需再对齐），还是接受 insufficient。不擅自改预期蒙对。

## 验证与边界

- 本地 **31 tests 通过**（原 29 + 新增 2）。
- 离线复现两条失败均为修复前真实拒绝，修复后结构路径符合预期。
- **边界**：单批次、单模型、样本极小，**不等于稳定准确率或正式评测**；Q04/Q06 反映检索短板，
  未修；Q09 待用户裁定；S01 未导入使 Q01 本就不能达标。程序只校验结构，语义由人工复核。
- **原始资料题尚未全部达标**，Issue 05 不收尾。

## 下一步（需用户决定）

1. 是否按 v3.5 重跑 Q01 与 Q07（定向，省钱），确认两处修复真实生效；
2. Q04/Q06 记为检索待办（未来结构适配时处理），本轮不修；
3. 请用户裁定 Q09 的预期行为。
