# 2026-10-23 全站功能核查

后续队长切片14：范围固定资料包、任务类型筛选/回历史版本与独立加载完成；本轮全量后端447通过/2跳过、165单元及106项相关双引擎场景通过。当前队长功能与清晰体验方法见[验收清单](../materialhub/captain_acceptance_2026_10_23.md)。下方11时点的全站428场景不冒称本轮全部重跑。

后续卡片13：四阶段补当前课程原对象快捷入口，M1资料卡片分别显示三种处理状态并支持详细/精简，保持统一色调与阅读/选择/整理保护；[当前实现与验证](action_cards_acceptance.md)。下方11全量回归属于此前时点，本轮不冒称重新执行全部后端。

后续视觉12：按用户最新要求，全站改为当前主题统一主色，覆盖下文08阶段的五模块固定配色；最新视觉与专项验证见[统一色调](unified_tone_acceptance.md)。下方全量功能回归保留11完成时点的实际证据，不冒称12重跑全量后端/全部浏览器场景。

记录者：Codex，辅助zhy。本次按用户“所有分界面美观、前后端一体，并核验所有功能”的要求，结合main_idea第9节、需求/共享契约、各成员交接和现有代码继续实施。正式40任务状态和成员/真人验收仍由本人填写。此前[2026-10-22核查](project_review_2026_10_22.md)是历史时点，下列增量已落地，不应继续整项列为未实现。

## 已完成的增量

- 共享层：五模块身份色、主题/底色/导航/密度/宽度、按钮与桌面选项浮层、适中字级和系统字体角色；所有11个分页面及AI/题库三模式、笔记管理/编辑/分屏延用同一视觉与导航。
- 学习记录：新增带归属过滤的六类型只读分页API，按当前课程汇总资料、笔记、问答、报告、作答与错题；标题检索/类型筛选、真实计数、显式刷新，按原UUID回到原工作区。各页共用唯一入口，不重新创建笔记/试卷或调用模型。
- 学习连续性：本机笔记恢复副本、阅读侧栏笔记、目录元数据分页/按需正文、当前资料版本/片段带入AI、知识点学习中心、显式标签练习、错题来源/复习计划、阅读书签/版本文本对照与常用筛选视图。
- M1：批量上传队列、暂停/明确重试、资料分类标签原子批量整理、冲突保护、独立加载恢复，保留原件与不可变版本。

范围与证据：[分界面](all_workspaces_acceptance.md)、[字体/记录后端](records_typography_acceptance.md)、[控件](controls_acceptance.md)、[配色](color_studio_acceptance.md)、[知识点](learning_hub_acceptance.md)、[连续性](continuity_acceptance.md)、[阅读工具](../materialhub/reading_tools_acceptance.md)。

## 全功能检查矩阵

| 域 | 核验的实际操作 | 主要浏览器测试文件 |
| --- | --- | --- |
| 认证、课程和支持 | 注册/登录、会话、课程归属、备份恢复、反馈、API设置指南、导航/路由 | platform、redo-api-guide、continuity-workspace、responsive-layout |
| M1资料 | 四格式解析/预览与文本降级、上传/版本/任务、整理/过滤、图片引用、引用目标分页、导出和回源 | material-workflows、material-preview、native-preview、material-organize、material-study-flow、reading-tools |
| M2学习 | 来源选择、问答/报告、确认前无发送、引用/错误反馈、历史/显式复用、结果到笔记 | ai-result-reuse、study-reports、question-drafts、learning-loop |
| M3笔记 | 标签/双链/引用、图片/导出、目录/批量/拖动、编辑/数学、识别文本插入、草稿/冲突/回收站 | note-tags、note-citations、note-portability、note-organization、note-layout、note-math、formula-workspace、formula-graphics、note-capture、note-continuity、note-trash |
| M4题库 | 正文/文件/ZIP/已有来源导入、PDF/OCR路径、Markdown/图片校正、知识标签/目录/拆合/去重与删除 | question-bank、bank-*、topic-hierarchy |
| M4作答复习 | 本地随机抽题、审阅/作答/提交后答案、选择批改/解答自评、原卷上下文、错题重做/掌握/计划改期 | question-bank、bank-self-review、bank-display-reference、redo-api-guide、review-schedule、learning-loop |
| 全站整合 | 学习记录分页与原ID回跳、知识点连接四域、主题/字体/按钮/菜单、320–1440宽度及未保存保护 | learning-records、learning-hub、workspace-polish、appearance、color-studio、controls、responsive-layout |

后端全量测试覆盖服务端权限/输入/原子操作/冲突/任务/备份/来源撤权/答案隔离等，浏览器测试覆盖用户操作；两者不能替代真实课程教学质量和平台实机试用。

## 实际执行状态

- 后端：443通过、2跳过（私有样本），158.98秒。未使用日常数据库或真实模型。
- 前端单元：最终26文件163项通过（1.84秒），包括4项新增离线/取消/本机可达/零重放回归。最终类型/生产构建通过（Vite 550ms）；入口150.31kB/gzip50.54kB，无500kB分块警告，体积不冒充性能实测。Ruff、安全显示与PDF.js检查通过。
- 迁移：临时库升级至当前head及ORM漂移检查通过，无新迁移。
- 浏览器：此前72项主题/控件/字体/布局/完整闭环通过（11.3分钟）。追加22项有20通过/2首次离线读取失败，已修复离线暂停问题。
- 全量浏览器：48文件434项Chrome/WebKit首轮实际415通过、13失败、6私有样本跳过（40.2分钟）。修复后82项相关复验全部通过（7.8分钟），覆盖全部13首轮失败。合并不同场景为428项经修复复验通过、6项私有样本跳过；不是首轮一次全绿，重复场景不相加。

测试均使用自制/授权fixtures和8056/5178临时API/前端，Mock/模拟Provider响应，真实密钥为空。测试截图在本机忽略目录；历史被测试脚本覆盖的证据图收尾恢复，不把旧图当新证据。

## 首轮发现与修复

| 首轮未通过 | 数量 | 定位与处理 |
| --- | --- | --- |
| 记录首次503被第二次读取掩盖 | 2 | 开发StrictMode清理/重建effect造成已取消首读仍发送；推迟到当前effect有效的微任务才启动，保留一次读取/显式重试断言 |
| 题库AI归类保存提示 | 4 | 脚本仍断言旧成功文案，页面实际保存；更新为当前待核验提示，继续核对服务端标签与刷新后用户选择 |
| 图形公式嵌套选区 | 4 | macOS的Control+A未全选，改ControlOrMeta+A；保持完整源码、撤销/重做、保存重开断言 |
| 字体多页面测试超时 | 1 | 整例45秒耗尽，未出现字体值断言失败；保留原脚本先复验，不以延长等待掩盖字体问题 |
| 13资料初始化等待 | 1 | 默认5秒不足以等待真实队列完成，设20秒有界等待，仍严格要求索引SUCCEEDED |
| 移出错题后刷新竞争 | 1 | 详情页无列表卡片，原零卡断言过早成立；先确认返回列表及URL无mistake，再核验数量/刷新/新作答后重新进入错题库 |

另修复首次离线弹窗UI加载/查询暂停（追加22项的2失败），保留原编辑DOM。记录使用统一transport和真实AbortSignal，关闭取消且拒绝迟到；全站本机GET查询使用networkMode=always，不被外网在线判断暂停，实际失败局部反馈，仍零自动重试/重连重放，缓存/会话/去重/写操作策略不变。普通连接错误去掉框架名与固定端口。先在契约11第6–9项记录，再改代码。

82项最终复验覆盖9文件：bank-topic-ai、formula-graphics、material-organize、learning-records、workspace-polish、color-studio、review-schedule、note-portability、redo-api-guide，包含全部13首轮失败和笔记网络恢复，最终全部通过（7.8分钟）。字体脚本保持原时限，复验通过；题库保存后的标签/用户选择、公式源码/撤销/保存和错题列表/刷新/重新答错也均通过，不只更换文案断言。

日常服务仅公开只读检查：5173首页200、8000健康200，新learning-records接口已加载，无需重启。最终截图保存在忽略目录frontend/local_only/workspaces-20261023；被测试脚本覆盖的6张历史M2证据图与最初干净的tsconfig.tsbuildinfo均恢复原始字节，不放入本轮源码差异。其余累计工作保留。

```sh
HUSTUDY_E2E_CHROME_CHANNEL=chrome npm run test:e2e --prefix frontend -- --project=webkit --project=chromium
HUSTUDY_E2E_CHROME_CHANNEL=chrome npm run test:e2e --prefix frontend -- bank-topic-ai.spec.ts formula-graphics.spec.ts material-organize.spec.ts learning-records.spec.ts workspace-polish.spec.ts color-studio.spec.ts review-schedule.spec.ts note-portability.spec.ts redo-api-guide.spec.ts --project=webkit --project=chromium
npm run test --prefix frontend
npm run build --prefix frontend
PYTHONPATH=backend .venv/bin/python scripts/verify_migrations.py
```

## 当前保留的边界与后续方向

1. 当前新题型为选择题/解答题，练习来自用户确认题库本地抽取；旧填空/AI候选/试卷/成绩仅兼容。M3识别为可核对文本插入当前笔记，AI整理停用。不能为补“全部功能”恢复停用能力。
2. 图谱、语义检索、自动间隔复习与已审阅笔记供AI等仍需单独契约和验证。现有知识点聚合、手动计划和关键词检索已可用，不冒称上述增强已实现。
3. 优先完成全量回归发现的缺口，再以真实课程样本核对公式/表格/图片、题目答案与标签、统计和学习报告教学效果。需要真实调用的质量验证仍由用户显式确认，不自动发送资料。
4. Safari/iPhone/Windows实机、读屏器、长期学习体验、干净环境安装、托管CI和正式团队接收仍独立记录。D10流程/空表不等于已发生真人反馈。

本轮保存工作区累计源码/测试/文档，不操作日常内容、提交/推送或代签成员。
