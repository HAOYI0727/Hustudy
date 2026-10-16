# zhy 当前任务状态与剩余交付

更新：2026-10-16；记录者：Codex（zhy队长会话辅助），本人审阅待填；工作区未提交/合并。任务DOC-ZHY-AUDIT-01。输入正式A01–A10、现有代码与验收证据，输出当前状态、剩余关口和成员依赖。本表管理任务；技术依据唯一汇总到[完成度核查](../../docs/zhy/completion_audit.md)，不复制公共API/schema。

**整体状态：核心功能自动验收通过，正式交付Doing。** A01–A08为Review（核心实现与自动证据齐备，待zhy/成员评审），A09/A10仍有真实协作/集成发布交付项。Review不是Done，不代填签收；旧聚合编号不等于正式十任务。最新证据：[测试报告](../../docs/test_report.md)、[检索/容量/环境](../../docs/zhy/materialhub/search_capacity_acceptance.md)、[多端视觉](../../docs/zhy/shared_platform/visual_polish_acceptance.md)。

| 正式任务 | 当前状态 | 当前代码与自动证据 | 关闭前的剩余事项 |
|---|---|---|---|
| A01 monorepo/环境 | Review | 锁文件/配置/启动，3.11与3.12各116项；同机临时源码全新venv/npm ci重建成功 | zhy正式评审；另一机器/OS未测，不冒记 |
| A02 用户、课程与JWT | Review | 标准JWT、CRUD/标签/revision、401草稿、双引擎名称确认删除与撤权 | 本人评审/接收；本机Safari最终删除未复验 |
| A03 SQLAlchemy/Alembic/共享schema | Review | 0001–0012、UUID/UTC/FK/WAL、回滚/漂移、共享恢复及只读分页快照 | 共享契约/迁移真实评审、集成接收 |
| A04 文件存储/ProcessingJob | Review | 原子文件/低磁盘507、租约/重试/取消/迟到保护、4并发容量读通过 | 评审；极限资源/多worker长压另列，不当基本测试已覆盖 |
| A05 上传校验与权限 | Review | 四格式有界上传/去重/不可变版本，200实际导入；19读取/10修改越权矩阵 | 正式模块验收；复杂真实样本逐份核对 |
| A06 四格式解析 | Review | PPTX嵌套组合/表格、PDF/DOCX顺序/MD定位；20张PPTX/50页PDF索引计时通过 | 真实样本人工核对；不声称OCR |
| A07 预览和降级 | Review | PPTX/Word直接原格式、PDF原页、转换兼容/截图回源；nonce隔离与后台模式保持已验 | 复杂字体/版式与本机Safari完整矩阵，zhy验收 |
| A08 FTS5/索引 | Review | BM25/标签/版本、独立分页/摘要；67命中回源，基线搜索p95通过 | 正式评审；P1语义检索和人工语义支持不混入P0计数 |
| A09 Gitee/CI/启动检查 | Doing | setup/dev/worker/check、accept_captain、隔离容量/干净重建入口 | Gitee/Wiki/分支与评审真实证据，托管CI接入或正式采用本地入口的范围评审 |
| A10 集成分支/发布构建 | Doing | 共享路由/主题/会话、完整账户恢复、多屏导航/统一视觉、42项双引擎/最终构建通过 | 等M2/M3/M4剩余P0，正式合并/发布、成员签收与至少5位真实用户试用 |


## 历史建议顺序与验收条件（最新状态以上表为准）

| 顺序/工作项 | 主责与依赖 | 完成证据 |
|---|---|---|
| 1 共享认证/前端技术基线对齐 | zhy；变更先写公共决策/契约，影响四模块 | 标准JWT异常/归属测试；路由/请求管理等实现或正式基线变更审阅记录 |
| 2 存储与规模管理 | zhy/M1 | 文件/图片/预览/导出统一预算及低磁盘失败保留既有数据；资料/任务分页的归属/稳定排序/空页测试 |
| 3 M1运行环境与完整交互 | zhy；环境允许时验证Python3.12/LibreOffice | 四格式上传/版本→阅读→截图或补录→引用回源→取消重试→导出；复杂样本/容量/性能结果，未执行项不能填通过 |
| 4 完整导出和恢复 | zhy共享协调，fzk/M3与xtc/M2、gcx/M4提供模块契约 | FR-14/15、NFR-08规定样本往返、UUID/hash一致、空账户/损坏/失败回滚；M1资料包不能替代 |
| 5 正式集成交付 | zhy组织，四模块各自验收；gcx牵头试用 | 全资源权限/E2E、成员真实接收、commit/PR/Wiki、发布和真实反馈；不代签成员 |

顺序是建议执行队列，不是已发生的团队排期决定。完整M2/M4功能仍由各自主责推进，不能把其所有内部开发重新分配给队长。GLM问答单列为[zhy集成证据](../../docs/zhy/integration/zhipu_qa_acceptance.md)，不是M1本体；其他成员个人记录未代写。

## 记录分工

- 当前任务、依赖和下一步：本文件；按日期发生的过程：[progress.md](progress.md)。
- 当前功能与限制：[features.md](../../docs/zhy/features.md)；技术完成判断：[completion_audit.md](../../docs/zhy/completion_audit.md)。
- 具体实现证据：docs/zhy/shared_platform、materialhub、integration；优化动机另见[optimizations](../../docs/zhy/optimizations.md)。
- 公共API/契约、公共任务、集成进度与跨成员交接仍维护在两目录根级；本轮[交接009](../handoff.md#h-20261015-zhy-009)待接收。

2026-10-15实现增量：PLATFORM-AUTH-02/PLATFORM-STORAGE-01/M1-BROWSE-01依次补齐标准JWT、统一原子存储/低磁盘和资料/任务分页；全量96项回归及共享检查通过。当前整体仍Doing，完整恢复/前端基线/环境与发布关口继续推进。具体证据见docs/zhy/shared_platform和materialhub，不将未测项标完成。

2026-10-15 PLATFORM-BACKUP-01：完整账户备份/空账户恢复、0012和模块快照适配器已补。四格式/3图/3笔记双链/2套试卷作答的隔离往返、篡改/归属/提交回滚/过期不重放通过；最终101项/共享检查通过。上方队列“完整导出和恢复”的代码切片已实现，跨机器/Safari/压力验收及M3单独知识库ZIP仍待推进，详情见docs/zhy/shared_platform/account_backup_acceptance.md。


2026-10-15 PLATFORM-WEB-BASE-01：React Router/TanStack Query/Ant Design既定基线落地，统一导航保护/按需加载/原账户重登保留草稿；10项Vitest与Chrome/WebKit各4项（合计8项）隔离闭环通过。共享check101项15.52秒；独立Python3.12.13锁依赖101项24.19秒。A01/A02/A09/A10实现缺口收窄，正式评审/完整矩阵/跨机器/性能/发布不冒记完成；[交接012](../handoff.md#h-20261015-zhy-012)待本人接收。


2026-10-15 M1-PREVIEW-RECOVERY-01：当前PPTX被禁用源于缺LibreOffice，安装后又实际定位Safari缺少Map新API并改legacy。环境/重试入口、隐藏页导出/页数校验和旧缓存截图保护完成；check110项15.47秒/10Vitest，双引擎14项约1.5分钟，3.12相关17项3.40秒通过。当前课件无截图旧缓存恢复146/146，Safari曾显示第一页；新标签页需原账户重登，未索取密码/外发资料。A07仍Doing，复杂样本/完整矩阵与正式接收不冒记完成；交接013。


2026-10-15 M1-SEARCH-02：新增分页与Unicode安全命中摘要，M3只读检索适配器、PPTX组合漏文修复、归属/删除矩阵、20项双引擎与隔离容量/干净重建。check116项16.69秒、12Vitest；3.12工作区116项16.96秒；同机干净源码115项21.66秒（快照早于归属矩阵新增）。10课程/200文档/1000笔记/5000chunk，4并发各100次，5类p95≤275.814ms；自制20张PPTX/50页PDF解析索引通过。A01–A08由Doing/Review统一进入Review，A09/A10正式交付继续Doing；[交接014](../handoff.md#h-20261015-zhy-014)待本人接收。


2026-10-15 M1-NATIVE-PREVIEW-01：用户要求按原格式预览，PPTX/Word本地直接渲染，PDF保持原页；兼容PDF/截图/文本引用继续独立。固定依赖及许可、隔离iframe/CSP、可取消原件请求、坏ZIP重试、后台解析不重置视图；14Vitest、26双引擎2.1分钟、类型构建通过，后端116项19.60秒。A07保持Review，旧格式/完整Office行为和实机Safari全矩阵不冒记；交接015待本人接收。


2026-10-15 PLATFORM-RESPONSIVE-01：A07/A10增加PPT比例/全站电脑平板手机排布、抽屉焦点及草稿验证；40项双引擎、14Vitest/类型构建与收尾子集通过。详见[验收](../../docs/zhy/shared_platform/responsive_layout_acceptance.md)，handoff016待本人审阅/接收。A01–A08 Review、A09/A10 Doing不变；不代记实机/真人/发布完成。


2026-10-16 PLATFORM-VISUAL-02：共享视觉/状态/图标与可见标签细化，42项双引擎3.6分钟、14Vitest/类型构建通过；[验收](../../docs/zhy/shared_platform/visual_polish_acceptance.md)。H-20261016-ZHY-001待本人审阅/成员接收，任务状态未因视觉切片改为Done。

2026-10-16 DOC-PROGRESS-SYNC-01仅校正当前文档/索引与[GitHub指南](../github_sync.md)，未重跑业务测试或执行提交推送；A09/A10仍Doing，实际commit/PR及成员接收待补，H-20261016-ZHY-002。
