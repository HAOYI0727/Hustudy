# 相近历史问答推荐与人工确认（2026-11-01）

后续范围更新：用户追加M2-RELATED-REPORT-08，[学习报告也支持相近目标推荐](related_reports_2026_11_01.md)。以下“报告保持精确/不返回推荐”仅描述07阶段，当前由08覆盖；问答规则保持。最新主体3976行/CSS65，共享1579单列，详见当前统计说明。

任务：M2-RELATED-QA-07。用户授权直接修改Hustudy-main-1031，不制作历史项目副本；用户后续单独授权更新PPT代码量页，其他PPT页面和截图保持。功能修改只涉及M2问答、相关接口、测试及文档，未改统一SQL资料或日常账户数据。

## 当前功能

资料问答继续优先使用原有精确复用；没有精确命中时，在相同来源、模型与设置下，推荐最多3条文字相近的历史问答。展示当前问题、原问题、原答案摘要、模型和生成时间。用户点击“查看原答案”，阅读完整历史回答，再勾选“我已对照原问题和原答案，确认适用于本次问题”，才能明确使用历史答案。也可不采用，沿原流程确认发送、生成新回答。

例如原问题为“依据所选资料，解释事务的ACID特性，并说明UNDO和REDO的区别。”，加入“仅”后不再逐字相同，但可获得相近历史问答推荐。不修改原问题，不把文字相近认定为语义等价。否定、范围和任务要求仍需用户核对，不移除实际请求中的“仅”“不”等限制词。

采用的是原结果的ID、原问题和原引用，不把旧回答改名为新生成。查找、查看及采用不调用模型、不新增AI任务，也不自动采用推荐。精确复用、学习报告及已停用出题的行为保持。

## 匹配与安全边界

- 仅同账户、同课程、相同模型/端点、当前配置修订、完整成功且使用当前问答提示词的真实历史结果。
- 资料正文、版本、用户选择范围、补充笔记和生成设置快照必须一致；所有来源及引用仍有效。不放宽成“同文件名”或“同课程即可”。
- 问题按Unicode NFKC和大小写规范化提取英文词与中文相邻词组，使用本地加权重合度排序；不是Embedding或模型语义判断。界面不展示百分比，防止将其理解成答案正确率。
- 最多读取最近100条合格历史元数据，排名后最多完整复核12个候选，去除相同原问题的重复历史，最多返回3条。候选范围有界，不能保证找到所有历史或所有同义改写。
- 没有显式选择课件时，问题改写可能改变检索片段；来源快照不同就不会推荐。用相同所选课件测试最容易复现。
- 查看、采用均在服务端重新检查候选资格；预览过期、已经确认派发、撤回/删除来源、修改笔记或配置后拒绝旧推荐。外账户请求404，不匹配或失效返回409。
- 前端异步读取有取消与代次保护，关闭/切换不采用迟到结果，401不自动重放。正文使用既有安全Markdown，摘要作为普通文本展示。

## 接口

预览与未派发请求响应新增`related_results`，默认空列表，每条字段为`id/query/answer_preview/model/created_at`。有精确`reusable_result`时不同时展示相近推荐。报告始终不返回此推荐。

- `GET /api/v1/remote-queries/{query_id}/related-results/{result_id}`：重新复核后查看原AIResult。
- `POST /api/v1/remote-queries/{query_id}/related-results/{result_id}/reuse`：要求`{"confirm_related_reuse":true}`；字符串`"true"`、数字1、false及缺失均拒绝。
- 原`POST /remote-queries/{query_id}/reuse`保持精确匹配规则。

实现入口：[related_answers.py](../../../backend/app/services/related_answers.py)、[RelatedAnswers.tsx](../../../frontend/src/features/ai/RelatedAnswers.tsx)。无新依赖、数据库迁移或真实模型请求。

## 实际验证

全部后端用临时数据库、自制事务材料与MockTransport；前端浏览器为隔离8056/5178服务并拦截模型发送，不使用日常账户或真实密钥。

- 联合回归146 passed（58.62秒）：新推荐、精确复用、远程问答、长课件分批、执行窗口、补充来源及账户隔离。1条既有Pillow getdata弃用警告，不宣称全量项目测试已通过。
- 随后补充已确认请求拒绝、同账户跨课程拒绝，并修正测试fixture写法；最终新功能专项20 passed（9.24秒），与联合回归重叠，不累加。
- 前端40文件250单元通过；类型检查、生产构建及相关Ruff检查通过。
- Chrome 390/1440px：新推荐2项及原精确复用2项，共4 passed（19.9秒）；验证先查看再勾选采用、保留原问题、零生成发送和零新增AI任务。
- 风险覆盖：仅字变化/改写、相同原问题去重、列表上限、严格确认、跨账户/课程/版本范围、未知ID、资料删除、笔记更新、配置清除、过期、已派发、部分结果、失败任务、旧提示词及报告隔离。
- 首轮新增与精确复用合计20项，19通过/1测试调用密钥清除接口的参数位置错误；按实际接口改为query revision后通过，未放宽业务规则。静态检查发现fixture同名导入遮蔽，已改显式fixture依赖并复验。

命令（项目根目录）：

```powershell
python -m pytest backend/tests/m2/test_related_answers.py backend/tests/m2/test_ai_topics_reuse.py backend/tests/m2/test_remote_ai.py backend/tests/m2/test_qa_batches.py backend/tests/m2/test_m2_execution.py backend/tests/m2/test_m2_supplements.py backend/tests/shared/test_account_ai_isolation.py -q --tb=short
npm test --prefix frontend -- --maxWorkers=2
npm run build --prefix frontend
```

浏览器（frontend目录）：

```powershell
$env:PYTHONUTF8 = "1"
$env:HUSTUDY_TEST_PYTHON = "E:\Anaconda\python.exe"
$env:HUSTUDY_E2E_CHROME_CHANNEL = "chrome"
npm run test:e2e -- --config playwright.m2.config.ts related-answers.spec.ts ai-result-reuse.spec.ts --project=chromium
```

## 用户简易验收

1. 重启后端/托管worker，刷新前端。保持之前成功问答的账户、资料选择、模型、笔记和修复设置。
2. 把原问题加上“仅”或改写，点击预览，查找“找到可能相关的历史问答”。
3. 核对原问题和摘要，点“查看原答案”；确认按钮在未勾选前不可用。
4. 勾选已核对，再明确使用。右侧展示历史原答案，通知保留原问题；不会新增生成任务或消费模型调用。
5. 如不适用，不勾选采用，仍可在原发送确认区生成新答案。完全相同问题继续走精确复用。

真实课程与模型质量仍由用户验收。用户追加授权后已重新统计并另存PPT代码量更新版：主体逻辑34文件3962行，CSS另2文件65行，共享15文件1579行另列。统计清单和说明已同步，原PPT与其他页面不覆盖。

## 重启

保存当前工作，后端、前端终端各按Ctrl+C。默认由后端托管worker，不再单独运行第三个worker。无新依赖，不必重装环境。

后端：

```powershell
Set-Location 'E:\aauniversity\Three1\软件工程\Hustudy\Hustudy-main-1031'
$env:PYTHONUTF8 = "1"
python -m uvicorn app.main:app --app-dir backend --reload --reload-dir backend/app
```

完整解释器路径写法（二选一）：

```powershell
& 'E:\Anaconda\python.exe' -m uvicorn app.main:app --app-dir backend --reload --reload-dir backend/app
```

前端另一个终端：

```powershell
Set-Location 'E:\aauniversity\Three1\软件工程\Hustudy\Hustudy-main-1031'
npm run dev --prefix frontend
```

访问http://localhost:5173/，必要时Ctrl+F5。若曾手动关闭worker自动托管，则继续使用原外部worker方案并重启它，不能同时启动重复worker。
