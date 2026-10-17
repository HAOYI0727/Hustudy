# M2切换GLM-5.3-Flash（2026-10-17）

任务M2-MODEL-53-FLASH；Codex辅助gcx，用户明确要求切换模型。实施目录为原Hustudy-main，不改已下载Hustudy-gcx或Hustudy-main2，也不改原83项上传副本。合并后的新改动，未上传/未发布；交接H-20261017-GCX-001。

## 官方接口核对与变化

[官方模型文档](https://docs.bigmodel.cn/cn/guide/models/vlm/glm-5.3-flash)核对日期2026-10-17：model code为glm-5.3-flash；仅支持thinking.type=enabled，支持JSON结构化输出。使用原智谱标准API端点，reasoning_effort=low（官方模型卡支持low/high/max），不记录/显示reasoning_content。它不是沿用旧免费模型权益，价格/账户权限以控制台为准。没有替用户发起真实或计费调用。

- Settings允许glm-4.7-flash和glm-5.3-flash，默认后者；这是两个智谱模型的配置兼容，不是多平台/网页选择器已经完成。
- .env.example及configure_zhipu.py默认新模型；脚本支持--model选择旧模型。本机.env仅替换HUSTUDY_LLM_MODEL，其他配置字节保留，不展示密钥，不需重新输入密钥。
- Provider按模型选择思考参数，保持JSON、输入/输出预算、超时、权限与引用校验；旧模型保持thinking.disabled。现有max_tokens也包含新模型可能使用的思考预算，遇截断明确失败，不自动增加预算或重试。
- provider状态返回新模型文档地址和核对日期；旧模型预览确认前或旧任务派发前发现配置变化即拒绝，新请求须重新预览确认。旧结果保留原模型身份，不改写历史。

## 验证

- 后端：pytest test_model_switch、test_remote_ai、test_study_reports、test_question_drafts、test_study_report_demo、test_ai_error_details、test_account_backups，104 passed in 22.81s。新旧模型参数均覆盖，含配置脚本保留其他字段、reasoning不外泄、旧预览/排队任务切换后不派发。
- Chrome：study-reports.spec.ts和question-drafts.spec.ts，390/1440px共4 passed（24.6s），真实临时API和模拟模型响应。
- 本轮相关后端/脚本Ruff通过。未重跑全量后端，原Windows3项失败仍未处理；未声称新模型真实生成质量或额度可用。
- 项目外diagnose_zhipu_minimal.py补--model选项，默认glm-5.3-flash；只检查--help和Ruff，未调用模型。该脚本是本机诊断工具，不是项目运行依赖。

## 重启（原项目）

在后端、worker各自终端Ctrl+C，等待回到PS提示符，再执行。新终端也可使用同样完整命令。

后端：
```powershell
Set-Location 'E:\aa大学\大三上\软件工程\Hustudy\Hustudy-main'
$env:PYTHONUTF8 = "1"
$env:HUSTUDY_LLM_MODEL = "glm-5.3-flash"
python -m uvicorn app.main:app --app-dir backend --reload
```
worker：
```powershell
Set-Location 'E:\aa大学\大三上\软件工程\Hustudy\Hustudy-main'
$env:PYTHONUTF8 = "1"
$env:PYTHONPATH = "backend"
$env:HUSTUDY_LLM_MODEL = "glm-5.3-flash"
python -m app.workers.materials
```
使用Anaconda完整路径时将最后一行python替换为`& 'E:\Anaconda\python.exe'`。前端无需重启，Ctrl+F5刷新；若前端已关闭，则npm run dev --prefix frontend。看到模型名glm-5.3-flash后，从新预览确认发起一次测试，旧失败历史不会重发。

原始API Key无需重新创建；有效密钥仍受新模型访问权限和费用限制。此次没有改数据库或业务数据。
