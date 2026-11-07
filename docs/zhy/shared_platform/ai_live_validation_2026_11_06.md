# AI真实可用性验证与改进（2026-11-06）

## 实测结论

本轮由用户明确授权真实检查及生成，仅使用本机test账户已经加密保存的智谱配置，活动模型为`glm-5.3-flash`；未修改密钥/模型或回退机器共享Key，没有展示凭据。连接、资料问答和完整分批学习报告均实际成功。当前可用不等于供应商任何时间都不会超时/限流或输出坏JSON。

| 项目 | 实际案例与范围 | 结果 |
| --- | --- | --- |
| 连接 | 固定极短JSON测试，无课程内容 | connected，1.27秒 |
| 资料问答 | 《第十章》v1第14–18页，比较系统/介质故障 | 8.07秒，grounded，4条逐字引用 |
| 学习报告 | 同一课件全部91片段/16082字，分3批 | 完成3/3批，grounded，29个知识点、4例题、15自测、78条去重来源引用，引用到第91页 |
| 历史与回源 | 查看已有结果、来源回到原版本/片段 | 两类结果均可从历史读取；Chrome/WebKit各两类回源成功 |
| 原生Safari | 总览进入真实问答、点击15页来源；打开完整报告 | 实际呈现答案及4引用，回到原文15页；完整报告显示有来源及第1/2/3部分 |

问答结果ID：`8e2e0391-9312-4422-a99c-ca341ab71f40`。完整报告ID：`35108ade-0dcb-42b3-80ef-230db7540106`，请求ID：`890eb0fb-d9ad-42de-b560-ad5210eb205f`。在test账户「数据库系统设计 → AI学习 → 资料问答/学习报告 → 已保存结果」查看。报告目标以“按知识点梳理第十章数据库恢复技术”开头。结果保持UNREVIEWED，不自动认定教师核实、个人掌握或保存为笔记。

## 发现的原因与修复

1. 首轮连接和问答正常，整章报告第一批64.53秒后因INVALID_JSON被拒绝。失败原文按既有规则未保存，不能事后断言具体是哪一种语法错误；不是API Key失效。报告提示词升级v11，明确JSON换行/引号/反斜杠转义、禁止围栏/前后文及精炼完整表达。纠正提示词对并未发送的sources.locator字段的依赖，按已排序来源阅读，页码继续由服务端凭引用恢复。增加只含固定类别及行列号的安全诊断，失败正文、推理及密钥均不回显或记录。严格JSON/schema/逐字引用校验不放宽。
2. v11第一批成功约85秒，但原实现仍派发第二批，120秒共享窗口到期时中止，保留首批30引用。新增仅分批报告的保守派发检查：记录本请求已成功调用的最大时长（0–120秒数值），同窗口已有调用且剩余不足该时长+2秒时停止下一批派发，返回REPORT_WINDOW_TOO_SHORT。该估计不保证下一批耗时，只用于避免明显余量不足的请求；不会增加窗口或减少资料范围，QA/M4/其他业务不启用此检查。
3. 真实第二窗口成功完成第二批约94秒，余约25秒时新逻辑阻止第三批派发；total_calls仍为3，未增加一次即将中断的调用。第三窗口明确续跑，跳过已完成部分，约88.74秒完成最后一批。最终v11任务4次真实调用（3次成功批次+改进前1次窗口中止），3个确认窗口，授权结构修复上限1但实际0次。单批6000token和单窗口120秒保持，不将多窗口描述为一次120秒内完成。
4. 首页共享provider_error从“模型不可用”改为中性“AI处理异常”；结果页继续展示具体格式/超时/来源等原因，新增“本窗口剩余时间不足”与未派发说明。旧v10历史仍可读取，新提示词下不把旧报告当精确复用结果。

## 逐项核验

- 问答4处引用、报告270处嵌套引用呈现（去重后78条）：均核对当前版本/片段、active状态、完整quote、SHA-256、真实页码及起止偏移，全部一致；没有用引用通过代替内容质量审阅。
- 抽查系统故障、UNDO/REDO顺序和检查点队列解释，对照实际课件；报告各批独立依据原文生成，没有跨批AI融合。所选文字覆盖完整，不代表图片/动画、每个视觉知识点均已理解。
- 每个知识点/例题/自测均有有效引用；每批5道自测。第一/第三部分分别由既有保护移除1/2条无效或重复概念关系，界面保留提示，不猜测替代边；不能宣称原始生成零瑕疵。
- 两类结果均在本人课程历史中找到；Chrome和WebKit真实页面共4项验证通过，报告三个部分可展开、390px无横向溢出、来源回原UUID/版本/片段、无页面异常。查看与回源期间未产生任何AI确认/续跑/新建笔记POST。
- 原生Safari通过computer use实际打开已完成问答/报告并回源。用户切换窗口会触发CUA“user changed”保护，没有绕过；没有以自动化测试代签教师/成员或全设备质量验收。

## 自动测试与复现

最终相关后端**199 passed**，1项既有Starlette/AnyIO弃用警告；前端5文件**22 passed**，TypeScript与Ruff、git diff --check通过。后端自动验证全部临时库/模拟服务，真实调用仅上述明确授权步骤；无依赖或迁移，无Git提交推送，没有修改PPT、课件原件/切片/已有笔记，也未自动保存生成笔记。

```bash
.venv/bin/python -m pytest backend/tests/m2/test_json_failure_diagnostics.py backend/tests/m2/test_ppt_summary_prompt.py backend/tests/m2/test_remote_ai.py backend/tests/m2/test_study_reports.py backend/tests/m2/test_m2_execution.py backend/tests/m2/test_report_structure_feedback.py backend/tests/m2/test_report_selfcheck_completion.py backend/tests/m2/test_related_reports.py backend/tests/m2/test_related_answers.py backend/tests/m2/test_model_switch.py backend/tests/shared/test_model_connections.py backend/tests/shared/test_api_connection.py backend/tests/m2/test_report_capacity.py backend/tests/m2/test_real_materials.py -q
cd frontend
npm run check
npm run test -- tests/unit/ai-result-status.test.ts tests/unit/ai-execution.test.ts tests/unit/reading-summary.test.ts tests/unit/report-review.test.ts tests/unit/ai-topics-reuse.test.ts
```

工程外证据：`/tmp/hustudy-ai-20261106/`，含连接结果、首轮失败及复测/续跑JSON、`verification.json`、`ui-results.json`、各组测试日志及Safari/双引擎截图；临时目录不是长期交付或Git内容，失败供应商原始正文/思考和凭据不在证据中。历史失败未删除，正式人工验收待本人。

## 手工体验

1. test账户进入API接入，检查配置后明确点击测试；成功只说明当前连接可用。
2. 在AI学习的资料问答选择《第十章》并限定14–18页，预览问题和来源，确认发送。核对回答及引用，点击来源应回到原第15等实际页。
3. 学习报告选择该课件完整版本，预览应有91/91片段、16082字、3批。明确确认后生成；大型报告可能需要多个确认窗口，已完成部分会先显示。
4. 若出现“本窗口剩余时间不足”或预算到期，核对已完成批数，勾选同意继续未完成批次，再确认继续；成功批次不重发，结构修复总额度不重置。只有需要时才选择允许格式修复，可能增加计费调用；限流/超时/无效引用不会因此自动重试。
5. 完成应显示有来源，三个部分均可展开。核对知识点、例子、自测与引用，若要笔记先整理为草稿、本人审阅后再保存；本轮没有代替用户保存笔记或标掌握。

当前官方模型接口说明：[GLM-5.3-Flash/FlashX](https://docs.bigmodel.cn/cn/guide/models/vlm/glm-5.3-flash)。模型配置保持thinking.enabled与low推理力度，本轮没有更换收费模型或切换第三方端点。
