# zhy 当前功能分类

2026-10-24 原文关联笔记：按版本/片段与标题检索，有效引用按笔记去重、计数与样本摘录，每页6篇。底部直接回原笔记，阅读笔记关联页按需预览并保留写作DOM；引用撤回/假引用排除，无课程归属和本人既有跨课程关系保持。[体验与验收](materialhub/reference_notes_acceptance.md)。

2026-10-24 课程复习日程：总览按需展开到期/逾期/今天/未来/已完成/全部待办，当前课程与标题过滤、真实分页6条及账户时区日期；点击仅回原错题回顾。主题日期卡片、手机两列、有界时间线、失败/401/迟到与响应课程核对；原日期修改/作答/掌握契约保持。[体验与验证](integration/course_agenda_acceptance.md)。

2026-10-23–24 完整使用引导：根[user.md](../../user.md)24章涵盖共享层/四模块的现行能力、步骤/预算/失败恢复与实例；使用指南新增按需阅读、章节搜索、原文件下载和自制传输层资料/题库/固定演示下载。实际示例走通资料→阅读笔记→题库确认→练习→错题回源→计划重做→完整备份，来源与掌握/计划边界明确。[范围与验收](integration/user_manual_acceptance.md)。

2026-10-23 25阅读导航：已打开课件总结支持按关键词/当前阅读页有效引用筛选，每页8项；目录可直达单个知识点讲解，键盘焦点及上/下项切换保持。完整总结/笔记/来源不改变，不产生新模型请求。[体验与边界](materialhub/reading_navigator_acceptance.md)。

2026-10-23 当前阅读助手由24专用视图替代21课程模式嵌入：固定本课件、三种总结侧重、可改提示词、真实页码知识点导览；23支持逐知识点摘记/自定义标题及原请求保护，复用M2/M3原闭环。[最新功能与验收](materialhub/ppt_companion_acceptance.md)。

2026-10-23 PLATFORM-CLOUD-ACCOUNT-22：共享API按开发/生产采用正确默认地址，生产默认同源/api/v1；可显式指向同一公共后端。账号库/文件持久化及现有test迁移见[云端账号说明](shared_platform/cloud_accounts.md)。未自动部署或改变本机数据，浏览器本地偏好/书签/草稿不冒充云同步。

2026-10-23 M1-READER-AI-21 / UPLOAD-LIMIT-20：阅读旁复用M2问答与报告，以设置/结果/草稿分区展示当前版本知识点，引用回跳保留阅读和编辑；笔记保存未知沿冻结request_id核对。资料单份30MiB、Office读取/反代同步，正常连接提示隐藏。[使用、验证与边界](materialhub/reader_ai_acceptance.md)。


2026-10-23 M1-UPLOAD-RELIABILITY-19：开发API默认管理worker、异常退避重启和子进程组清理；OS锁/有界心跳、认证处理连接状态和上传局部反馈，兼容PDF独立处理不堵解析/索引。生产守护与同源HTTPS示例已准备，未部署。[根因、实现、验证](shared_platform/worker_deployment.md)。

2026-10-23 M1-LEARNING-LAYOUT-18：PPT默认单页原格式、文本成组分页及全版本查找/末页定位，知识点有界分区、手机目录与按需图片工具；已有145页样例真实前后数据及草稿/引用验证见[排版验收](materialhub/learning_layout_acceptance.md)。

2026-10-23 M1-READINESS-17：资料检查可筛选/分页查看最新版本正文与三阶段状态、打开原版本并明确恢复原任务；共享首页使用当前问题份数，历史任务保留。断网/401/未知结果核对、预算和草稿保护验证见[7步验收](materialhub/readiness_acceptance.md)。

2026-10-23 M1-SOURCE-REVIEW-16：学习关联增加相关错题、有效逐字引用/整版本来源说明、本人待办/到期/最早日期与M4掌握摘要；共享回看路由持久化，明确重做后才创建练习。[功能与验收](materialhub/source_reviews_acceptance.md)。

2026-10-23 M1-LEARNING-CONNECTIONS-15：版本/片段「学习关联」汇总有效引用的已有知识笔记、资料问答、学习报告及知识点，真实计数/分页/标题筛选；原对象回跳和练习设置联动，保持撤权/旧版来源/草稿。[功能与7步验收](materialhub/source_connections_acceptance.md)。

2026-10-23 M1-SCOPED-EXPORT-14：选择资料包固定提交时的版本，仅含来源截图；范围幂等、未知提交/401显式核对、重试不扩大。处理记录补类型/状态组合筛选、原版本回跳与独立加载，沿用现有任务/权限/草稿。[全部功能体验与验收](materialhub/captain_acceptance_2026_10_23.md)。

2026-10-23 PLATFORM-ACTION-CARDS-13：四阶段卡片可回当前课程已有对象，练习仅恢复进行中作答；M1资料卡片显示版本/元数据/三种独立处理状态，支持详细/精简并保留选择、阅读和整理输入，无新增API/迁移/模型操作。[设计与验证](integration/action_cards_acceptance.md)。

2026-10-23 PLATFORM-UNIFIED-TONE-12：所有模块、首页卡片、导航、支持页和记录工具统一随当前主色联动，保留语义状态色与内容阅读区，覆盖历史08固定五色。[设计与验证](integration/unified_tone_acceptance.md)。

2026-10-23 PLATFORM-TYPOGRAPHY-09/RECORDS-10/WORKSPACE-POLISH-11：中英文字体角色、全分界面内部配色/工具布局及唯一共享学习记录入口；后端四域只读汇总、真实分页/筛选与原ID定位，保持正文/作答/草稿和停用边界。[功能与验证](integration/all_workspaces_acceptance.md)。

2026-10-23 历史PLATFORM-COLOR-STUDIO-08（已由12统一主色覆盖）：按用户追加反馈实现五模块色系、彩色学习/统计/课程卡片、实色入口、导航色图标、模块封面及工具栏；保持六字段偏好、原内容与业务行为。[设计与验证](integration/color_studio_acceptance.md)。

2026-10-23 PLATFORM-CONTROLS-07：全站按键与工具折叠样式、桌面主题选项浮层、适中标题与卡片阴影/悬浮；保留原select和业务回调、触控原生降级、编辑草稿和学习数据。[实现与验证](integration/controls_acceptance.md)。

2026-10-22 PLATFORM-APPEARANCE-06：全站外观面板、六预设/自定色、三基调、导航深浅、布局密度/宽度和设备持久化；共享语义令牌贯穿四模块及Ant Design，编辑草稿原地保持。[功能与验证](integration/appearance_acceptance.md)。

2026-10-22 M1-READING-TOOLS-05：新增本机阅读书签与同资料版本文本对照，支持历史原文回跳/固定片段校验，保留笔记草稿离开保护；账户课程隔离、失效/存储异常显式处理。[使用与验证](materialhub/reading_tools_acceptance.md)。

2026-10-22 新增知识点学习：固定原文依据、同源/同名标签笔记、含子标签题目与当前错题/计划，带入标签后仍显式设置练习；M1保存/应用/改名/删除本机常用筛选。Codex辅助zhy集成，业务主责保持。 [功能与验证](integration/learning_hub_acceptance.md)。

2026-10-22 新增阅读笔记侧栏、本机草稿恢复、笔记及题库摘要/按需正文、AI分页选材，保持原文版本与引用。Codex辅助zhy跨模块集成，不改变各模块主责。 [使用、验证与边界](integration/continuity_acceptance.md)。

2026-10-22 M1连续完善：新增跨页资料选择、批量分类/标签五种操作、整批冲突与单份整理核对；引用目标按标题分页读取，任务/列表/笔记候选独立重试。[使用与验证](materialhub/organize_acceptance.md)。

2026-10-22 后续整合：新增四域课程工作台、阅读继续、带Citation摘录笔记、结果/作答定位、错题回源与复习计划；统一导航/样式，并修复WebKit标签选择与弹窗焦点。[实现与验收](integration/learning_loop_acceptance.md)。

2026-10-22增量：资料多选/拖放串行上传、逐项状态/显式重试及原文历史版本/片段进入AI问答/报告已完成自动验证；[使用与边界](integration/material_study_acceptance.md)。全项目40任务与当前待办统一见[当前核查](integration/project_review_2026_10_22.md)，下方历史日期保持。


更新：2026-10-15；记录者：Codex（zhy队长会话辅助），本人审阅待填；工作区未提交/合并。当前状态以[完成度核查](completion_audit.md)及[正式A01–A10任务表](../../collaboration/zhy/task_status.md)为准。**核心功能已有实现，全部队长职责尚未完成验收。** 早期逐轮实现日志保存在[历史功能记录](history/features_2026_10_13-15.md)，历史待办和测试数量不代表最新结论。

## 共享基础层（zhy主责）

| 功能/任务 | 输入→输出、主要异常 | 验证及边界 |
|---|---|---|
| 工程与API，A01/A09 | 环境配置→FastAPI/前端/worker；统一request_id/错误码/本地检查 | 锁文件/脚本与回归已有；3.11/3.12各116项及同机干净源码/新依赖重建通过；正式Gitee/CI协作证据待交付 |
| 认证与课程，A02 | 凭据/课程元数据→本人课程CRUD/分类标签；401/404/409及删除确认 | PBKDF2、PyJWT标准HS256、强密钥初始化/旧会话重登；[课程整理](shared_platform/course_organization_acceptance.md)、[生命周期](shared_platform/basic_acceptance.md) |
| 数据与来源契约，A03 | schema/迁移→UUID/UTC/归属/外键/WAL、不可变来源身份 | 0001–0012链与回滚/漂移测试；公共定义只放[contracts](../contracts.md) |
| 文件/任务，A04 | 有界文件/任务→本地保存、持久worker、租约/重试/取消恢复 | 已有风险测试；统一存储/原子发布/低磁盘507已补，资源压力仍待验收 |
| 工作台与集成，A10 | 同一课程/来源→四模块布局/导航/API/共享反馈 | 自制SVG与公共CSS一致；既定Router/Query/Ant Design已接入，20项Chrome/WebKit闭环通过；完整P0/业务矩阵/发布未完成 |

## M1 MaterialHub（zhy主责）

| 功能/需求 | 输入→输出、异常/不变量 | 证据 |
|---|---|---|
| 导入/版本，FR-03/04 | PPTX/PDF/DOCX/MD≤30MiB→去重资料/新不可变版本；非法/超限/越权拒绝 | [测试](../../backend/tests/m1/test_materialhub.py)；低磁盘预检已实现/测试，本机容量及权限矩阵已补，复杂真实样本另验 |
| 解析/定位，FR-04/36 | 原件→Chunk及slide/page/docx_block/heading；扫描无正文明确提示 | DOCX正文顺序、PPTX嵌套组合/表格、Markdown Unicode偏移测试；不声称OCR |
| 阅读/来源，FR-06/07/08 | 有效版本→原件/PDF.js/文本降级/回源/引用笔记；删除撤权，旧引用不改指 | [预览测试](../../backend/tests/m1/test_preview_assets.py)；LibreOffice成功转换/legacy兼容/隐藏页定位及双引擎截图回源已补；复杂版式与完整Safari链路待验收 |
| 整理/搜索，FR-09 | 名称/分类/标签/版本范围→FTS5/BM25带定位结果 | 关键词检索已实现，非语义搜索；资料/任务及知识搜索均已分页，本机容量/双引擎与命中摘要已验 |
| 资料任务，FR-05 | PARSE/INDEX/PREVIEW→独立状态/错误、取消恢复/幂等重建 | [任务控制验收](materialhub/acceptance_2026_10_14.md)，不是全M1验收 |
| 图片/截图，FR-37的M1依赖 | PNG/JPEG/WebP→Asset、版本/页号/说明/标签、分页/反链 | 实际解码、来源/删除失效、revision冲突测试；M3附件ZIP仍缺 |
| 人工PDF来源 | 页号/转录→草稿、确认、修订、撤回与Citation | [补录测试](../../backend/tests/m1/test_manual_transcripts.py)；M4正式拆题消费待接入 |
| 课程资料包，FR-14/15/37依赖 | 本人课程→原件/版本/预览/正文/确认补录/图片/来源ZIP/hash | [实际下载验收](materialhub/material_export_acceptance.md)；不含完整笔记/AI/考试学习记录，不支持恢复 |

M1完整说明/缺口及旧方案见[materialhub目录](materialhub/README.md)。图片识别、语义检索属于P1，不能因为没有实现就称P0资料库解析失败。

## 队长跨模块集成协助（不计为M1独有功能）

| 对应业务主责 | 队长会话实际集成内容 | 归属与限制 |
|---|---|---|
| M2 / xtc | GLM课程问答、M1有界来源、预览/逐次确认/任务/校验/取消；[验收](integration/zhipu_qa_acceptance.md) | 记录在zhy，不代记xtc贡献；完整教学报告/政策/浏览器验收仍缺 |
| M3 / fzk | 图片/结构化Citation消费、安全Markdown、回源/反链、草稿来源冻结及课程删除适配 | 笔记正文/双链/知识库ZIP仍归M3；不因队长辅助标记成员完成 |
| M4 / gcx | 来源授权、蓝图/作答安全回归、课程生命周期适配 | 正式拆题/映射/统计/真实拟卷仍归M4，未全部实现 |

认证/存储/分页阶段96项回归是2026-10-15已有结果，本轮文档分类没有重跑业务测试。个人优化见[optimizations.md](optimizations.md)，跨成员接收只由[handoff](../../collaboration/handoff.md)中本人填写。

## 完整账户备份后续实现

PLATFORM-BACKUP-01在共享层补齐完整账户ZIP/空账户恢复、0012与后台任务、四模块适配器、校验/事务回滚/清理和独立页面；此前“恢复未实现”是历史，当前代码已实现并通过四格式/3图/3笔记双链/2套试卷作答往返与异常风险测试。最后101项全站及共享检查通过。M1课程包与完整账户包仍分开，M3独立相对Markdown知识库ZIP未完成，Safari/环境/压力待验收。见[验收](shared_platform/account_backup_acceptance.md)。


## 2026-10-15 共享前端基线与会话恢复

PLATFORM-WEB-BASE-01：Router URL页面/课程/引用定位、刷新/前后退/统一未保存导航保护；QueryClient会话和写入代次分区的GET去重/失效，token不入query key、无持久缓存、变更不重试。401原账户Modal重登保留笔记/资料整理草稿；公共主题/Alert/按需工作区与Modal，沿用SVG/CSS风格。

当前10项Vitest、8项Chrome/WebKit隔离闭环、check101后端及共享检查通过，独立Python3.12.13锁依赖101项通过。输入输出/异常、具体命令和未完范围见[验收](shared_platform/web_base_acceptance.md)。M1/M3只适配初始加载，未重写M2/M4内部；正式评审和全P0仍未完成。


## 2026-10-15 M1预览恢复

新增预览能力检测、阅读区原任务重试、PDF错误详情/重试打开；显示层与worker同版本legacy修复本机Safari Map新方法缺失。Office实际安装转换，PPTX保留隐藏页并核对一页一张，旧错位缓存拒绝读取/截图，有引用截图时不静默改指。当前旧课件缓存恢复146/146，原件/Chunk不改。check110项/10Vitest、双引擎14项、3.12相关17项通过；[验收](materialhub/preview_recovery_acceptance.md)区分实机观察、自动结果与未完成项。

## 2026-10-15 当前功能与自动验收收口

新增资料/笔记独立服务端分页、真实总数、≤260字符Unicode高亮摘要、来源UUID跳转，关闭搜索截断和全笔记前端筛选；PPTX嵌套组合文本/表格已支持，旧不可变版本不重写。M3只读检索与一处失效提示为队长辅助集成，不计作他人成员贡献。输入输出/异常/使用/实测详见[验收](materialhub/search_capacity_acceptance.md)。

最新116项后端（3.11及3.12分别全量）、12Vitest、20项双引擎与所有共享检查/构建通过；10课/200文档/1000笔记基线p95通过，同机干净源码/新依赖重建通过。当前核心功能没有本轮已知未修复的基本流程失败，A01–A08为Review；不等于所有极限样本/完整Safari或全站P0，A09/A10真实协作/集成发布仍Doing。

## 2026-10-15 PPT/PDF/Word原格式入口

用户新增直接预览需求：PPTX/Word读原件、本地隔离渲染；PDF按原页，转换PDF另作兼容预览。原格式支持基础样式/表格/图片、分页/缩放/PPT演示，后台完成保持模式，失败明确重试；引用/截图/版本不变。输入输出、限制和26项双引擎/14Vitest/116后端及构建证据见[验收](materialhub/native_preview_acceptance.md)。此更新覆盖早期“Office必须转PDF”的产品入口描述；不含旧.ppt/.doc或完整Office编辑动画。


## 2026-10-15 全站多屏工作台

PLATFORM-RESPONSIVE-01统一13px界面、20–26px标题与卡片密度，电脑侧栏、平板/手机吸顶抽屉导航；资料库/笔记列表窄屏折叠但保留状态，所有模块按可用宽度重排，触控44px/表单16px。PPT画布比例适配，源文档字号独立。40项双引擎/14Vitest/类型构建通过，收尾20/6项子集复验；范围、截图、未完成实机/真实用户边界见[验收](shared_platform/responsive_layout_acceptance.md)。无API/迁移或M2–M4算法重写。


## 2026-10-16 统一视觉层级与交互状态

PLATFORM-VISUAL-02：保留响应式密度，统一色板/文字/按钮/状态/焦点，顶部突出当前工作区、侧栏显示账户；补齐笔记/试卷图标和真题/蓝图可见标签，空状态按功能区分，备份独立主题，登录注册与帮助同步。42项双引擎、14Vitest、类型构建通过，7处关键配色抽样达到4.5阈值；[验收及5张截图](shared_platform/visual_polish_acceptance.md)。无API/迁移/算法变更，不能等同全站无障碍、实机或真实用户满意度。
