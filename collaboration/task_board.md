# P0 公共任务与集成记录

## 当前状态入口（2026-10-16）

共享基础层 + M1核心自动验收通过，正式A01–A08为Review，A09/A10为Doing；不能写成全站P0或正式发布完成。已实现JWT、存储/分页、前端基线、完整账户恢复、原格式阅读与多端视觉。剩余为复杂样本/实机、极限资源、本人评审/成员签收、M2–M4剩余P0、集成发布和真实试用。

- [zhy正式十任务](zhy/task_status.md) / [技术核查](../docs/zhy/completion_audit.md)：当前调度与实现边界。
- [测试报告](../docs/test_report.md)：10-15后端116项；10-16前端14Vitest、42项双引擎/类型构建通过；不同日期不累加。
- [交付路线](roadmap.md) / [GitHub同步](github_sync.md)：后续模块工作与提交步骤。

本文件下表是早期骨架的**聚合任务历史**，A01–A05与正式十任务的编号/语义不同。例如旧A04是“解析与检索”，正式A04是“文件存储/Job”。不能据此把正式A01/A02或全部队长任务标Done。B/C/D原历史条目与增量保留，不冒记成员贡献；GLM问答后续集成见文末。

## 初始聚合任务历史

协作证据增量 DOC-TEAM-01（2026-10-13）：两套四人成员目录与持续 handoff 已建立并完成文档结构/链接检查；成员接收状态为待接收，见 [H-20261013-ZHY-002](handoff.md#h-20261013-zhy-002)。此项不扩展产品 P0 功能，不改变已有业务任务状态。

状态：`Todo / Doing / Review / Done / Blocked`。下面的 `Done` 只表示当时骨架或垂直切片已有代码与验证，不代表当前正式任务或全部 P0 验收完成。

| 任务 | 负责人 | 需求 | 当前状态 | 验收证据 |
|---|---|---|---|---|
| A01 运行环境与应用工厂 | A | NFR-10 | Done | `README.md`、启动脚本 |
| A02 认证与课程归属 | A | FR-01–02/NFR-06 | Done | `routers/auth.py`、`courses.py` |
| A03 资料版本/切片/任务模型 | A | FR-03–05 | Doing | `models/material.py` |
| A04 四格式解析与关键词检索 | A | FR-04、06、09、36 | Doing | `services/materials.py`、`documents.py` |
| A05 文件预览/图片/导出/备份 | A/C | FR-08、14–15、37 | Doing | test_materialhub.py；附件 ZIP/完整备份待办 |
| B01 Mock Provider 与证据状态 | B | FR-16–20 | Doing | `routers/ai.py`、API 冒烟 |
| B02 StudyReport 教学结构 | B | FR-18、38 | Doing | StudyReport schema/test |
| B03 真实 Provider 与预算 | B | FR-20、45 | Todo | TC-12 |
| C01 Markdown 笔记与 revision | C | FR-10–11 | Doing | `routers/notes.py` |
| C02 双链/反链/Citation | C | FR-12–13 | Doing | API 冒烟、TC-08 |
| C03 图片引用/导出/备份 | C | FR-14–15、37 | Doing | 图片嵌入/反链测试；附件 ZIP/恢复待办 |
| D01 真题导入/拆分/确认 | D | FR-39–40 | Doing | `routers/exams.py` |
| D02 Topic 映射与统计 | D | FR-35、41–43 | Todo | TC-29–30 |
| D03 蓝图/拟卷/审阅 | D | FR-21–24、44–45 | Doing | API 冒烟、TC-13–14 |
| D04 作答/错题/复习 | D | FR-25–30 | Doing | API 冒烟、TC-15–18 |
| I01 前端工作台与四模块导航 | A + 全员 | NFR-10 | Doing | `frontend/src/main.tsx`、Vite build |
| I02 权限/API/E2E/性能测试 | 全员 | NFR-02、06–10 | Doing | 15 项 API/风险测试；E2E/性能待办 |

成员映射已确认：A=zhy、B=xtc、C=fzk、D=gcx，见 [roles.md](roles.md)。仓库账号、Issue/PR 链接及开始/结束日期按实际补充。个人进度见同名目录，跨成员记录见 [handoff.md](handoff.md)。

## 按日期的公共集成增量

### 2026-10-13 C 模块交接增量

C01/C02：`features/notes/index.tsx` 已提供搜索、模板、自动保存、冲突对照、双链插入和反链；`routers/notes.py` 使用原子 revision 更新。C03：单笔记 Markdown 导出已实现，图片附件导出和完整恢复仍为 Todo。新增 `test_notes_workspace.py` 验证冲突、反链、导出、归属和删除失效。该增量不将整模块标记为 Done。

### 2026-10-13 共享工作台连接增量

I01：新增课程内查找、指定资料片段/笔记直达与使用指南；补齐浏览器 viewport/标题/键盘入口。FR-06/09、FR-10–12、FR-16、NFR-09/10，仍为 Doing。前端构建通过，pytest 8 passed；Safari 业务验收等待登录。后续优先级与具体风险见 [experience_roadmap.md](experience_roadmap.md)。

### 2026-10-13 A/M1 主责切片

A03/A04：不可变版本、Alembic 0001–0003、旧库备份/升级、独立 worker 租约恢复与重试、四格式定位、FTS5 已有代码及测试，仍为 Doing（资源/性能和完整验收未完）。
A05/C03：PDF/转换预览降级、安全图片/嵌入/反向引用已有代码，状态改为 Doing；课件截图、附件 ZIP 与完整恢复继续 Todo。
C01/C02：安全 Markdown 预览、最新双链标题、失效提示、Citation 回源和原文插入已集成；资料反链及完整浏览器验收待补。
B01：来源过滤与 AI 草稿原子 Citation 保存已集成；真实 Provider 和完整教学输出仍 Todo/Doing。
D03/D04：蓝图配额、截止、题目/选项归属、提交幂等、提交后答案接口已测试；统计与真正三模式拟卷仍未实现。
I02 改为 Doing：pytest 15 passed、Ruff/迁移漂移/Markdown 安全/构建通过；Safari 新资料库渲染已观察，完整 E2E、压力、用户反馈未完成。以上不代表模块全部 Done，不代表人类成员完成了对应实验。

### 2026-10-13 M1-ORGANIZE-01 状态更新

A04/I01：资料分类/标签、元数据部分更新、精确标签搜索、最新/历史版本范围、可读任务记录、统一 SVG/控件与原文查找/专注阅读已实现。C02 接口增量：M3 只读服务提供原文→笔记反向引用；不修改笔记正文。0004 迁移、18 pytest、Ruff/安全渲染/构建通过，Safari 已观察现有 PPTX 117 切片、香农 2 命中、整理面板/专注/回顶与资料/AI 样式。上述更新旧段落中的“资料反链/分类待补”局部状态；A04/I01/C02 仍 Doing，课程/笔记标签、完整浏览器验收和 P0 其余关口未完成。交接 H-20261013-ZHY-003 待接收。

### 2026-10-14 M1-PREVIEW-ASSET-01

A03/A04/I01：0005 来源迁移、PDF.js 按页阅读、成功页 PNG 保存、固定版本/页号与回页、来源删除/课程删除图片撤权；M1 图片 HTTP 入口独立，M3 URL/嵌入语法兼容。22 pytest、迁移/Markdown/PDF.js 双页渲染/构建通过；Safari 图片区渲染已观察，完整上传/截图/回页 E2E 待测。保持 Doing，未将 FR-37 图片标签/附件导出或全 P0 标 Done。交接 H-20261014-ZHY-001 待接收，下一步依赖见 docs/zhy/materialhub/materialhub_gap_analysis.md。

### 2026-10-14 M1-TRANSCRIPT-01

A03/A04/I01：人工 PDF 草稿/确认/历史修订/撤回、FTS/Chunk/Citation 来源、原解析真实状态与重试保留；0006 和来源消费适配已有实现。26 pytest、Ruff、迁移/安全/PDF.js/构建通过，运行库与本会话 worker 同步。A03/A04/I01 仍 Doing，M4 正式人工来源拆题消费、Safari E2E、资产检索、任务管理、完整导出/恢复未验收；交接 H-20261014-ZHY-002 待接收。

### 2026-10-14 M1-ASSET-ORGANIZE-01

A03/A05/I01：图片名称/说明/标签、revision 冲突、元数据查找/精确标签/来源/排序/分页、引用笔记跳转已有实现；0007 旧图回填/中断回滚与原 UUID 保留。M3 只适配插入菜单名称，正文/引用行为不改。30 pytest、Ruff、迁移/安全/PDF.js/类型/构建通过；运行库 head=0007。更新旧记录“资产标签/说明检索待补”的代码状态，完整 FR-37/P0 仍 Doing：附件导出/完整恢复、资料/任务分页、显式任务取消/重建、Safari E2E/压力仍未验收。交接 H-20261014-ZHY-003 待接收，未提交/合并。

### 2026-10-14 M1-JOB-CONTROL-01

A03/A04/I01/I02：显式取消/恢复、UUID幂等索引重建、租约迟到保护、FTS回滚、依赖预算不重置已有实现，5新风险测试和全量35pytest/共享检查通过；最终列表归属与前端调整分别补验通过。Safari113片段/预览降级/重建入口与图片空状态局部观察，不等于完整交互。独立验收课程创建被切换打断，确认未保存；共享下拉样式按截图优化，最终截图待复验。完整验收见[报告](../docs/zhy/materialhub/acceptance_2026_10_14.md)，交接H-20261014-ZHY-004待接收。更新旧“取消/重建待实现”的代码状态，但资料/任务分页、附件备份、压力/全资源/E2E仍Doing。

### 2026-10-14 M1-EXPORT-01

历史聚合A03/A05/I01/I02：0008/后台资料包/原件+确认来源+图片/校验器、来源撤权/预算/租约恢复与共享SQLite时间比较修复；40pytest/共享检查通过。Safari真实3资料/3版本包生成→下载完成、374片段/377内容文件与整包hash校验通过。资料包不是完整备份，M3笔记ZIP/全部账户恢复仍待办；压力、分页、环境/LO、全资源与发布关口未验收。正式队长十任务映射见[验收报告](../docs/zhy/materialhub/material_export_acceptance.md)，旧表聚合编号不当作十任务Done。交接H-20261014-ZHY-005待接收，未提交/合并。

### 2026-10-14 共享课程删除与基本回归

PLATFORM-COURSE-DELETE-01（正式A02/A03/A04/A10）补齐0010、模块清理接口/同事务、确认影响/revision/名称、孤立笔记复习与失效Citation保持。47项自动检查通过；Safari确认保护通过，用户库未删除课程。[验收](../docs/zhy/shared_platform/basic_acceptance.md)、[handoff007](handoff.md#h-20261014-zhy-007)待本人接收。

认证目前是自定义签名令牌，标准JWT迁移需评审；资料/任务分页、M3附件ZIP/账户恢复、M2/M4完整能力、环境/性能/E2E/发布仍保留Doing/Todo。旧A02的Done仅是骨架切片，不能视为全部验收。

### 2026-10-14 真实课程问答集成

M2-ZHIPU-QA-01在zhy集成会话扩展B03/B04/B07/B08的课程问答依赖：GLM-4.7-Flash、0011、M1有界来源、预览/确认/单次后台/schema与原文验证。67项回归/共享检查、自制真实1引用417tokens通过。待成员本人评审/接收，不能标完整B/M2 Done。

真实教学报告、M4模型题目、完整AI评测/政策/Safari闭环继续Doing/Todo；不改其他成员个人贡献。[验收](../docs/zhy/integration/zhipu_qa_acceptance.md)、[handoff008](handoff.md#h-20261014-zhy-008)。

### 2026-10-15 队长缺口实现

正式A02补标准JWT；A04/A05补FileStorage原子发布/低磁盘；A08补资料/任务服务端分页，A10同步页外回源/会话反馈。最终96项全站及共享检查通过；历史标准JWT/分页待办已更新为实现，环境/压力/Safari/完整恢复/前端基线与发布仍Doing。详见zhy/task_status.md和docs/zhy验收，交接010待本人接收。

### 2026-10-15 完整恢复与前端基线增量

PLATFORM-BACKUP-01/0012补齐账户ZIP与空账户恢复（四格式/图片/笔记/双链/试卷作答等往返和异常回滚通过），不等同M3独立知识库ZIP。PLATFORM-WEB-BASE-01补Router/Query/Ant Design基线与401同账户重登保留草稿，10项Vitest与8项隔离Chrome/WebKit闭环通过；独立Python3.12锁依赖101项通过。此前标准JWT/完整账户恢复/前端基线/3.12待办由新结果覆盖，正式A01–A10仍按[当前表](zhy/task_status.md)保留人类评审/完整矩阵/Office/容量性能/Gitee发布关口，交接011/012待本人接收。

### 2026-10-15 M1预览恢复

M1-PREVIEW-RECOVERY-01补齐Office依赖、Safari legacy兼容、环境检测/原任务恢复、隐藏页导出与错位缓存保护。实际check110项/10Vitest、双引擎14项、3.12相关17项通过；原无截图缓存已146/146，Safari曾显示第一页，最终新标签页因会话过期需重登。A07仍Doing（复杂版式/完整矩阵/正式评审），检索分页与容量/性能另列，交接013待接收。见[验收](../docs/zhy/materialhub/preview_recovery_acceptance.md)。

## 2026-10-15 M1-SEARCH-02：队长功能与自动验收收口

Codex辅助zhy，工作区未提交/合并；先更新公共契约，再补资料/笔记独立分页和纯文本Unicode命中摘要、只读M3检索适配器、PPTX嵌套组合文字/表格提取。修复原搜索50条截断和长文命中不可见，引用继续绑定原document/version/chunk，不修改不可变旧版本。补录撤回时笔记显示“来源当前不可用”，M2/M4内部算法与其他成员个人记录未改。

最终check116 pytest/16.69秒、12Vitest及共享检查/构建通过；独立3.12工作区116项16.96秒；Chrome/WebKit20项1.8分钟。19类读取/10种越权变更、课程撤权、补录确认/引用/撤回、索引UUID、搜索分页回源均通过。10课/200实际上传资料/1000笔记/5000片段，5类接口各100次/4并发p95最大275.814ms；20张PPTX/50页文本PDF解析索引0.191/0.1766秒。同机干净源码/新Python3.12venv/npm ci重建115项21.66秒与共享检查通过（早于归属矩阵新增快照，最新116项另验）。

证据：docs/zhy/materialhub/search_capacity_acceptance.md与evidence原始JSON，统一交接H-20261015-ZHY-014。无用户数据读取或真实模型调用；本机M4/24GiB高于建议基线，不冒记低配/跨机器/所有Office版式。A01–A08进入Review，Gitee/正式签收/集成发布/真实试用及M2–M4剩余P0继续Doing，不代签成员。

## 2026-10-15 M1-NATIVE-PREVIEW-01：原格式直接阅读

用户明确要求按原格式预览；Codex辅助zhy，工作区未提交/合并，FR-06/36及CR-M1-NATIVE-01。先更新契约，再接PPTX/Word直接OOXML本地渲染；PDF仍原页，转PDF另叫兼容预览。原数据/引用不变，API原件读取可取消，后台解析完成只补文本不切走当前视图。统一控件/格式标识、PPT演示、翻页/缩放、Word样式表格图片、失败重试；旧.ppt/.doc/完整动画/编辑不纳入本切片。

运行时置于无same-origin/无连接的nonce隔离iframe，仅传文件字节/随机通道；原件仍由既有归属接口读取。固定依赖及嵌入许可/对应源码说明保留；dev/build的pre钩子生成本地IIFE和notices，不用外部文档服务。主模块按需加载原格式阅读器，不将约1.31MB运行时塞入主入口。

最终26项Chrome/WebKit（各13项）2.1分钟、14Vitest与类型/构建通过，共享check116项19.60秒及迁移/安全显示/PDF实渲染通过。首轮坏文件注入受StrictMode重复读取影响，修正测试；随后WebKit发现后台切回文本的真实问题，修复并固定时序测试后全量通过。未新跑容量/3.12全量/干净依赖安装，不冒记历史证据为本轮结果。未访问现有账户或新发起真实模型请求，其他成员个人目录未改。

证据docs/zhy/materialhub/native_preview_acceptance.md；统一交接H-20261015-ZHY-015，zhy及成员本人审阅/接收待填写。复杂字体/动画/图表和本机Safari全矩阵仍按真实边界，不将26项通过等同全站P0或发布完成。
