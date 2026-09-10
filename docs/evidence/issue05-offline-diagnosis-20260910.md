# Issue 05 离线诊断与回归

2026-09-10。代码基于 cfc4563 的工作区修改，未提交或推送。使用 diagnose；未联网、未增加真实费用。原始证据未修改。

## 证据与复现

- `issue05-live-20260909.json`：partial 问题为“应如何限制工具？具体最多几项？”，返回原则结论、grounded、空 missing。
- `issue05-conditions-failure.json` 及 `.data/boundaries.sqlite3` run 14：JSON 完整，引用逐字匹配，正文保留环境 A/B 和否定，但 status=partial、missing 为空。
- 修复前两次重放：partial 均被旧 validate 放行为 grounded；conditions 均报“部分回答必须说明缺失”。CLI replay 14 同样复现。
- 单变量诊断：仅将 conditions 的 status 改为 grounded，旧校验即通过，排除 JSON/引用失败。此探针不是产品中的自动修复，也未改写保存的响应。

## 原因

1. 旧校验接口只有答案和证据，没有问题，因此无法发现第二问未交代。提示词已经提醒数字缺失，单纯重复提示不构成可靠修复。
2. status 由模型独立填写，和问题覆盖、missing 没有共同的结构化来源；conditions 是状态误判，不能为消除错误凭空补写 missing。
3. 原有十题测试只喂人工写好的正确答案，无法捕捉真实错误模式。

## 修改

- evidence-v3 将原问题按问号、分号、换行分成带顺序 ID 的片段，原始完整问题仍一并传入。每项 coverage 必须关联有效结论索引或明确说明缺失；拒绝遗漏、重复、未知 ID、无效索引、空项及未关联结论。
- 程序从 coverage 汇总 grounded/partial/insufficient 和 missing，不依赖模型单独填写的顶层 status。引用 ID、逐字原文、结论引用、工具禁用、费用结算仍按原路径校验。
- 没有覆盖记录的旧正文在新版调用中被拒绝，不自动把所有 partial 升为 grounded。历史 v2 replay 继续重现当时契约错误；v3 replay 使用保存的问题片段，不能绕过覆盖检查。
- 比较结论本身引用双方、missing 不夹带无引用事实等规则补入提示词；这些仍待真实语义检查。

## 回归结果

先新增 `tests/test_question_coverage.py` 的四项行为测试并运行：旧实现失败（包括子测试共 9 failures、1 error），随后修改实现。最终新增至六项，使用临时知识库、临时账本和注入的模型传输函数，经过公开 answer 接口；未访问 API。

`python -m unittest discover -s tests -v`：22 tests，全部通过。包含十个受控场景子测试；覆盖原始 partial 拒绝、第二问漏项拒绝、补充显式缺失后 partial、conditions 添加人工覆盖映射后 grounded、旧 conditions 不盲目升级、数字有证据时 grounded、单个片段确有缺失时 partial、非法覆盖及 CLI 离线重放。

测试中新增的 coverage 是人工契约输入，**不是模型生成，也不是对原报告的修订或真实成功结果**。conditions 原始正文仍缺覆盖记录；历史 replay 14 仍应报原错误。

## 限制与下一步

分句不等于语义拆问：同一句中的多个要求仍需要模型逐项交代。模型也可能把原则结论错误关联到数量问题；索引合法不能证明答到了数字。此改动修复显式覆盖和状态一致性的程序缺口，不证明模型语义漏答已消失。没有关键词硬编码的数量检测，也没有加入额外付费判题器。

当前进程 DEEPSEEK_API_KEY 未配置，未运行新版真实调用。先在本机运行：

```powershell
python scripts/check_boundaries.py --live --case principle --case number --case partial --case conditions
```

脚本可隐藏输入密钥，报告仍自动保存独立时间戳；无需重新提供旧报告。按新版结果检查语义后再补 agreement/conflict 及此前未执行的 negation/injection/analogy/missing_measurement。保留原始资料开发题欠项；Issue 05 不关闭、不进入 06。

本机账本：spent=0.037608 元，available=9.962392 元，reserved=0，blocked=false。仅为保守记账，非平台账单核对。
