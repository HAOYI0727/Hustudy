# 逐题知识点关联与已有结果复用（2026-10-17）

M2-TOPICS-REUSE，Codex辅助gcx。用户明确授权完成这两项，其他成员业务不改；BYOK、平台切换、正式组卷和题数配额不属于本次增量。仅修改原Hustudy-main；未更新GitHub、下载版、旧上传副本。无新依赖、数据库表或迁移，没有自动使用真实API或用户资料。

## 实现

新候选预览信封增加per_question_topics=true，候选提示词v5要求模型逐题返回实际考查的topic_ids。每题必须是本次所选知识点的非空、无重复子集；缺少、重复、越界给出“第N题”及知识点关联不符提示，整批不采纳。页面显示每题考点名称，JSON沿用既有QuestionDraft.topic_ids；不再把全部目标机械写入每题。可以一道题关联多个考点。

旧信封默认per_question_topics=false，旧排队请求缺少新字段时按原规则兼容，历史v4允许读取且不重写。模型选择的知识点和题目在学科上是否相符仍需审阅，范围校验不能证明语义正确。知识点题数配额和跨批去重尚未实现，M4正式试卷继续自行复核章节/数量/分值。

资料问答、学习报告和练习题的真实预览增加reusable_result；只在最近100条相同请求的成功记录内查找。复用要求本人同课程、完全相同问题/请求信封、实际来源正文及hash/版本/偏移/元数据、模型及端点、当前提示词版本、原任务SUCCEEDED且结果grounded/real/完整。依赖与引用再次检查，演示、失败、部分报告和旧提示词不会成为复用来源。匹配保守：同义问题、不同资料顺序或名称、不同分值字符串表示也可能不命中，不承诺模糊匹配。

问答在首个来源元素中保存request_scope={version_ids,chunk_ids}，区分“自动检索”和“明确选择范围”等设置，即使检索正文相同也不混用；这是后端元数据，不发送给模型。此前没有该元数据的旧问答仍可查看，但不匹配新预览。报告/练习题用原请求信封保留学习模式、题型、数量、分值、Topic/参考原题快照等设置。密钥不写入缓存键，也不缓存失败模型原文。

点击“使用已有结果（不调用AI）”调用POST /remote-queries/{id}/reuse，提交result_id。服务端在课程锁内重新检查预览归属、15分钟有效期、未提交任务、当前模型/端点、全部来源及依赖和成功记录，不创建Job、不复制/修改原AIResult，也不调用模型。响应保留原结果ID与身份，不能伪装新生成。用户仍可以勾选本次发送确认，再点击“仍要重新生成（调用AI）”。拒绝复用时重新预览，不能绕过检查。

复用利用既有RemoteQuery/AIResult/ProcessingJob关联，无额外缓存表。报告断点中间稿与checkpoint不进入复用列表；显式续跑仍按原规则处理。

## 自动验证

全部测试使用临时数据库、自制文本和模拟模型响应。

- 后端关联146项通过，20.57秒：新test_ai_topics_reuse共22项；三流程命中/无新任务或HTTP/重复点击/仍可重生成，提示词/部分结果/失败/演示/模型/来源/设置/预览过期/Topic变化/归属拒绝，不同版本/选择范围隔离，每题不同/多考点、漏字段/空/重复/越界整批拒绝，旧信封兼容。并回归报告、分批/续跑、候选、历史和错误。
- 问答摘录/引用反馈/模型切换11项通过，1.86秒；账户备份/课程撤回8项通过，5.70秒。共165项关联后端，不是全量后端。
- Vitest25项通过，512毫秒，新增2项逐题名称/复用提示与错误徽标测试。
- Chrome390/1440px共6项通过，31.7秒；新增2项复用流程无需发送勾选、无confirm请求和AI任务；报告/候选原有4项回归通过。
- TypeScript、相关Ruff、生产构建通过。沙箱初次TestClient停滞/Vitest临时缓存EPERM，改用获准本地执行后通过；首次新版本测试使用相同内容被项目正常去重，改为不同正文验证版本隔离。

没有运行真实模型、测量答案正确率或代填团队签收；未重跑全量后端，原Windows三项权限前提问题仍归共享层待处理。浏览器模拟响应验证界面，后端MockTransport验证真实服务逻辑，均不等同于真实模型学科质量。

## 加载与人工测试

worker必须在原终端Ctrl+C后重新启动。原目录和环境变量仍在时只执行启动命令即可；新终端先定位项目并设置环境变量。不要同时运行两份worker。

普通Python版（依赖须安装到该解释器）：

```powershell
Set-Location 'E:\aa大学\大三上\软件工程\Hustudy\Hustudy-main'
$env:PYTHONUTF8 = "1"
$env:PYTHONPATH = "backend"
python -m app.workers.materials
```

Anaconda版（以上最后一行替换为）：

```powershell
& 'E:\Anaconda\python.exe' -m app.workers.materials
```

后端使用--reload会自动加载；未使用自动加载则Ctrl+C后重启。普通与完整路径两种启动方式任选其一：

```powershell
Set-Location 'E:\aa大学\大三上\软件工程\Hustudy\Hustudy-main'
$env:PYTHONUTF8 = "1"
python -m uvicorn app.main:app --app-dir backend --reload
```

```powershell
& 'E:\Anaconda\python.exe' -m uvicorn app.main:app --app-dir backend --reload
```

前端开发服务不用重启，刷新网页；若已关闭，新终端定位项目后执行npm run dev --prefix frontend。后端、worker和前端分别保留独立终端。

1. 练习题生成选两个已有知识点、生成2–3题，预览并自行确认调用。检查每题的“考查知识点”和JSON是否分别对应题意，允许综合题关联多个。旧历史结果不回填重算。
2. 任意一种真实AI功能生成成功后，点击开始新问题，保持相同问题、资料范围和设置，再预览。若命中，点击“使用已有结果（不调用AI）”，无需远程发送勾选，直接显示原结果。
3. 如果要新答案，保留命中提示，勾选发送确认，点击“仍要重新生成（调用AI）”。这才会增加模型调用。
4. 修改问题、学习方式、题数或资料范围，重新预览应不复用不同设置的结果。删除资料/更改Topic后，原预览不能复用，需重新选择有效范围。

## 文件与交接

新增：backend/app/services/ai_result_reuse.py；frontend/src/features/ai/ReusableResult.tsx；backend/tests/m2/test_ai_topics_reuse.py；frontend/tests/unit/m2/ai-topics-reuse.test.ts；frontend/tests/e2e/m2/ai-result-reuse.spec.ts；本文件。

修改：backend/app/schemas/question_drafts.py、remote_ai.py；backend/app/ai/question_drafts.py；backend/app/services/question_drafts.py、remote_ai.py；backend/app/routers/remote_ai.py；backend/tests/m2/test_question_drafts.py；frontend/src/api/client.ts；frontend/src/features/ai/RealQueries.tsx、QuestionDraftView.tsx、AIResultStatus.tsx。公开QuestionDraft形状未改变，不需要重生成其JSON schema。

同步：AGENTS.md、README.md、docs/contracts.md、api.md、user_guide.md、test_report.md、README.md，docs/gcx/README.md、features.md、optimizations.md、m2_plan.md、m2_remaining_audit_2026_10_17.md、changed_files_2026_10_16.md，collaboration/gcx/README.md、progress.md及collaboration/handoff.md。旧上传副本未更新，提交前必须包含此次新增源文件及此前未提交增量；dist/缓存/运行数据/密钥不作为源代码提交。
