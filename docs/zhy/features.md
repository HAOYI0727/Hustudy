# zhy 当前功能分类

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
| 导入/版本，FR-03/04 | PPTX/PDF/DOCX/MD≤20MiB→去重资料/新不可变版本；非法/超限/越权拒绝 | [测试](../../backend/tests/test_materialhub.py)；低磁盘预检已实现/测试，本机容量及权限矩阵已补，复杂真实样本另验 |
| 解析/定位，FR-04/36 | 原件→Chunk及slide/page/docx_block/heading；扫描无正文明确提示 | DOCX正文顺序、PPTX嵌套组合/表格、Markdown Unicode偏移测试；不声称OCR |
| 阅读/来源，FR-06/07/08 | 有效版本→原件/PDF.js/文本降级/回源/引用笔记；删除撤权，旧引用不改指 | [预览测试](../../backend/tests/test_preview_assets.py)；LibreOffice成功转换/legacy兼容/隐藏页定位及双引擎截图回源已补；复杂版式与完整Safari链路待验收 |
| 整理/搜索，FR-09 | 名称/分类/标签/版本范围→FTS5/BM25带定位结果 | 关键词检索已实现，非语义搜索；资料/任务及知识搜索均已分页，本机容量/双引擎与命中摘要已验 |
| 资料任务，FR-05 | PARSE/INDEX/PREVIEW→独立状态/错误、取消恢复/幂等重建 | [任务控制验收](materialhub/acceptance_2026_10_14.md)，不是全M1验收 |
| 图片/截图，FR-37的M1依赖 | PNG/JPEG/WebP→Asset、版本/页号/说明/标签、分页/反链 | 实际解码、来源/删除失效、revision冲突测试；M3附件ZIP仍缺 |
| 人工PDF来源 | 页号/转录→草稿、确认、修订、撤回与Citation | [补录测试](../../backend/tests/test_manual_transcripts.py)；M4正式拆题消费待接入 |
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
