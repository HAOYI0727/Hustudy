# 当前课程复习日程

2026-10-24，PLATFORM-COURSE-AGENDA-27，Codex辅助zhy。实施前已记录[契约27](../../contracts.md#platform-course-agenda-27)、[API增量](../../api.md)与[交接028](../../../collaboration/handoff.md#h-20261024-zhy-028)。这是共享总览对M4计划的只读集成，计划创建/改期/完成、作答与掌握仍沿M4原协议，不改变成员归属。

## 如何体验

1. 在练习中形成一道测试错题，打开回顾页，安排今天或未来的复习日期。
2. 回课程总览，展开“当前课程复习日程”。默认显示今日及逾期，切换逾期/今天/未来/已完成/全部待办。
3. 输入计划标题，点击查找或回车；每页6项，清除恢复当前课程范围。计划改动后重新展开或明确刷新。
4. 点击一项计划，进入原错题的“错题回顾与复习”；先看原题和原文，需要时再明确重做、改期或完成计划。

日期卡片、六项范围、搜索和时间线使用统一主色、系统字体、轻阴影和细指针悬浮。结果区高度有界，手机范围两列；过期/完成保留警告/成功语义。没有计划时提供真实空态，读取错误单独反馈，不伪造进度、学习时长或掌握率。

## 后端与来源边界

扩展现有GET /review-tasks的可选课程、字面标题搜索、状态与日期范围；旧调用继续兼容，旧独立计划只在全局列表可见。指定课程先验证本人有效课程，M4适配器检查Mistake→Attempt→Paper→Course完整归属，排除移出及删除课程。

在同一read snapshot中按账户时区计算日期，基础集合经课程/标题过滤，一次SQL聚合六项计数；之后状态/日期过滤、真实total和稳定due_date/id分页。不是先加载本页再统计，也没有逐计划查询。仅投影计划元数据，不获取题干、答案、作答、重做正文或存储路径；隔离测试核验请求最多5条SELECT（含认证与课程），读取不写学习数据。

总览按需展开才读取，用可取消的直接请求，错误仅明确重试，无断网重连重放；关闭、课程/账户切换拒绝迟到。回原UUID带review=plan，不自动创建redo、不调用模型，不从此只读面板改日期/完成或标掌握。

## 自动验证

后端专项6项通过（2.68秒），全量473通过/2私有样例跳过/5既有弃用警告（83.30秒）。新4项覆盖真实分页/稳定顺序、一次聚合/只读、账户/课程/伪造关联链/撤权、字面%_查找、参数预算和Honolulu/Kiritimati跨日；原2项验证旧API兼容与改期/掌握独立。Ruff与临时迁移漂移检查通过。

最终前端187单元/31文件通过（2.09秒），类型/生产构建通过（Vite643毫秒）；Markdown安全渲染及PDF.js两页图文/预算检查通过。

Chrome/WebKit扩大回归56项首轮53通过/3失败（5.3分钟），失败均为新日程主题断言在颜色过渡中立即取值。改为等待实际主题色稳定，保留用户动画；并收齐桌面搜索工具栏、响应课程/计数核对、320px展开视图与完成计划后重新打开的实际闭环。最终16项专项全部通过（1.2分钟），覆盖日程10项和手册6项；其中320px新增2项，其余与首轮重叠，58个不同浏览器场景经修正复验通过，不累加重复场景。

新日程实测包括六项计数与真实两页、字面关键词搜索/清除、刷新、普通失败/断网/401显式恢复、关闭/课程切换迟到隔离、错误课程响应拒绝、统一主题与1440/390/320无整页横向溢出、回原UUID仅回顾、明确完成计划后日程数量更新且掌握不变。旧回归涵盖学习完整闭环、上传阅读检索、历史/离开/401草稿、备份hash、五尺寸、复习日期冲突与原手册下载安全。

已查看桌面/手机日程截图，桌面输入和查找按钮同排，手机两列范围/局部滚动/日期卡片可操作。截图输出在忽略的Playwright测试目录，不覆盖成员历史证据。user.md增加操作及例子，人工清单增加W10–W12共118项，保持未勾选；现行入口统一链接仍存在的队长清单，不重建已不在工作区的根checklist.md。

## 命令与临时日志

```bash
PYTHONPATH=backend .venv/bin/python -m pytest backend/tests/shared/test_course_agenda.py backend/tests/m4/test_review_schedule.py -q
PYTHONPATH=backend .venv/bin/python -m pytest -q
.venv/bin/ruff check backend/app backend/tests backend/migrations
PYTHONPATH=backend .venv/bin/python scripts/verify_migrations.py
npm test --prefix frontend
npm run build --prefix frontend
node scripts/verify_markdown.mjs
node scripts/verify_pdf.mjs
HUSTUDY_E2E_CHROME_CHANNEL=chrome npm run test:e2e --prefix frontend -- course-agenda.spec.ts review-schedule.spec.ts learning-loop.spec.ts platform.spec.ts responsive-layout.spec.ts user-manual.spec.ts
HUSTUDY_E2E_CHROME_CHANNEL=chrome npm run test:e2e --prefix frontend -- course-agenda.spec.ts user-manual.spec.ts
```

本机临时日志前缀`/private/tmp/hustudy-agenda-`：`api-target.log`、`api-full.log`、`unit-final.log`、`build-final.log`、`migrations.log`、`e2e.log`与`final-e2e.log`。Playwright文件过滤为正则，learning-loop同时纳入manual-learning-loop；首轮实际56项、最终16项，以日志为准。临时日志/截图不是永久交付物。

所有数据为隔离库、自制题库和临时账号；未写入日常test数据、未调用真实模型、未新增表/迁移/依赖或部署云服务。正式40任务、成员/真人/实机接收仍待本人，自动浏览器不代替Safari/iPhone实机。
