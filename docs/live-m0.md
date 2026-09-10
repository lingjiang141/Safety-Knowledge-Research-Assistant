# Issue 03：真实调用验收

2026-09-09：模型和人民币价格已核对。**当前状态：三类端到端真实验收仍未完成（欠项保留）。**
不要向聊天发送密钥。

> 2026-09-10 更新：输出上限已由 800 提升至 **1500 token**（常量 `OUTPUT_TOKEN_LIMIT`，见 `skra/answer.py`），
> 因为 800 在多引用时会截断 JSON。下文出现的「800 输出 token / 3.152928 元预留」为历史记录，
> **当前单次最大预留为 3.159228 元**（1,048,576 输入 + 1500 输出，按保守高峰单价）。

## 模型与预算

选择 deepseek-v4-flash，依据 [DeepSeek 官方价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)：高峰缓存未命中输入为 3 元/百万 token，输出为 9 元/百万 token。非思考模式、JSON 输出受支持；使用已文档化的 thinking disabled 参数。计费配置七天后过期，需要重新核实。

官方说明上下文长度 1M。预留取更保守的 1,048,576 输入 token，加 **1500** 输出 token，因此每次最多暂占 **3.159228 元**；这是防止超预算的预留，不是实际预计费用。成功后按实际用量及保守高峰单价结算并释放剩余预留。用量异常或未知保持阻断。该方案不依赖未经证明的字符/token 估算。

## 本机步骤

在项目根目录的 PowerShell 执行；使用现有自建示例，避免把未导入的官方资料当作已知证据。

```powershell
python -m skra budget
python -m skra ask "提示注入是什么？仅解释这份示例中的情况。" --config examples/deepseek-flash.2026-09-09.json --preflight
```

预检不联网、不预留费用，输出最大预留、余额和是否可调用。key_configured 为 false 时可以使用下面的隐藏输入方式：

```powershell
python -m skra ask "提示注入是什么？仅解释这份示例中的情况。" --config examples/deepseek-flash.2026-09-09.json --prompt-key
```

在提示位置粘贴密钥并回车，输入不显示、不写文件；每次运行需重新输入。若在同一终端已安全配置 DEEPSEEK_API_KEY，则省略 --prompt-key。其他终端设置的临时变量不会自动传给当前 Codex 进程。

第一题成功后再逐题执行，出错先检查 budget，不循环重试：

```powershell
python -m skra ask "提示注入防护在本项目实测成功率是多少？" --config examples/deepseek-flash.2026-09-09.json --prompt-key
python -m skra ask "工具权限是什么？这种限制在我的电脑上降低多少百分比风险？" --config examples/deepseek-flash.2026-09-09.json --prompt-key
python -m skra budget
```

这三题均含可命中关键词，第二题用于检查“检索到主题相关内容但缺少所问事实”，不是只测试零命中分支。

## 逐条复核

| 问题 | 预期 | 需人工检查 |
| --- | --- | --- |
| 概念 | grounded | 只说明示例支持的内容；引文真实、中文释义准确 |
| 实测比例 | insufficient | 不编造比例、不借用外部成绩 |
| 概念与个人效果 | partial | 有据部分正常解释；明确没有个人环境效果数据 |

记录每次 answer_run_id、call_id、实际返回状态和预算；使用 run 命令读取保存记录。不要上传密钥、完整数据库或账户截图。可直接反馈不含密钥的错误或回答文本。

1500 输出 token 已比原 800 宽松，但在极多引用情况下仍可能截断；此时界面应报告失败且保留费用，不能将不完整内容当作成功。是否继续调整输出额度应根据真实失败记录决定。

## 当前验收状态

已完成免费预检与本地回归测试（**当前 31 tests 通过**）。真实调用只在 Issue 05 的验收脚本中发生过；
Issue 03 自身三类端到端验收、平台费用核对**仍未完成**，保持未完成，不以其他 Issue 的调用代替。

更新：用户首次真实调用已返回用量，但回答校验失败。已修复校验错误信息丢失的问题；旧记录没有模型正文，无法重放。新失败记录会保存最终正文及具体诊断，可用 `python -m skra replay <回答运行记录ID>` 离线重新校验，不产生费用。失败正文只供诊断，不是通过验收的答案；不要将完整数据库公开上传。
