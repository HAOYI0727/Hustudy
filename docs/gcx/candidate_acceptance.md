# M2-CANDIDATES-01 验收与交接

2026-10-16，Codex辅助gcx实现。用户授权按依赖持续推进，不等待原排班日期。工作区未上传GitHub/未发布；人工审阅、成员接收待填写。无新增数据库列/迁移/依赖或隔离环境，不自动调用真实模型。

## 本轮交付

- 真实候选：single_choice/boolean/short_answer，historical/variant/weakness，每批1–6题。预览展示完整设置、目标Topic、已确认原题和材料后严格确认；后台单次派发，取消/过期租约/来源或Topic/原题变化阻止迟到结果采纳。
- 整批校验：数量精确、合法唯一选项/正确选项ID、布尔答案、简答rubric的Decimal精确分值、实际发送原文引用、目标章节依据、原题参考白名单、同批及原题规范化题干hash去重。失败不保存部分成功题。服务器分配ID和draft状态；语义/学科正确性不能由这些检查证明。
- M4只读适配：exam_ai_context读取当前用户有效课程Topic及双CONFIRMED原题，不发送原题答案、不改M4表或状态。已提供旧枚举转换。公开[QuestionDraft Schema](question_draft_schema.json)及Pydantic导入模型供xtc使用。
- 候选工作台：资料/精确片段、Topic、题型/数量/分值/模式/难度、原题选择，参考答案展开、知识依据回源、历史与JSON导出。包含答案的导出仅供作者审阅，不得作为考生响应。
- 固定演示：仅原始fixtures/materialhub_demo.md、进程与线程Topic、基础难度、最多2题；未知输入明确不足。新增完整固定教学报告演示，旧简化演示端点改为同一受限实现。演示不联网、不创建AI任务，不伪装真实理解。
- 报告和问答/候选精确片段选择；新增课程问答持久历史。错误仅保留安全数字code与有限Retry-After，区分余额/并发/频率/当日配额/服务流量限制，不输出原始错误body/message，不自动重发。

## 使用

重启后端与worker，刷新前端。先在「真题与模拟卷」创建Topic，再进入「AI学习 → 题目候选 · 待审阅」。选择资料、目标考点和出题设置；真实模式点击预览，核对材料/目标/原题后明确确认。变式先在考试模块导入、拆题并确认原题，再回候选页选择。当前原题确认不等于考点映射已确认，需审阅目标是否匹配。

没有模型额度时，使用项目原始样例资料并创建名称恰为“进程与线程”的Topic，选择基础、非变式、1或2题，运行固定自制演示。报告模式也能运行同一资料的固定报告演示。不要把演示生成题计入真实AI质量评估。

## 实际验证

- 首轮M2回归69 passed/16.62秒；后续公开QuestionDraft校验及关联回归82 passed/17.44秒；最终新增完整固定报告和M1关联后：**89 passed/27.77秒**。不同运行不累加。覆盖三题型、成功变式、原题照抄/同批重复拒绝、坏JSON/选项/答案/评分细则/假引用、Topic/原题变化、取消、证据不足、配额、跨用户、保留前缀、未知演示、精确片段、历史、备份恢复无重复派发。
- 全量中间版本：**167 passed / 3 failed，44.19秒**；失败仍为已有Windows的POSIX 0600、执行位和符号链接特权断言，未删改/跳过。此全量发生在新增固定报告2项测试之前；不据此推算或声称最终全量通过。
- Ruff、TypeScript/生产构建、14项Vitest通过。临时库迁移无漂移，Markdown/AI显示安全及PDF实际渲染检查通过。
- Chrome中间版本4 passed/25.6秒，390/1440px：候选使用真实临时账户/上传/Topic/演示/历史/JSON下载与内容核对，报告AI响应为HTTP替身；选中片段及无页面横向溢出通过。最终固定报告演示操作补验结果见文末。截图[候选桌面](evidence/question-drafts-1440.png)、[候选窄屏](evidence/question-drafts-390.png)已查看。
- Python3.12.4复用E:\Anaconda\python.exe、Node24.14.1，pytest全程临时库/假密钥；未读取用户资料或发起真实模型调用。Windows沙箱本地socket需在沙箱外验证，不增加新环境。

## 尚未解决的依赖与验收

1. M4无章节UUID实体，当前chapter_id是资料版本并显式声明chapter_ref_kind=document_version。正式蓝图集成必须由M4映射并重验总量/章节/总分/状态，不能把此候选当正式试卷。本轮不改M4生成器或作答。
2. M1未提供教师确认标注、M4未提供完整确认映射/统计证据契约，报告仍只标AI建议；不伪造teacher_mark/observed_exam、历史频率或个人掌握度。
3. 真实模型生成的学科正确性、至少20题人工质量检查、WebKit/实机、成员签收及Windows全站3失败仍待验。用户此前报告“基本功能正常”仅记录为操作反馈，不等于正确率验收。

## 复验命令（项目根PowerShell）

```powershell
$env:PYTHONUTF8 = '1'
& 'E:\Anaconda\python.exe' -m pytest backend/tests/test_question_drafts.py backend/tests/test_ai_error_details.py backend/tests/test_ai_scope_history.py backend/tests/test_study_report_demo.py backend/tests/test_study_reports.py backend/tests/test_remote_ai.py backend/tests/test_account_backups.py backend/tests/test_course_retirement.py backend/tests/test_materialhub.py -q
& 'E:\Anaconda\python.exe' -m ruff check backend/app backend/tests backend/migrations
npm run test --prefix frontend
npm run build --prefix frontend
$env:PATH = 'E:\Anaconda;E:\Anaconda\Scripts;' + $env:PATH
$env:HUSTUDY_E2E_CHROME_CHANNEL = 'chrome'
npm run test:e2e --prefix frontend -- study-reports.spec.ts question-drafts.spec.ts --project=chromium
```

交接H-20261016-GCX-002，见[公共handoff](../../collaboration/handoff.md#h-20261016-gcx-002)；当前任务见[M2状态](m2_plan.md)。

## 最终浏览器与构建复验

Chrome最终4 passed，22.5秒：390/1440px各验证真实临时API的候选精确片段/固定演示/答案/JSON下载/历史/完整固定报告；另两项报告AI确认/草稿/恢复使用HTTP替身。生产构建（含TypeScript与本地Office预构建）通过。截图来自最终浏览器轮次；固定报告操作在候选截图拍摄后另行断言。无真实模型网络请求。
