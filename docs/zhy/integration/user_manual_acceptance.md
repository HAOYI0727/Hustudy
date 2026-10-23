# 全站现行功能核查与完整用户手册

2026-10-23，PLATFORM-USER-MANUAL-26，Codex辅助zhy。[契约26](../../contracts.md#platform-user-manual-26)、[交接027](../../../collaboration/handoff.md#h-20261023-zhy-027)。本轮核查现有共享层/四模块，补站内使用引导与根目录[user.md](../../../user.md)，不把历史停用功能或待规划能力写成当前功能，不代签成员、真人与实机。

## 已补齐的用户入口

根user.md为按流程组织的24章现行手册，包含账号/课程、资料与版本、PPT专用助手及导航、课程AI、笔记/公式/图片/识别、知识点、题库校正/分析/蓝图/练习、自评/错题/计划、检索/记录/外观/反馈、导出/恢复及错误处理。原docs/user_guide.md保留历史增量，增加现行手册入口，不直接把历史拼接当现行说明。

网站“使用指南”增加显式完整手册阅读/下载、24章目录与正文关键词查找、焦点/宽窄布局和局部失败重试。根user.md通过Vite显式静态资产引用在开发/生产发布，同一源文件、不维护第二份正文。默认不请求正文，打开后读取；关闭取消并拒绝迟到。渲染复用现有安全Markdown，不执行HTML、不自动加载图片或外部链接。手册与示例均为公开自制内容，不含账号数据/密钥/配置。

下载自制[传输层资料](../../../fixtures/learning_loop_material.md)、[配套题库](../../../fixtures/learning_loop_questions.md)及原固定报告演示资料，不会自动导入/建课程/抽题。指南步骤修正为阅读→理解→笔记→练习→复盘；明确主笔记自动保存与阅读/AI草稿显式保存的区别。

## 示例闭环中的来源核对

手册实例如实区分两种来源：从已上传题库版本导入，冻结原题引用供错题回原题；知识标签人工确认的讲义片段供知识点中心回课程资料。粘贴题库文本不自动拥有上传版本，标签讲义关系也不会冒充题目冻结引用。

测试用网页下载的实际文件进行上传、解析、阅读笔记、题库导入/核验、选项打乱后作答/刷新恢复、错题回源、讲义聚合、安排计划、重做及完整备份下载/hash核对。计划和掌握独立，保留已掌握错题不自动完成计划。示例只有选择题/解答题，网络样例不冒充操作系统固定报告演示能力。

## 本轮功能核查矩阵

| 范围 | 实际链路 | 手册章节 | 验证入口 |
| --- | --- | --- | --- |
| 认证/课程/共享导航 | 注册、归属、课程切换、会话过期和记录 | 1–4、18、22 | platform、learning-loop、learning-hub |
| M1资料 | 校验/解析/预览/版本/定位/引用/任务和撤权 | 5–6、23 | backend全量、native-preview、source-connections/reviews |
| 当前PPT助手 | 固定版本、覆盖/引用页码、知识点导航与笔记 | 7 | reader-ai、reading-navigator |
| M2课程学习 | 预览同意、报告/问答、失败与固定演示 | 8 | backend全量、learning-loop |
| M3笔记 | 目录/导入/标签/编辑/公式/图片/引用/草稿 | 9–11 | note-organization/portability/citations/math/capture |
| M3回收站 | 批量删/恢复/清空、到期与冲突 | 21 | backend全量、note-trash |
| 知识点 | 来源确认、候选区别、题目/笔记/错题聚合 | 12、15 | learning-hub、source-connections |
| M4题库 | 原件/规则识别/审核、标签、拆合/统计/蓝图 | 13–15 | question-bank、bank-review-tags |
| M4练习/错题 | 选项映射、保存恢复、自评、来源/每日目标 | 16–17 | bank-self-review、redo-api-guide、manual-learning-loop |
| 复习日期 | 时区、日期保存/改期、计划与掌握独立 | 17 | review-schedule、source-reviews |
| 导出/完整恢复 | 笔记/资料/账户用途与恢复条件 | 20 | backend全量、note-portability、platform、manual-learning-loop |
| 外观/布局/手册/反馈 | 全站主题、窄屏、指南、实际静态下载 | 19、22、24 | appearance、responsive-layout、user-manual |

本轮覆盖现有功能与异常，不恢复AI自动出题/笔记AI整理，不新增语义检索、图谱或自动间隔复习。正式40任务、模型真实教学准确性、复杂真实课件、实机与长期体验仍需各自核验。

## 自动验证记录

后端全量469通过、2私有样例跳过、5既有弃用警告（78.87秒）；Ruff通过，临时迁移升级与模型漂移检查通过。前端187项单元/31文件通过（2.74秒），类型/生产构建通过，手册/样例静态资产实际发出。手册首轮6项Chrome/WebKit阅读/下载/离线与关闭验证全部通过（30.4秒）。

示例脚本首次因控件定位不匹配失败1项，中断1项/未执行8项；修正为实际combobox后跑通至备份，发现脚本使用旧下载按钮名，停止1项/其余9项未执行，修正为“下载完整备份”。这些是测试定位问题，没有修改判分/来源契约来配合脚本。最终手册与示例10项Chrome/WebKit全部通过（1.8分钟），包括恶意HTML/脚本/外部图片不执行、不请求和真实下载逐字节校验。

扩大回归240项首轮232通过、8失败（23.7分钟）；8项均为外观测试仍要求纯色backgroundColor，而当前资料卡片已使用渐变。按实际设计改为检查linear-gradient、主题wash/tint两端与选中边框，继续保留正文对比色/焦点/溢出断言；没有为通过测试退回旧版纯色界面。外观20项双引擎专项最终全部通过（2.7分钟）。240个不同场景经修正复验通过；20项专项及先行手册10项属于240项的重叠子集，不累加。

安全Markdown脚本首次因Node没有Vite的import.meta.env而无法启动，修正仅在临时编译文件中注入固定公开开发环境，不读本机配置/密钥。随后NotePreview/AIAnswerPreview的脚本、危险URL、外部图片、双链改名/删除、图片占位和表格检查通过；PDF.js自制两页PNG/文本/预算/越界检查也通过。已实际检查1440/390手册截图：目录/正文有界、字级适中、没有整页横向溢出。

### 命令与日志

```bash
PYTHONPATH=backend .venv/bin/python -m pytest -q
.venv/bin/ruff check backend/app backend/tests backend/migrations
PYTHONPATH=backend .venv/bin/python scripts/verify_migrations.py
npm test --prefix frontend
npm run build --prefix frontend
node scripts/verify_markdown.mjs
node scripts/verify_pdf.mjs
HUSTUDY_E2E_CHROME_CHANNEL=chrome npm run test:e2e --prefix frontend -- user-manual.spec.ts manual-learning-loop.spec.ts
HUSTUDY_E2E_CHROME_CHANNEL=chrome npm run test:e2e --prefix frontend -- platform.spec.ts learning-loop.spec.ts learning-hub.spec.ts source-connections.spec.ts source-reviews.spec.ts native-preview.spec.ts reader-ai.spec.ts reading-navigator.spec.ts note-organization.spec.ts note-portability.spec.ts note-trash.spec.ts note-citations.spec.ts note-math.spec.ts note-capture.spec.ts question-bank.spec.ts bank-self-review.spec.ts bank-review-tags.spec.ts review-schedule.spec.ts redo-api-guide.spec.ts appearance.spec.ts responsive-layout.spec.ts user-manual.spec.ts manual-learning-loop.spec.ts
HUSTUDY_E2E_CHROME_CHANNEL=chrome npm run test:e2e --prefix frontend -- appearance.spec.ts
```

本机临时日志前缀`/private/tmp/hustudy-manual-`：`api.log`、`unit.log`、`migrations.log`、`build-current.log`、`loop-final-e2e.log`、`broad-e2e.log`与`appearance-final-e2e.log`。临时日志/截图不是源码交付或永久证据，测试截图默认在忽略目录，不覆盖成员历史截图。核查于10月23日开始，外观与文档收尾跨日至10月24日。

所有测试使用临时数据库/存储、自制文件和固定演示/替身，未调用真实模型、未向日常test写入数据，未部署云服务或代签成员。截图输出默认在忽略的测试目录，不覆盖各成员已记录证据。
