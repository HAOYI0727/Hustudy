# M2-STUDY-REPORT-01 验收记录

日期2026-10-16；成员gcx，实际实现Codex辅助。需求FR-16–20、FR-18.1–12；任务B02/03/05/06/07/08/09/10。代码在本地工作区，未上传GitHub、未发布。本人审阅与其他成员接收均待填写。

## 实现与使用

AI学习 → 章节学习报告 · 需确认 → 选择资料和学习方式 → 预览片段/覆盖范围 → 勾选确认 → 后台生成 → 查看报告、自测与引用 → 可编辑草稿 → 确认保存为笔记。

仅依据有效本人课程文本（包括已确认补录）；最多6片段、每片段2000字符、总计8000字符。按所选版本及正文顺序选择，预览逐版本显示实际片段数/字符数；超出部分不发给模型，不能称完整全章。输出上限6000 tokens。未连接教师/真题依据，标签仅AI建议。结果自动持久化，可读取最近20条历史；旧来源删除后嵌套/顶层引用同时失效。保存笔记仍由用户确认。

## 已执行证据

- Python 3.12.4（E:\Anaconda\python.exe），现有Anaconda环境；未新建环境。Node24.14.1，未安装新依赖。pytest使用临时数据库、假密钥/MockTransport；不读取用户资料、不调用真实模型。
- 最初M2报告+已有问答：36 passed，5.42秒；随后新增报告账户备份往返测试，以后续结果为准，不叠加计数。
- 全量后端初次：129 passed / 3 failed，29.37秒（新增备份用例之前）。3项为既有Windows平台假设：test_jwt_contract的POSIX 0600、test_preview_recovery的chmod执行位、test_storage_contract创建符号链接需特权。未更改这些断言或关闭安全检查；不宣称全量通过。
- Ruff、TypeScript检查与前端生产构建通过。Vitest 14 passed。沙箱内Vitest遇到临时缓存rename EPERM，改在沙箱外复验通过；未通过增加环境或降级依赖规避。
- Chrome桌面1440px、窄屏390px：2 passed，14.7秒，截图[桌面](../evidence/study-report-1440.png)、[窄屏](../evidence/study-report-390.png)，已实际查看。账户/资料/笔记使用临时真实API，AI HTTP响应用固定替身；覆盖确认前不发送、结构化展示、自测展开、实际保存笔记、刷新恢复且不重复确认、无页面横向溢出。不能称真实模型端到端验收。
- pytest最初在沙箱内Windows asyncio本地socket初始化阻塞；沙箱外20项问答回归通过。测试结束释放SQLite连接池，修复Windows临时库清理错误，不改运行数据库。

最终补充回归结果见本文件文末及[个人进度](../../../collaboration/gcx/progress.md)。

## 可复验命令（项目根PowerShell）

```powershell
$env:PYTHONUTF8 = '1'
& 'E:\Anaconda\python.exe' -m pytest backend/tests/m2/test_study_reports.py backend/tests/m2/test_remote_ai.py backend/tests/shared/test_account_backups.py backend/tests/shared/test_course_retirement.py -q
& 'E:\Anaconda\python.exe' -m ruff check backend/app backend/tests backend/migrations
npm run test --prefix frontend
npm run check --prefix frontend
npm run build --prefix frontend
$env:PATH = 'E:\Anaconda;E:\Anaconda\Scripts;' + $env:PATH
$env:HUSTUDY_E2E_CHROME_CHANNEL = 'chrome'
npm run test:e2e --prefix frontend -- study-reports.spec.ts --project=chromium
```

## 验收边界与后续

真实模型返回质量/耗时、完整真实报告浏览器闭环、WebKit和实机、教师/真题标签、M4真实候选及全站Windows平台测试适配均未完成。本轮不标FR-18全部人工验收或M2全部完成，不将用户此前跑通已有流程当本轮报告验收。

## 最终补充回归

报告/既有问答/账户备份/课程删除关联回归：**45 passed，9.63秒**，包含17个报告用例（新增报告备份恢复往返且不重新派发）。Ruff通过；迁移升级/ORM无漂移通过（临时库），Markdown/AI显示安全和PDF.js检查通过；TypeScript复验通过。本轮未重复全量后端，之前129通过/3失败如实保留，不把后续45项叠加成全量成绩。

补充：Markdown检查入口已适配Windows，通过Node直接调用本地TypeScript JS入口；首次迁移检查遭沙箱临时目录权限限制，沙箱外使用临时数据库和假配置通过。未修改已有3项全量失败测试。

最终代码复验（提示词学习方式说明/标签约束/worker异常保护完成后）：45 passed，14.69秒；Chrome 2 passed，17.1秒；Ruff及前端类型/生产构建通过。截图已更新到此轮。
