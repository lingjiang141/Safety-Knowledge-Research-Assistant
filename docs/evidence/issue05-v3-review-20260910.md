# evidence-v3 真实运行复核

原报告：`issue05-live-v3-20260910.json`（原本机 `.data/boundary-report-20260910T060206934201Z.json`）。失败正文与证据：`issue05-v3-principle-failure.json`，boundaries run_id=26、call_id=10。原文件未改写；本复核由助手完成，不代替用户最终验收。

## 实际结果

仅 principle 执行，因“结论必须有有效引用”停止。number、partial、conditions 未执行，不能称四题通过。

正文的结论、英文引用与中文释义一致，但出现两项错误：

1. `claims[0].citations[0]` 是完整引用对象，契约要求字符串 ID；该对象与顶层引用完全相同。
2. coverage.missing 说缺少操作细节，扩大了一般原则问题的要求。即使仅修正引用形状，仍汇总为 partial，语义复核不通过。

## 离线诊断与修改

旧校验两次重放均报相同引用错误。单独将重复引用对象改成其 ID 后，引用通过但状态为 partial，确认格式与语义是独立问题。

先新增公开 answer 路径回归，真实响应测试失败，再实现无损转换：只有内嵌对象与已经通过原文校验的顶层引用完全相等时才能取其 ID；缺少顶层引用、未知 ID、不同原文/释义或多余字段均拒绝。返回 `normalizations` 记录转换，不修改 coverage、missing 或原始记录。离线 replay 26 现能展示 partial，这是诊断结果，不是语义验收通过。

提示词改为 evidence-v3.1，增加完整 JSON 格式示意和一般建议问题的范围说明，仍要求明确数值问题答数值或说明缺失。没有硬编码本题状态，也没有删除模型的缺失说明。**提示词修改未经过真实调用验证，原则问题误判仍列为未解决。**

`python -m unittest discover -s tests -v`：24 tests 全部通过，含十场景子测试。新增测试保留真实响应的 partial，证明转换不悄悄修订语义。`python -m skra --db .data/boundaries.sqlite3 replay 26` 免费成功，引用格式被转换，语义错误仍可见。

## 费用与后续

这次用户真实调用新增保守记账 0.004605 元，累计 0.042213 元，可用 9.957787 元，预留 0，blocked=false。助手本轮无付费请求。当前进程仍无 API 密钥。

下一步运行 v3.1 定向四题，先核查 principle 是否不再扩问，再检查 number、partial、conditions：

```powershell
python scripts/check_boundaries.py --live --case principle --case number --case partial --case conditions
```

报告保存后直接从本机读取，不要求用户粘贴正文。其余六个受控场景以及原始资料开发题仍待验证。Issue 05 保持 in-progress，不进入 06。
