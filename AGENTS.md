# Hustudy：Codex 开发规范

## M3提交整理（2026-10-19）

用户已确认第1–8项验收通过，第9项暂缓，并明确授权整理文档、提交与推送GitHub，覆盖下方历史“不提交”限制。只提交本项目相关源码、测试、迁移、依赖许可和文档，排除密钥、运行数据、临时材料和无关回归截图。停用功能旧操作指南已清理；旧表/接口兼容不得随文档清理删除。后续团队接收仍按第20节执行。提交收尾的SQLite内联外键检查按实际PRAGMA补全反射信息，禁止为消除误报重建notes；测试须确保真实动作差异仍被检测。

## M3-CAPTURE-TEXT-01（2026-10-19，fzk）

用户确认图形公式本轮验收通过，要求停用笔记AI整理和语音/文档直接生成新笔记。文字识别、音频转写与实时语音仅提供可核对的文本，确认后插入当前笔记选区，经原编辑器保存/撤销；不创建识别专用笔记，不添加页号/时间标题或AI格式。移除管理页识别新建及AI配置入口；整理接口返回410，后台取消遗留QUEUED/RUNNING整理任务并撤销租约，不再调用Provider。历史识别结果和笔记保留，旧密钥保留加密存储，仅允许读取状态/清除，禁止新配置与启用；不影响M2 AI学习。保护当前编辑会话、正文变化、401/409和关闭后识别草稿，使用隔离库/浏览器与自制文件验证零自动新建、纯文本、选区/撤销/保存和停用边界。先契约后实现，无新迁移，更新collaboration/docs/README，继续不提交推送。

## M3-EDITOR-MATH-03（2026-10-18，fzk）

用户已确认M3-EDITOR-MATH-02已有功能验收通过。本轮借鉴AxMath文档中的分类符号面板、结构子字段与键盘导航，独立实现常用符号图形按钮/结构图标、最近使用、本地结构填写及原公式参数恢复，改进参数选区与退出结构后的连续输入。只借鉴交互，不复制商业软件代码/图标，不引入计算或识别功能。保留可见LaTeX源码、原数学库/11种生成器及标准Markdown保存；只对识别明确的结构提供字段，未知语法原样保留，不做有损重写。输入变化、嵌套、撤销/重做、401草稿、取消及触屏/键盘操作使用隔离测试验证。无新依赖/API/迁移，先契约/交接后代码；同步fzk文档与README，不提交推送。

## M3-EDITOR-MATH-02（2026-10-18，fzk）

用户已确认M3-EDITOR-MATH-01手动复验通过，并要求参考LaTeX速查页扩展项目内公式编写。本轮提供可搜索分类符号/结构库、选区嵌套与参数导航、矩阵/分段/对齐表格式生成、窗口内撤销重做及本地语法速查；覆盖希腊字母、关系/集合/逻辑、运算、定界符、箭头、函数、微积分、线代、字体/重音/间距/颜色/盒子和常用学科模板。继续复用本地KaTeX及标准Markdown公式，不引入完整TeX文档编译或不受限宏包，不下载外部字体/发送笔记。可编辑源码始终保留，复杂结构显式预览确认，取消不写正文；保护旧选区、401草稿、UUID引用与渲染资源边界。先契约/交接后代码，验证全部内置模板、嵌套编辑/矩阵/撤销和双引擎响应式，更新fzk文档，继续不提交推送、搁置AI识别。

## M3-TRASH-01（2026-10-18，fzk）

用户确认工作区复验全部通过，授权增加回收站、批量删除/恢复/彻底删除/清空与自动清理，默认保留30天。沿用Note.deleted，0016补deleted_at/purge_after及账户独立保留策略（1–365天或关闭）；旧删除记录从迁移时起保留30天。批量操作先锁归属并核对全部revision，清空使用回收站快照防止误删新进入的笔记。恢复保留UUID/正文/标签/引用，原目录已删则未归档，原课程不可用时显式恢复到当前课程；彻底删除清除笔记关系但不删图片/资料。既有检索/导出排除回收站，链接恢复可用，完整备份含回收站及策略且兼容0012–0015。worker每分钟有界清理，到期以UTC24小时计，离线暂停、重启续清。修改策略明确影响已有回收站内容；测试仅隔离库/浏览器，不清理用户数据、不调用真实模型，更新契约/API/fzk文档，继续不提交或推送。

## M3-LAYOUT-DRAG-01（2026-10-18，fzk）

用户确认上一轮文件夹/导入/标签/推荐/编辑器复验1–5通过。本轮按反馈收拢笔记界面：侧栏只保留目录和标题导航，中央列表集中勾选与批量动作，管理/编辑切换保留草稿与撤销历史；导入、导出、标签、推荐、图片等按需弹窗。原生对话框支持焦点约束、Escape关闭与返回触发点，处理中禁止关闭，导入重试身份不随关闭丢失。桌面拖动笔记（含已选多篇）到文件夹/未归档，拖文件夹调整父目录/根目录；仅接受本页面拖动，使用原revision与既有接口，拒绝循环/超深/冲突，失败不假更新，保留按钮操作供触屏/键盘使用。无新API、迁移、依赖或远程模型调用；先契约后代码，用隔离浏览器覆盖拖动、草稿保护、弹窗与390/1440布局，更新fzk文档，继续不提交/推送。

## M3-ORGANIZE-IMPORT-EDITOR-01（2026-10-18，fzk）

用户确认引用管理复验2/3/4成功，并要求多级文件夹、保留目录导出、批量Markdown导入/统一标签与文件夹、便捷批量标签管理、分类推荐和编辑器增强。先记录0015 NoteFolder/Note.folder_id契约，保持UUID链接、revision冲突、旧笔记与0012–0014备份兼容；文件夹限制同账户同课程、最多6级，拒绝循环/重名/非空删除。批量标签/移动原子校验全部revision，失败不部分修改。MD逐文件UTF-8校验、文件名去扩展名为标题、请求UUID幂等，失败可明确重试。ZIP保留选中笔记目录，未归档放根目录，图片相对路径和名称冲突仍正确。分类建议采用可解释本地标题/标签匹配，经用户勾选确认才移动，不宣称外部AI或发送内容。编辑器补选区格式、撤销/重做、快捷键、分屏预览/大纲/查找与专注模式，安全渲染保持。用隔离数据库测试迁移/旧备份/权限/冲突/导入/ZIP/界面，不调用真实模型；更新collaboration、docs、README；继续不提交。

## M3-CITATION-LIFECYCLE-01（2026-10-18，fzk）

用户确认图片上传/笔记导出成功并授权核查继续M3。先记录当前C01–C10审计，补资料引用闭环：同笔记同版本/切片/逐字摘录重复添加返回原引用；每篇最多50条，创建与追加都遵循；删除仅移除本人指定笔记的引用，不删原资料/正文，来源反查与旧导出撤权同步。引用列表经M1授权接口补资料名/版本号，加载失败可重试，刷新不覆盖笔记草稿，失效引用可移除。引用独立于正文revision，串行写锁保护计数/删除，无新迁移。自动保存隐藏页暂停，回到前台重新启动定时，不自动重放401/409；补计时与隔离浏览器验收。审阅笔记供M2/M4消费需联合契约，图谱等P1、实机/真人与团队签收单列，不把现有十任务或局部用户反馈当全部完成。继续不提交。

## M3-BATCH-IMAGES-01（2026-10-18，fzk）

当前用户要求优先：ZIP自动附带所选笔记实际引用的图片，只含标题.md与必要images文件，不递归加入链接笔记或整库图片；共用图片去重，解压后相对路径可读。笔记编辑器与复用的图库上传入口支持多选，每批最多20张、单张10 MiB，顺序请求既有M1接口；显示进度和逐文件结果，部分成功保留，失败仅显式重试，网络/认证/服务异常停止后续请求，不自动重放。保留上传时编辑与离开保护。先契约/基线/交接后代码，补选择隔离、解压后实际图片加载、批量/部分失败回归。无新迁移或依赖，不调用真实模型，继续不提交。

## M3-SIMPLE-EXPORT-01（2026-10-18，fzk）

按用户反馈调整日常导出：单篇.md与ZIP内笔记均按标题命名；支持勾选部分笔记，默认ZIP根目录仅含Markdown，可选附带引用图片。不再向普通用户要求命令行校验或放入重复sources/manifest/README；内部归属、hash、租约与撤权校验保留。选择与图片选项持久化在既有导出sources_json的request命名空间，重试不扩大选择，旧记录标明旧版且不回写。笔记页复用M1 AssetLibrary提供图片改名/说明/标签/引用/删除，保持未保存保护和删除影响提示，不改M1后端。先更新契约/基线/交接，再实现并验证选择隔离、同名标题、图片管理与简洁包，继续不提交。

## M3-IMAGE-NAMING-01（fzk，验收反馈修复）

用户实测双链插入/改名、ZIP校验和断网草稿保留成功，指出笔记没有图片上传入口、ZIP及包内UUID文件名难管理。本轮补编辑器“上传图片并插入”，复用M1 uploadAsset授权/文件校验接口，不自建图片存储或伪造来源。上传期间阻止切换，失败保留草稿，不自动重放401上传。ZIP下载名用用途+账户时区日期时间，包内按课程/标题及图片名称命名，处理同名、非法字符、保留名、大小写与长名称；先分配路径再转换相对链接，UUID仍保留在manifest而非用户文件名。旧包需重新导出；清单/原文/图片hash规则不变、无新迁移。先契约后实现，补实际上传/预览/导出浏览器与命名/链接/hash回归，同步fzk文档；继续不提交。

## M3-PORTABLE-NOTES-01（2026-10-17，fzk）

用户已反馈上一轮标签验收均成功，并授权继续M3其他功能；仍暂不提交。先完成C07知识库ZIP及C08断网恢复、C01删除入口（FR-10/11/12/14/37）。知识库ZIP为当前账户全部有效笔记及其引用图片，保留原始正文、转换后的相对链接Markdown、标签与Citation来源清单；文件逐项SHA-256校验，不请求外部URL。耗时打包用持久NOTE_EXPORT任务/租约，预算与失败可见，撤回来源后旧包禁止下载。0014仅新增M3派生导出记录，完整账户备份不纳入导出缓存，显式兼容0012/0013备份；迁移提案待zhy整合。删除入口显式确认并用revision防止误删并发修改；网络恢复只重试网络失败草稿，401/409及业务失败不得自动重放。测试用隔离库/存储和浏览器，不修改用户笔记，不调用真实模型；同步公共契约、API、README和fzk文档。

## M3-NOTE-TAGS-01（2026-10-17，fzk）

本轮按 fzk 用户授权开始 M3，先完成 C02/C08/C09 的笔记标签闭环（FR-09/10/11）。标签为个人笔记元数据，与正文共用 revision；最多12个，每个去首尾空白后1–32字符，精确去重。未传标签的旧调用保留原值，[]清空；冲突返回服务端标签并保留本地草稿。标签筛选不得影响双链目标解析，搜索同时支持标题/正文/标签。

Windows实测ZoneInfo("Asia/Shanghai")因缺少tzdata导致既有账户恢复失败；补锁定Windows专用tzdata依赖并复验，不能靠放宽备份时区校验掩盖问题。

先在 docs/contracts.md 和 handoff 记录 Note.tags 及0013迁移提案，再在个人功能分支实现并用临时库验证；由 zhy 评审整合迁移。完整备份标记新schema版本，旧0012备份恢复时缺失标签显式补[]，其余校验不放宽。同步 fzk 进度/功能/优化、README 与公共API；公共进度/追踪仅追加待集成证据，不代签成员或覆盖队长结论。保留本地uvloop Windows修复，不改M1解析/M2生成/M4考试或调用真实模型。

当前M2-TOPICS-REUSE（2026-10-17）：用户授权逐题知识点关联和已有成功结果复用。新候选信封开启per_question_topics，模型逐题选择所选Topic的非空子集，服务端检查重复/越界，页面和JSON保留；旧信封历史兼容，不改M4表或正式组卷。复用仅本人同课程、完全相同问题/范围快照/模型端点/当前提示词下成功的真实完整结果，来源/依赖重新校验；预览显示可复用结果，用户显式点击本地复用，不创建模型任务，仍可另行确认重新生成。不新增表/依赖、不自动调用真实API；先contracts后实现，补归属/失效/设置差异/无额外网络的模拟测试，同步gcx文档与README。

当前M2-REPORT-CAPACITY（2026-10-17）：用户确认其余功能正常，仅修学习报告。旧学习步骤8项/知识点引用3条等展示型小上限导致真实报告失败；一次审查报告所有列表/文本容量，提升至有界可用范围，完整保留而非截断超限项。自测3–5和标签合法枚举等业务约束保留，全部引用逐项校验；报告引用总预算同步调整，M3单篇笔记50引用不变。报告专属中文数量诊断，不改变问答/候选行为。不自动使用真实API，补超过旧上限且尾项假引用仍拒绝的回归，并同步文档。

当前M2-REPORT-SELFCHECK（2026-10-17）：样例真实调用漏self_checks.evidence。保留严格ReportOutput持久契约；仅模型接收层允许自测缺引用，丢弃无引用原题，基于已通过逐字引用校验的报告知识点/例题生成基础自测至至少3项，明确服务端生成提示/来源，不给原题猜引用。其他必填/结构/假引用仍拒绝，不自动真实重试。先contracts，后代码/模拟回归，更新gcx文档；不声称模拟测试等同真实模型成功率。

当前M2-REAL-MATERIALS（2026-10-17）：用户授权修复真实函数式编程PDF/PPTX使用、来源限制、校验/超时反馈和AI布局；保留现有全局测试密钥，不开发BYOK。先contracts后实现。只读检查实际资料文本，M1解析器问题先报告不擅自改。报告采用显式预览的有界全范围与分批，每批单次调用/120秒预算，成功批次用既有AIResult内部checkpoint保存，不新增表/迁移；中断后仅显式确认续跑，不重发成功批次。来源/模型配置每批重验，取消/撤权拒绝迟到写回；集合报告分节展示不伪称全文合并推理。候选保留运算符/代码空白语义，细化错误；引用编号适配报告与候选。桌面独立滚动双栏、手机结果跳转。模拟验证不调用真实API，文档同步。

当前修复M2-REPORT-STRUCTURE（2026-10-17）：学习报告report层笼统错误覆盖重名/无效概念链接。先更新契约：必填教学结构和引用仍严格验证，知识点重名给固定明确错误；仅过滤可选related_concepts中的自指/不存在/重复链接，并在页面与Markdown明确记录移除提示，不猜测目标。不静默修复必填内容、不自动重试真实模型；同步gcx文档并验证历史兼容。

当前修复M2-QA-EXCERPTS（2026-10-17）：用户要求解决问答反复引用失败。仅在问答采用服务端原文摘录编号，模型选择编号、服务端精确回填原文；兼容旧source_id/quote输出并保持逐字检查，不做模糊修复或自动真实重试。先同步contracts；报告/候选协议不改，无新依赖/迁移。记录提示词版本与离线回归，不宣称真实质量已验收。

当前修复 M2-CITATION-FEEDBACK（2026-10-17）：针对新模型返回INVALID_CITATION，先记录契约，细分无效片段ID/非原文摘录的安全提示，加强候选引用提示，并在M2页面显示引用校验失败。保持逐字校验、整批拒绝、既有状态兼容和预览确认；不读取/保存失败模型原文、不自动真实调用或重试。

当前模型覆盖（2026-10-17）：用户指定glm-5.3-flash，已切默认及原项目本机配置，兼容glm-4.7-flash。新模型只能开启思考，保留预算/确认，不自动真实调用。见文末M2-MODEL-53-FLASH及docs/gcx/model_switch_2026_10_17.md。

## 2026-10-16 当前成员与实施约定（优先于历史分工）

用户最新授权：M2不再按预排时段刻意拆分，持续完成当前可独立交付的P0，只有跨模块真实依赖才留待交接。本轮M2-CANDIDATES-01实现真实/固定自制演示QuestionDraft、M4只读Topic/已确认真题适配、候选审阅/JSON交接、精确片段选择、问答历史及安全错误细分；不写正式试卷/作答，不修改数据库schema或新建环境。M4尚无章节UUID实体，候选chapter_id暂为选定资料版本UUID，附chapter_ref_kind=document_version；M4接入正式蓝图必须显式映射并重新验收。教师标注与完整统计缺少契约时如实待办。先更新公共contracts，保留旧报告/问答兼容，所有真实请求先预览确认，不自动重试或使用用户密钥测试。

用户确认 gcx 接手 B/M2 AI Study，xtc 接手 D/M4 ExamPilot；zhy、fzk 不变。gcx 时段为10月16–17日、10月24–25日、11月1日。使用 GitHub 网页手动上传，不要求本地 Git/分支操作；历史贡献/交接不改写，不代签其他成员。复用 E:\Anaconda\python.exe，不创建环境；不读取或输出密钥、不自动调用真实模型。

上一切片 M2-STUDY-REPORT-01 对应 FR-16–20、FR-18.1–12：只实现有界来源的真实教学报告闭环，复用 RemoteQuery/AIResult/AI_ANALYSIS，不新增数据库列或迁移。请求类型与范围以版本化 JSON 信封保存在既有 query 字段；普通问答禁止使用保留前缀，服务端决定任务类型。先同步 docs/contracts.md，再实现。必须验证确认前无网络、归属/撤权、覆盖范围、严格结构/逐项引用、取消/重复确认和已有问答/备份回归。报告不自动发送修复请求，不自动标为已审阅，不伪造教师/真题标签；该切片不含M4候选，候选由当前M2-CANDIDATES-01继续交付。

本文件用于约束在此目录及子目录中的开发工作。先阅读 `main_idea.md`、`Hustudy_requirements.md` 与 `Hustudy_team_collaboration.md`；本版新增功能以 v0.4 四模块协作基线为准。用户明确的新要求优先于文档；需求发生变化时同步更新相关基线，不能悄悄扩大范围。

## 1. 项目定位与首版目标

Hustudy 是面向大学生的工具类产品，核心为PPTX/PDF/DOCX 等课程文档阅读、结构化 AI 讲解、个人知识库、Markdown 笔记与资料/图片交叉引用、历年真题分析与期末模拟题生成。沿用此前 StudyLens 的学习闭环，产品名称统一为 Hustudy。

首版完整流程：创建课程 → 上传 PPTX/PDF/DOCX/Markdown → 阅读与笔记/图片引用 → AI 知识点讲解 → 上传历年真题并校正拆题 → 确认考点与课件映射 → 查看历史分布和资料缺口 → 确认蓝图 → 生成模拟卷并审阅 → 作答 → 错题回源 → 补弱复习。

模拟题拟合是匹配用户设置的章节、题型、分值、数量和难度标签，不是预测教师真题。难度、主观题评分与费曼报告必须标注为辅助估计。

## 2. 范围与执行原则

1. 首先交付 `Hustudy_requirements.md` 中的 P0。DOCX、图片引用、真题拆分校正、考点映射与历史统计属于 P0。P1 包括语义检索、跨资料自动对齐、扫描试卷 OCR、费曼和间隔复习；考研考公外部信息聚合、语音和多人协同为 P2。
2. 4 人是开发团队规模，不能据此默认需要多人实时协同编辑。
3. 采用本地优先的 Web 单体：浏览器 + FastAPI + 本地 SQLite/文件存储。配置真实远程模型时，仅在用户确认后发送选定资料片段；不宣称全离线运行真实大模型。
4. 先定义共享领域实体、接口和状态，再开发页面。不得拼接几个 GitHub 仓库形成相互独立的用户系统与数据库。
5. 借鉴开源功能设计；若引入源码或资源，先核对对应版本许可证、保留署名和要求的声明，记录到 `docs/third_party.md`。未核实的仓库地址或许可证不得写成已确认事实。
6. 日常开发不引入微服务、Redis、复杂消息队列、Kubernetes 或图数据库。复杂处理用数据库任务记录 + 单独 worker 进程，避免请求超时。
7. 文档、笔记、试卷、答案、检索过滤与文件下载均检查用户归属。权限控制在服务端执行。
8. 所有外部模型响应经过 schema 校验和业务校验。长文本可作为字段值；结构字段、引用和题目选项不能只靠正则从聊天文本猜测。
9. 测试必须覆盖业务风险，不要求每个无逻辑 CRUD 都写同样的测试。代码、测试、迁移、接口文档和需求追踪保持一致。
10. 禁止虚构用户访谈、人工核实、性能数据、满意度、测试结果或 AI 使用日志。

## 3. 技术基线

以下是实施选型，不代表已验证所有版本组合。初始化时检查运行环境与官方文档，锁定依赖版本并提交锁文件。

| 层 | 首版选择 | 约束 |
|---|---|---|
| 后端 | Python 3.12、FastAPI、Pydantic 2、SQLAlchemy 2、Alembic | 使用同步 SQLAlchemy；耗时任务放 worker，避免阻塞异步事件循环 |
| 存储 | SQLite、FTS5、本地文件 | 启用外键和 WAL、设置忙等待；记录中文分词版本；迁移时校验 FTS5 可用 |
| 解析 | python-pptx、pypdf、python-docx、Markdown 解析器 | 按正文顺序提取 DOCX 段落/表格；不把 PPTX 或 DOCX 解析器当排版渲染器 |
| PPTX/DOCX 预览 | 本地浏览器原格式渲染；LibreOffice转PDF作为兼容路径 | 原格式在无same-origin/无网络iframe中运行；转换由worker限时，均保留文本降级 |
| 搜索 | jieba 等中文分词 + FTS5 | 原文与检索 token 字段分离，引用偏移只针对原文 |
| 前端 | React、TypeScript、Vite、Ant Design、React Router、TanStack Query | 数据请求统一；React 渲染中不直接执行生成任务 |
| 笔记 | Markdown 编辑器、react-markdown、清洗器 | 禁用未经清洗的 HTML；引用是结构化对象 |
| 模型 | LLMProvider：Mock 与可配置真实 Provider | 具体名称、端点、密钥通过配置；密钥只存后端环境 |
| 测试 | pytest、httpx、Vitest、Playwright、Ruff、TypeScript 检查 | 单元、API、闭环 E2E；不用真实网络测试替代确定性测试 |
| P1 | 选一种嵌入索引适配器、ECharts/React Flow 按需引入 | 不能同时维护 Chroma 与 FAISS；未启用语义搜索时不得声称已启用 |

真实模型适配器开发前核对所选服务的当前官方接口。Mock 只提供固定演示资料对应的确定性结果；未知输入返回能力限制，不能伪装真实理解。

## 4. 项目目录

```text
Hustudy/
  AGENTS.md
  main_idea.md
  Hustudy_requirements.md
  backend/
    app/
      core/          # 配置、安全、异常、数据库
      models/        # SQLAlchemy 实体
      schemas/       # 请求、响应、模型输出结构
      repositories/  # 带归属过滤的数据访问
      services/      # 课程、资料、笔记、AI、试卷、复习
      routers/       # HTTP 入口
      ai/            # providers、prompts、retrieval、validators
      workers/       # 解析、预览、模型生成任务
    migrations/
    tests/
  frontend/src/
    pages/           # 登录、课程、资料、阅读、笔记、试卷、错题、复习
    features/        # 按业务域组织组件与交互
    api/             # 由 OpenAPI 生成/维护的客户端
    types/
  scripts/           # 初始化、演示种子、备份恢复、启动
  data/              # 运行数据；不提交用户文件或密钥
  fixtures/          # 自制/获授权的小型测试资料
  docs/              # API、设计、决策、测试、追踪、AI记录、用户指南
```

数据库迁移由成员 A 统一整合；其他成员先提出 schema 变更。业务命名统一 `user_id` 为所有者，不混用含义不明的 `flag` 或多套软删除规则。

## 5. 领域模型与引用契约

核心实体：User、Course、Document、DocumentVersion、DocumentChunk、ProcessingJob、Note、NoteLink、Asset、AssetReference、Citation、AIResult、Topic、TopicSource、PastPaper、PastQuestion、QuestionTopicMapping、ExamAnalysisReport、ExamBlueprint、ExamPaper、Question、ExamAttempt、AttemptAnswer、Mistake、ReviewTask、Feedback。

所有用户业务对象都有 `id`、`user_id`、`created_at`、`updated_at`；数据库时间存 UTC，复习日历按账户时区计算，默认 Asia/Shanghai。响应使用带时区 ISO 8601。UUID 用于持久对象；数值排序字段不能充当永久 ID。

版本和引用要求：

- Document 是资料身份；DocumentVersion 是一次不可变内容导入。覆盖上传必须新增版本。
- Chunk 属于版本，保存 `locator_type`（slide/page/heading/docx_block）、`locator_value`、正文与原文偏移；Markdown 偏移明确使用 Unicode 字符序号、从 0 开始、左闭右开。
- Citation 同时存版本 ID、chunk ID、定位、原文摘录和摘录 hash；服务器验证摘录确实存在。后续更新资料不能静默把旧引用指向新内容。
- 笔记之间使用 `[[note:<uuid>|显示名]]`。资料引用保存结构化 Citation，通过编辑器插入；禁止仅靠名称拼接定位。
- NoteLink 保存 source_note_id、target_note_id 和显示标签。反向链接从关系计算，不重复保存两套不一致列表。
- 图片采用 Asset 和 AssetReference，保存 MIME、hash、大小、alt/caption、版本来源与归属；引用用 UUID。图片删除后所有位置显示失效，不能破坏笔记正文。图中文字只在 OCR/人工转录明确可用时进入正文检索。
- 删除笔记后，现有引用显示“目标已删除”；删除文档撤销文件读取和检索资格，只保留删除标记及引用元数据，相关引用显示不可用。不得继续发送被删资料给模型。

引用示例（ID 为示例占位符）：

```json
{
  "version_id": "<uuid>",
  "chunk_id": "<uuid>",
  "locator": {"type": "slide", "value": 12},
  "quote": "摘录的原文",
  "availability": "active"
}
```

## 6. 核心状态与异常处理

ProcessingJob：QUEUED → RUNNING → SUCCEEDED / FAILED / CANCELLED。解析任务失败可重试；worker 重启后将过期运行租约恢复为待重试，设置最大尝试次数。任务类型区分 PARSE、PREVIEW、INDEX、AI_ANALYSIS、GENERATE_PAPER。

DocumentVersion 保存 `parse_status`、`preview_status`、`index_status`，不要用单一 READY 掩盖其中某项失败。只有解析和关键词索引完成后可检索；预览失败可用文本阅读；向量索引未完成不影响关键词检索。

Note 用 `revision` 乐观锁保存；冲突返回 409，显示本地内容与服务器版本，不能静默覆盖。

ExamPaper：DRAFT → REVIEWED → READY → ARCHIVED。生成的是 DRAFT；用户审阅并确认后才能开始模拟考试。试卷及题目快照不可因重生成而改变已有作答。

ExamAttempt：IN_PROGRESS → SUBMITTED → SCORED。首次提交后不可覆盖；重复提交相同请求返回已有结果。截止时间由服务端校验；答题中每次保存都能恢复。

## 7. API 契约

统一前缀 `/api/v1`；统一错误形态 `error.code/message/details/request_id`，保留正确 HTTP 状态码。创建资源用 201，任务入队用 202，参数校验用 422，归属不可访问按统一策略返回 404。

| 域 | 主要接口 |
|---|---|
| 用户与课程 | POST /auth/register、POST /auth/login、GET /auth/me；/courses 的 CRUD |
| 资料 | POST /courses/{id}/documents；GET /documents/{id}/versions；GET /jobs/{id}；DELETE /documents/{id} |
| 阅读 | GET /versions/{id}/chunks；GET /versions/{id}/preview；GET /versions/{id}/original |
| 搜索 | GET /courses/{id}/search?q=…；结果包含定位、版本和后端评分 |
| 笔记 | /notes 的 CRUD；GET /notes/{id}/backlinks；GET /notes/{id}/citations |
| AI | POST /courses/{id}/ai-queries；POST /versions/{id}/analyses；GET /ai-results/{id} |
| 试卷 | POST /exam-blueprints；POST /exam-blueprints/{id}/generate；GET /exam-papers/{id}；POST /exam-papers/{id}/review |
| 作答 | POST /exam-papers/{id}/attempts；PUT /attempts/{id}/answers/{question_id}；POST /attempts/{id}/submit |
| 复习 | GET /mistakes；POST /review-tasks；GET /review-tasks/today；POST /review-tasks/{id}/complete |
| 备份反馈 | POST /backups；POST /backups/restore；POST /feedback |

考生接口只返回题干、选项与分值。答案、rubric 和解析在提交后由单独接口返回，不能在前端藏一个含标准答案的完整 JSON。

## 8. AI、检索与拟卷规则

P0 使用中文分词关键词检索，并以可校正的 Topic 列表统一真题与课件术语；P1 才引入向量搜索。混合检索采用 RRF 等可解释排序，不直接混合未归一化的 cosine 与 BM25 分数。排序分数不是回答正确率，不能展示成“可信度 98%”。

输入资料视为待分析数据，文档内指令不得提升为系统指令。先按归属、课程、版本有效性过滤，再检索并检查引用。返回 `grounded`、`insufficient_evidence` 或 `provider_error`，证据不足时不生成假引用。

模拟卷生成分为四步：

1. 校验蓝图：每个题型、分值、题数、章节覆盖；总分等于题型项目 `count * points` 总和。章节分配必须使用整数题数并与总题数一致；难度是标签，不是难度测量。
2. 逐题生成：题干、选项、答案/rubric、解析、章节、难度标签、引用、来源是否曾为 AI 草稿。
3. 校验与去重：引用真实、答案合法、分值精确、题数满足；同卷标准化题干 hash 去重。P1 再增加语义去重。预算内最多两轮修复。
4. 失败显式返回不足原因与可调整项，不能无声降低数量或伪造证据。成功试卷仍要求用户审阅。

客观题按规则判分；主观题保存 rubric 和 AI 建议分，允许用户覆盖并保留原建议。首次作答才算错题事件；网络重试不能重复增加错误次数。相关错题创建复习任务需幂等。

Mock 模式默认演示资料，页面固定显示“演示模型”。远程模式用户拒绝发送时仍可阅读、记笔记、检索和查看已有结果，不执行新模型任务。

## 9. 四人协作约定（概要）

| 代号 | 主责 | 接口交接 |
|---|---|---|
| A 队长 | 共享基础层 + M1 MaterialHub：认证课程、SQLite、迁移、文件存储、四格式解析、索引与集成 | 提供 DocumentVersion/Chunk/Citation/Asset/Job 契约，并维护 `main`/`develop` |
| B | M2 AI Study：Provider、RAG、知识点教学报告、重点难点考点、AI 结果校验 | 消费 M1 的 Citation，只输出结构化 StudyReport/AIResult/QuestionDraft |
| C | M3 NoteGraph：Markdown、图片、标签、双链、反链、回源、导出与冲突处理 | 使用 M1 Citation，AI 内容以可审阅草稿方式插入 |
| D | M4 ExamPilot：真题拆分映射、历史统计、蓝图、模拟题、作答、错题复习与试用 | 调用已校验的 M2 草稿，使用 M1 授权和 M3 回源跳转 |

每人维护本模块 API 与测试，并互相评审。不能让 D 独自承担所有测试。共享模型/schema 先评审；使用独立分支或工作目录，避免同时覆盖相同文件。人类团队协作不意味着自动启动多个 AI 子代理。

## 10. Codex 实施流程与完成定义

收到明确“实现第 N 阶段”时，只完成该阶段及必要依赖；收到“完成初版”时按阶段持续推进到全部 P0，不能停在计划。

阶段顺序：0 基线与契约 → 1 认证课程 → 2 四格式解析阅读 → 3 笔记图片双链 → 4 AI 分析检索 → 4A 真题拆分/映射/统计 → 5 拟卷作答 → 6 错题复习备份 → 7 测试交付。P1 在 P0 验收后推进。

每轮：检查现有代码和用户改动 → 将任务对应到需求 ID → 完成最小闭环 → 运行有针对性的测试、类型检查与构建 → 更新 `docs/traceability.md` 和 `docs/progress.md` → 报告实际结果和限制。禁止把测试未执行写成通过。

必须验证：

- PPTX 原文定位、DOCX 段落/表格顺序与预览失败降级；非法文件、扫描 PDF 无文本；图片归属、删除失效与导出恢复。
- 笔记引用、重命名、并发冲突、目标删除、版本更新。
- 另一用户不能访问任何文档、检索结果、笔记、试卷或预览文件。
- AI 输出坏 JSON、假引用、超时、证据不足、Mock/真实模式标记。
- 真题拆分、跨页题目、未知分值与无官方答案、考点映射校正、重复试卷去重、已审阅样本统计。
- 蓝图不满足约束、试卷数量分值、双来源与真题改写检测、答案不提前泄露、重复提交与中断恢复。
- 错题去重、复习时区、备份恢复完整性。

具体量化指标遵循 `Hustudy_requirements.md`；所有指标是验收目标，未经测量不能填成成果。

## 11. 课程文档与个人提交

当前附件要求的是个人需求分析实验。4 人项目可共享项目背景和技术契约，但个人提交必须由本人审阅，记录本人实际使用的提示词、采纳/修改/否决、人工核实结果。不能伪造其他成员工作或将小组计划冒充已完成实验。

`Hustudy_requirements.md` 是需求基线 v1.0；人工核实项和运行结果必须按实际证据更新，不得为了凑评分删除“未核实/未实现”的状态。教案节点、Gitee Wiki 目录、甘特图和发布维护要求见 `Hustudy_team_collaboration.md`。

## 13. 四大核心模块与共享基础层

Hustudy 采用“共享基础层 + 四个业务模块”的协作结构。四名成员各自负责一个业务模块；队长额外负责共享基础层、接口契约、数据库迁移、集成分支和最终验收。业务模块之间只能通过共享 schema、service interface 和事件契约交互，不能直接读取其他模块的数据库表。

```text
                    ┌──────────────────────────┐
                    │  Shared Platform Layer    │
                    │  Auth / Course / DB / Job │
                    │  Storage / API / Test     │
                    └───────────┬──────────────┘
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼                 ▼
       Module 1            Module 2            Module 3            Module 4
       MaterialHub         AI Study             NoteGraph            ExamPilot
       资料与知识库          AI学习分析            笔记与交叉引用         真题与复习
```

### Module 1：MaterialHub 资料库与知识索引

负责 PPTX/PDF/DOCX/Markdown/图片的上传、分类、版本、解析、预览、切片、关键词检索、来源定位和删除失效。

- 允许修改：`documents`、`document_versions`、`document_chunks`、`assets`、`processing_jobs` 及对应 repository/service/router/test；
- 对外提供：`DocumentVersion`、`ChunkRef`、`AssetRef`、`Citation`、`ProcessingJob`；
- 不负责：AI 解释文本、真题考点判断、笔记正文和试卷生成；
- 必须通过：三种文档解析、DOCX block 顺序、PPTX 预览降级、图片类型校验、跨用户下载隔离。

### Module 2：AI Study AI学习与知识点分析

负责 Mock/真实 LLM Provider、提示词版本、RAG 上下文选择、章节总结、重点难点考点报告、例子、自测题、回答引用校验和任务预算。

- 允许修改：`ai/`、`study_reports`、`ai_results`、AI schemas/services/routers/tests；
- 依赖：Module 1 只读 `Citation`、`ChunkRef` 和有效版本查询；
- 不负责：直接上传文件、修改用户笔记、创建正式试卷或写入作答记录；
- 必须通过：`grounded`、`insufficient_evidence`、`provider_error` 三种路径，坏 JSON、超时、假引用和发送确认。

### Module 3：NoteGraph 笔记与交叉引用

负责 Markdown 编辑、标签、自动保存、revision 冲突、双链、反链、图片嵌入、资料 Citation 插入、回源、知识库导出和备份交互。

- 允许修改：`notes`、`note_links`、`citations`、`asset_references`、笔记页面/组件/测试；
- 依赖：Module 1 提供有效来源，不自行解析文件；Module 2 的 AI 草稿必须作为可审阅草稿插入；
- 不负责：改变原始资料版本、替用户确认真题考点、给主观题自动定最终分；
- 必须通过：重命名后链接有效、目标删除显示失效、并发保存返回 409、导出附件 hash 一致。

### Module 4：ExamPilot 真题、模拟题与复习

负责历年真题导入元数据、拆题草稿、人工校正、Topic 映射、历史统计、资料缺口、蓝图、三种生成模式、作答、判分、错题和复习任务。

- 允许修改：`past_papers`、`past_questions`、`topics`、`topic_mappings`、`exam_*`、`mistakes`、`review_tasks` 及对应前端/测试；
- 依赖：Module 1 的来源和文件；Module 2 的结构化题目草稿；Module 3 的回源跳转；
- 不负责：重新上传或修改资料、直接调用未校验的模型文本、绕过试卷 DRAFT/REVIEWED/READY 状态；
- 必须通过：父子题不重复计分、未知年份/分值不补造、映射校正后可重算、正式试卷保留来源快照。

## 14. 队长负责的共享基础层

队长先搭建并维护以下稳定骨架，其他成员在骨架上开发，不重复创建第二套用户和数据库：

1. monorepo 目录、README、`.env.example`、锁文件和本地启动脚本；
2. FastAPI app factory、配置、日志、CORS、统一响应、错误码和 request_id；
3. SQLite/SQLAlchemy/Alembic、基础 User/Course、外键、WAL、UTC 时间和 `user_id` 过滤；
4. JWT 登录、测试用户 fixture、文件存储抽象和统一 ProcessingJob；
5. 前端路由、布局、API client、错误/加载/空状态组件；
6. CI 或本地检查入口：后端测试、前端类型检查、构建、Ruff 和迁移检查；
7. `docs/api.md`、`docs/decisions.md`、`docs/progress.md`、`docs/traceability.md` 初始版本。

队长不得在没有评审的情况下替业务成员重写模块内部实现。共享层的修改必须先更新接口契约，再通知受影响模块。

## 15. 分支、提交与合并规则

- 分支：`main` 只保留可演示版本；`develop` 用于集成；个人分支使用 `feature/m1-upload`、`feature/m2-rag`、`feature/m3-notes`、`feature/m4-exam`、`fix/<issue>`；
- 提交：使用 `feat(module): ...`、`fix(module): ...`、`test(module): ...`、`docs: ...`；一个提交尽量只解决一个可审阅问题；
- 合并前：必须说明需求 ID、修改文件、迁移变化、测试命令、未完成风险；
- 禁止：直接向 `main` 推送未测试代码、覆盖别人成员未提交的修改、在业务模块中偷偷修改共享表结构；
- 数据库变更：先在 `docs/contracts.md` 写字段和迁移意图，由队长合并迁移；
- API 变更：先更新 Pydantic schema/OpenAPI 示例和调用方，再修改 service/router；
- 冲突解决：以共享契约为准，保留两边业务行为的测试；不能用“最后一次保存”静默解决语义冲突。

## 16. Codex 模块开发协议

每次向 Codex 提交任务必须明确模块编号、需求 ID、允许修改目录和验收命令。Codex 必须：

1. 阅读 `AGENTS.md`、`main_idea.md`、`Hustudy_requirements.md`、`Hustudy_team_collaboration.md`；
2. 说明当前模块的输入、输出、依赖和不修改的目录；
3. 先检查 git diff 和已有用户改动；
4. 只完成一个可验收垂直切片，代码、测试、文档一起提交；
5. 若需要跨模块变更，先提出契约变更，不直接实现隐式耦合；
6. 运行模块测试和必要的集成测试，报告实际输出；
7. 更新进度和追踪矩阵，不把计划写成完成。

推荐任务格式：

```text
模块：M2 AI Study
任务：实现 FR-17 课程范围内带来源问答
允许修改：backend/app/ai、backend/app/services/ai、对应 schemas/tests、docs/api.md
依赖：M1 已提供有效 ChunkRef/Citation 查询
禁止修改：M1 解析器、M3 笔记表、M4 试卷表
验收：TC-10、TC-11、TC-12；pytest ...；前端构建（如涉及）
```

## 17. 集成顺序与 Definition of Done

集成顺序固定为：共享基础层 → M1 资料上传/解析 → M3 笔记与引用 → M2 AI 分析 → M4 真题与试卷 → 全链路验收。M2 和 M4 可以并行设计 schema，但 M4 只有在 M1 的 Citation 契约稳定后才能接入真实资料。

一个任务只有同时满足以下条件才算完成：需求 ID 可追踪；输入输出和异常已定义；代码通过对应测试；没有破坏其他模块；数据库变更有迁移；API 或交互有文档；真实测试结果已记录；未完成项和风险已公开。

## 18. 课程教案对齐规则

教案要求最多 4 人分组，使用 Gitee 记录软件过程和管理；个人需求分析/设计报告与小组项目交付分开计算。Hustudy 必须把课程证据当作项目交付物，而不是开发结束后补写。

| 教学关口 | 教案要求 | Hustudy 必须形成的证据 | 负责人 |
|---|---|---|---|
| 第一次课 | 头脑风暴、mindmap、会议记录/照片、NABCD、Gitee 立项 | `docs/01_project_kickoff.md`、原始会议照片、思维导图、Gitee Wiki 首页 | 队长组织，四人参加 |
| 第二次课 | 智能需求获取、需求评审 | 需求来源表、用户场景、需求评审记录、AI 协作提示词 | 队长 + Module 负责人 |
| 第三次课前 | 提交需求分析报告；第一次师生沟通 | `Hustudy_requirements.md`、AI 协作/人工核实记录、需求追踪矩阵；沟通意见和变更记录 | 队长提交，四人审阅 |
| 第四次课 | 智能化软件开发方法 | Codex/AI 使用规范、任务拆分、分支与评审记录 | 队长 |
| 第五次课 | 架构、数据结构、算法；提交设计报告；迁入迁出和代码管理；提交源代码及可执行程序 | 架构图、ER 图、API、状态机、算法说明、Gitee 提交记录、可运行版本 | 队长集成，四模块负责 |
| 第六次课 | 软件质量与智能测试 | 测试策略、测试用例、覆盖异常/性能/权限的记录 | 各模块测试，队长汇总 |
| 第七次课 | 功能/性能测试、测试报告、用户说明、公开发布、用户反馈 | `docs/test_report.md`、`docs/user_guide.md`、Gitee Pages/发布地址、匿名反馈与分析 | D 负责试用，队长发布 |
| 第八次课 | 每组 8 分钟公开讲解与展示，全程记录 | 汇报 PPT、演示脚本、录屏/照片、每名成员分工体会 | 四人共同准备 |

评分对齐：需求分析 20%，原型/概要设计/详细设计 35%，编码与测试 30%，功能创意 10%，真实用户反馈 5%；项目成绩占综合成绩 95%，考勤占 5%。不得用产品功能数量替代过程证据。教案要求每人领取约 5–10 个粒度适中的任务；当前四模块各安排 10 个任务，满足任务总数不少于 30 的要求。

每次 Gitee Wiki 更新必须包含：日期、参与者、目标、输入、决定、未决问题、变更的需求/任务 ID、证据链接。会议照片、原型访问地址、测试截图、发布地址和用户反馈不能只存在个人电脑中。
## 12. v0.3 知识点与真题分析契约

### 12.1 DOCX 与图片

DOCX 用正文 block（段落或表格）在该版本内的顺序定位；表格单元格可再指定 row/col。原始 Word 页码受布局环境影响，不能伪造。转换出的 PDF 页码是“预览页码”，不自动视作 DOCX 正文引用页码。转换/解析失败须保留可观察状态。

扫描 PDF 在 P0 可查看原页并人工补录题目。补录保存独立转录文本、来源页、确认人及时间，Citation 标 source_kind=manual_transcript；原文摘录校验针对转录文本，并保留原页供人工比对。不声称解析器已识别原图中文字。OCR 为 P1。

P0 图片支持 PNG/JPEG/WebP 上传、笔记内嵌与课件截图保存，每张≤10 MiB；服务端验证实际类型、解码尺寸和资源预算。截图保存来源版本与页号。采用 `![[asset:<uuid>|说明]]` 作为 Hustudy 内部嵌入语法，编辑器提供按钮；不是 Obsidian 插件/格式完全兼容声明。完整知识库导出把链接转成相对 Markdown 路径，并附 assets 目录和来源清单。

### 12.2 教学报告结构

StudyReport 字段：scope_version_ids、summary、topics、learning_sequence、prerequisites、examples、self_checks、citations、model_mode、review_status。

每个 topic 包含：稳定 topic_id、名称、别名、解释、重点理由、难点原因、常见误区、疑似考点、引用。每个“重点/难点/考点”标签都有 origin：

- teacher_mark：用户确认的教师标注/授课大纲；
- observed_exam：已审阅历年题中确实出现；
- ai_suggestion：AI 辅助推断。

不能把粗体或出现次数自动当教师考点；没有真题时不编“历年高频”。讲解按“学习目标→前置知识→概念→原理→例子→误区→自测”组织。来源矛盾列出双方，不强行合并成一个事实。

### 12.3 真题处理状态

PastPaper 记录 course_id、year（未知可空）、variant、provenance、document_version_id、内容 hash、review_status；来源为用户提供，默认不保证官方真实性。跨页题目可包含多条 Citation。

PastQuestion 保存原题号、题干、子题、选项、分值（未知为 null）、原始答案及其来源、AI 参考答案与其标记，不能覆盖原始答案。拆题先输出 DRAFT，用户支持合并、拆分、改题干/分值并确认。

QuestionTopicMapping 保存 topic_id、primary/secondary、依据引用、suggested/confirmed/rejected 状态。课程 Topic 可人工改名、合并；别名归一后才统计，修改已确认映射使旧报告标记 STALE 并重算。拆题与映射必须经过确认后才能进入正式统计；草稿另列不能混入分母。

### 12.4 历史统计与补弱

统计快照保存所用 paper/question/mapping 版本、未知年份数、未知分值数、独立样本数。相同文件重复上传或同年同卷重复材料按 hash 和人工确认去重。

主考点用于分值统计；次要标签用于涉及题数，不能将一道多考点题的完整分数重复加到每个考点。未知分值不按 0 分补全；单列未知数量与已知分值覆盖率。年份出现率使用已知年份的不同年份数，不能称未来命中率。

资料匹配显示“已确认有匹配/仅 AI 候选/当前已导入资料未匹配”，最后一项不等于课程没有讲过。差距报告对比历史考点、课件 Topic、笔记与本人已完成作答，未作答的掌握状态为 unknown，不从阅读时长推定掌握。

### 12.5 依据真题生成新题

新增生成模式：同考点变式、历史蓝图模拟、薄弱项专项。P0 自动数量分配在章级别；topic 目标逐题标注和校验。若用户配置严格 topic 配额，必须将其作为显式约束检查，不可作为可选提示忽略。

每题保留 original_past_question_ids（设计参考）、material_citation_ids（知识依据）、mode、topic_ids、difficulty_label、generation_status。真题题干引用不自动成为答案正确性的依据；没有课件/已审阅答案支持时提示补充资料。

标准化题干与本卷/参考原题 hash 相同则拒绝；P1 语义相似检查再检测只换名的近重复。变式应改变条件、数值或情景并重算答案，用户仍要审阅计算与开放题。冻结试卷必须记录检索资料和模型输出快照，不因后续真题重新标注改变旧作答。

### 12.6 新接口

- POST /courses/{id}/assets；GET /assets/{id}；GET /assets/{id}/references；DELETE /assets/{id}
- POST /versions/{id}/study-reports；GET /study-reports/{id}
- POST /courses/{id}/past-papers；POST /past-papers/{id}/extract；PATCH /past-questions/{id}
- POST /past-papers/{id}/confirm；PUT /past-questions/{id}/topic-mappings
- GET /courses/{id}/topics；PATCH /topics/{id}；POST /topics/{id}/merge
- POST /courses/{id}/exam-analyses；GET /exam-analyses/{id}；GET /exam-analyses/{id}/gaps

真题分析不能修改学生已保存笔记；自动生成笔记一律先保存草稿，用户确认后合并。

## 19. 当前代码协作入口

首版代码的四人协作资料统一维护在 `collaboration/`。成员缩写与现行角色为：`zhy`（张昊轶，A 队长，共享基础层 + M1）、`xtc`（向天晨，D，M4）、`fzk`（付振琨，C，M3）、`gcx`（高长鑫，B，M2），与正式 `hustudy/main_idea.md` 的现行分工一致。仓库账号、Issue/PR 地址和具体交期仍按实际补充。

`collaboration/roles.md` 维护唯一成员/模块映射；`task_board.md` 维护公共任务和真实状态；`workflow.md` 维护分支/评审/测试流程；`handoff.md` 是持续追加的跨成员交接日志；`project_handoff.md` 是环境复现指南；`roadmap.md` 记录后续范围。个人进度放入同名成员目录，具体规则见第 20 节。

当前可运行闭环为：注册/登录 → 创建课程 → 上传 Markdown 并生成切片 → 关键词搜索与文本阅读 → 创建 Markdown 笔记与结构化 Citation → Mock AI 带来源问答 → 创建考点/导入并拆分真题 → 校验蓝图 → 生成 DRAFT 试卷 → 审阅为 READY → 作答、客观评分、错题与复习任务。PPTX/PDF/DOCX解析依赖已锁定/安装；GLM真实课程问答与完整账户备份恢复已实现。真实教学报告已接入但学科人工质量仍待验；真实拟卷、OCR、语义检索、复杂统计及完整环境/性能/交付仍按当前任务与验收记录保持待办；早期任务板中的历史缺口不覆盖后续实际结果。

## 20. 四人文档隔离与统一交接规则

`collaboration/` 和 `docs/` 均必须保留 `zhy/`、`xtc/`、`fzk/`、`gcx/` 四个同级目录。目录名固定使用小写成员缩写；成员目录与业务模块编号同时写入记录，不能从文件夹归属推断实际贡献。

| 位置 | 唯一维护内容 |
|---|---|
| `collaboration/<成员>/README.md`、`progress.md` | 个人任务、进度、依赖/阻塞、下一步与交接 ID |
| `docs/<成员>/README.md`、`features.md`、`optimizations.md` | 个人负责功能的输入/输出/异常/使用说明，以及优化动机、变化、验证和限制；可增加设计、测试、AI 协作与人工核实证据 |
| 两目录根级文件 | 公共规则、操作指南、架构/契约/API、公共任务、集成进度与追踪、第三方声明；现有跨模块历史记录保留 |
| `collaboration/handoff.md` | 跨成员修改/接收/复验的统一入口，链接个人证据与公共契约 |

1. 开始任务先明确当前成员缩写（任务提示可写“成员：xtc；模块：M2”），再读公共文件、自己的目录及与任务相关的 handoff 条目，检查 `git diff`。不得仅凭模块名称推定实际实现者。默认只编辑本人记录；需修改其他成员记录时由该成员维护，或明确记录授权和代写来源，不能替其填写人工确认。
2. 每个可交接切片同时更新个人 progress、features/optimizations（确有相应变化才更新）和 handoff；未完成但影响下游的接口/阻塞也应及时记录。提交或发起 PR 前完成同步，不等到最终集成才补写。
3. 记录必须包含日期、记录者/实际实现者（含 AI 辅助）、模块、任务/需求 ID、分支及 commit/PR 或“工作区未提交”、代码范围、测试命令与实际输出、风险、接收人及下一步。没有执行的测试写“未执行”，没有成员提交的材料写“待本人补充”。
4. 公共 `docs/contracts.md`、`docs/api.md`、`docs/decisions.md` 是权威契约，不在个人目录复制第二套。跨模块/数据库变更先更新公共契约意图，在 handoff 写受影响成员与迁移需求，再按既有模块评审和队长迁移流程集成。
5. handoff 使用唯一 ID `H-YYYYMMDD-成员-序号`；新增独立条目，不覆写其他成员历史。状态区分“待接收 / 集成中 / 已验收 / 阻塞”。接收人填写本人接收/复验结果；未填写不能视为已接收，已接收不能代替合并和验收。
6. 共享层与跨模块结果由队长同步 `collaboration/task_board.md`、`docs/progress.md`、`docs/traceability.md`，用链接汇总个人证据；个人完成、集成通过和全部 P0 完成分别标记。AI 在队长会话辅助修改 M2–M4，应记入 zhy 的集成交接并列出受影响成员，不能冒记为 xtc/fzk/gcx 本人贡献。
7. 公共日志冲突时保留双方条目及唯一 ID，基于最新 develop 整理重复记录；不得以覆盖整个文件解决。任何记录不含密钥、用户私有资料或虚构会议/签收/实验结果；正式个人课程提交仍由本人审阅。

## 21. 当前课程生命周期集成约束

Course.deleted_at（0010）是课程逻辑撤权标记。各模块使用services/courses.owned_course查询有效本人课程；写入课程资源时取得共享课程写锁，来源查询仍校验父课程。不得用仅id/user_id的旧查询重新开放已删除课程。

课程删除协调器通过material/note/ai/exam_retirement的count/retire接口工作；模块适配器不自行commit，失败必须全事务回滚。保留外部笔记正文及失效Citation身份，不把课程笔记转成有效全局笔记，不留下孤立复习任务。只取消活跃任务，历史终态不改写；worker完成检查原租约与有效课程。

DELETE课程必须revision，前端先展示影响并核对名称；没有产品恢复入口，逻辑撤权不保证物理擦除。完整账户备份/恢复已由第25节后续实现覆盖；当前标准JWT见第24节，旧自定义签名令牌只是历史状态。

最新真实验收见docs/test_report.md与docs/zhy/shared_platform/basic_acceptance.md，交接H-20261014-ZHY-007待成员本人接收；47项自动检查通过不等于全部P0、性能、浏览器E2E或正式发布完成。

## 22. 智谱真实课程问答约束

当前GLM-4.7-Flash课程问答已接入，密钥只使用忽略的.env和后端SecretStr；脚本configure_zhipu隐藏输入，普通测试强制假密钥/MockTransport。不得在日志/文档/前端变量或请求正文输出密钥，输入含当前服务密钥时拒绝。

真实调用须RemoteQuery服务端来源快照→严格确认→AI_ANALYSIS任务；worker只认本模块resource_id与本人归属，不在网络等待时占SQLite写锁。引用必须来自实际发送片段，结构不从聊天正则猜测；任何失败不能伪装演示成功，不自动重发已派发请求。取消/删除不能召回已发送请求，但阻止后续采纳。

真实章节报告已在2026-10-16的M2-STUDY-REPORT-01接入，详见docs/gcx/study_report_acceptance.md；M4题目仍待接入。政策保存/训练/远程删除细项未核实，确认页如实说明；文档与接口核对不等于这些政策已核实。最新证据见docs/zhy/integration/zhipu_qa_acceptance.md和handoff008，67项回归不等于全部P0或成员本人接收。

## 23. 队长当前状态与文档分类

正式A01–A10以`collaboration/zhy/task_status.md`管理当前状态/依赖/关闭条件，以`docs/zhy/completion_audit.md`维护技术完成判断；`progress.md`与日期验收报告保留历史。公共任务板早期A01–A05是聚合编号，不得换算为正式十任务Done。当前共享基础层+M1尚未全部实现/验收，历史67项全站回归不等于全部队长任务完成。

`docs/zhy/features.md`维护当前分类功能，`optimizations.md`维护优化过程；`shared_platform/`放共享层证据，`materialhub/`放M1证据，`integration/`放队长辅助M2–M4的记录，`history/`保留归档功能日志。归档时更新引用方和文件内相对链接，保留真实日期/结果，并从历史报告链接当前核查。公共API/契约/决策、全站进度、测试报告与统一handoff仍在两目录根级，不复制成个人权威契约，也不迁入其他成员个人目录冒记贡献。

## 24. 当前认证与存储/目录实现

PLATFORM-AUTH-02后使用PyJWT2.15.1标准HS256，固定issuer/audience/用途/必需claims；旧两段token不兼容须重登。JWT密钥≥32字符，setup只初始化空值/旧占位并保留GLM配置，不回显密钥。历史0010阶段关于自定义令牌的描述仅是历史，不可覆盖当前行为。

PLATFORM-STORAGE-01提供FileStorage原子发布/不覆盖/清理和HUSTUDY_STORAGE_RESERVE_BYTES磁盘预检，低空间HTTP507。资料/图片与解析/预览/导出使用共享保护；预检不是硬配额。M1新增documents/page、jobs/page稳定分页并保留旧数组接口，页外来源须经授权单资料查询，不得仅从当前页判断已删除。最新96项回归不等于全部验收。

## 25. 完整账户备份恢复边界

0012/PLATFORM-BACKUP-01已实现账户ZIP/空账户恢复，经各模块backup适配器而非跨模块查表。恢复只到空账户，业务UUID冲突拒绝；账户凭据/密钥不导出，身份映射为当前账户，FTS重建。不自动恢复运行任务或派发模型；derived课程ZIP字节不复制，记录显示不可下载。schema变化必须更新格式/迁移/往返测试。

任何路径/字段/归属/FK/文件hash/Citation/预算失败须整体回滚业务、清理本次文件。控制记录最多50条，终态可移除，运行中不可移除；过期恢复不自动重放。删除来源后服务端旧包下载撤权。101项回归和四格式/3图/3笔记双链/2卷作答的隔离往返不等于Safari/跨机器/压力或全部P0通过。

## 26. 共享前端、会话与隔离验收

PLATFORM-WEB-BASE-01后页面/课程与可选来源定位由React Router URL驱动，不另建并行useState导航。新增导航必须通过路由器，保留hustudy:before-navigate与beforeunload保护。JSON GET复用统一QueryClient，按会话/路径/写入代次分区，不把token放query key或持久缓存；成功写入切换代次，退出清理。模型确认/生成和其他变更不自动重试。

401保持原工作区挂载并弹出原账户重登，背景inert；恢复token不得重置原笔记、资料整理等编辑草稿。切换账户先显式退出并执行未保存确认，失败请求由用户决定重试。Ant Design沿用公共主题，不引入外部字体或第二套页面风格；工作区按需加载。

本地check包含Vitest；Playwright入口npm run test:e2e --prefix frontend，使用8056/5178与临时数据库/文件，不复用用户8000/5173或密钥。测试路径使用绝对目录；Chrome channel可显式设置HUSTUDY_E2E_CHROME_CHANNEL=chrome，默认Playwright Chromium。3.12已在独立环境101项通过，现有运行环境仍3.11；8项Chrome/WebKit闭环不等于完整P0/性能/发布通过，最新边界见docs/zhy/shared_platform/web_base_acceptance.md。

## 27. M1预览兼容与页号恢复

M1-PREVIEW-RECOVERY-01后PDF.js显示层/worker使用同版本legacy，避免本机Safari缺少Map.getOrInsertComputed。Office可由HUSTUDY_LIBREOFFICE_PATH或自动发现，GET material-capabilities仅返回状态不泄露路径；POST versions/{id}/preview-jobs显式恢复，不重置失败任务次数。普通pytest固定缺失转换器保证确定性，Office成功由独立浏览器闭环验收。

PPTX转换必须包含隐藏页，输出后核对PDF页数等于原幻灯片数；预览读取和截图拒绝旧错位缓存。有既存截图时不得静默重建改变来源，须人工核对；DOCX仍标preview_page，正文引用为docx_block。测试覆盖缺少现代Map方法/隐藏页/真实三格式截图回源，不能仅以Node渲染或最新WebKit通过宣称本机Safari全部验收。具体结果按docs/zhy/materialhub/preview_recovery_acceptance.md记录。

## 28. M1分页检索与验收证据

M1-SEARCH-02新增search/page，旧search数组保持最多50条；不能把旧数组数量当总数。新分页返回纯文本excerpt/Unicode字符highlights，不得当HTML或Citation偏移。M3只读note-search适配器归该模块，M1通过接口消费，不直接查笔记表；资料筛选不约束笔记，未启用语义搜索。计数与页读取使用SQLite只读快照，跨页更新不冻结。

PPTX组合形状递归读取文本/表格，保持原slide定位；不可变旧版本不静默重解析，需导入新版本。自动验收统一scripts/accept_captain.sh，临时容量及干净环境脚本不读取用户.env/data，真实模型调用不进入验收。当前本机容量/性能、干净源码重建及20项双引擎通过的具体证据见docs/zhy/materialhub/search_capacity_acceptance.md，不能冒记真实用户评分、跨机器/完整Safari或团队签收发布。

## 29. 按原格式预览与兼容PDF边界

M1-NATIVE-PREVIEW-01后PPTX/Word直接预览用原件、本地隔离iframe；PDF继续PDF.js原页。转换PDF明确叫兼容预览，其后端preview_status不代表原格式状态。后台解析/轮询只能补文本，不重置用户当前预览视图。已有截图仍是PDF兼容页，不能把DOCX浏览器阅读页或原格式DOM截图冒充其来源。

iframe仅allow-scripts，不能加allow-same-origin/远程连接；只传原件字节和随机通道，绝不传token。消息校验source/origin/channel/页数，卸载取消请求；CSP仅执行nonce的本地IIFE。原格式依赖及完整许可由锁文件/build:office生成，dev/build的pre钩子必须保留；新增依赖或格式需同步许可和验收。旧.ppt/.doc/在线编辑/完整动画仍非当前实现，不能把PPTX支持写成所有PPT二进制格式支持。最新26双引擎/14Vitest见docs/zhy/materialhub/native_preview_acceptance.md，非完整Safari或所有Office版式通过。


## 30. 全站密度与多屏布局约定

PLATFORM-RESPONSIVE-01采用共享responsive.css统一覆盖界面密度和断点，不能在各模块重复增加互相冲突的字号/导航规则。1100px及以下使用原生dialog导航抽屉；760px及以下资料库/笔记列表可折叠，内容保持挂载；桌面仍保留侧栏。模块颜色、公共图标、按钮和空状态保持一致。

界面基础字号13px、标题20–26px，阅读内容字号与Office文件排版独立。触屏按钮/图标热区至少44px，触屏表单16px避免iOS聚焦缩放；不可用整体zoom或裁掉body溢出掩盖布局问题。长代码/表格/文档允许局部滚动。抽屉必须支持Escape、Tab循环/焦点恢复，成功导航才关闭，取消离开不能丢草稿；登录失效仍沿用原账户恢复。

共享展示变更需覆盖320/390/820/1024/1440px及Chrome/WebKit、触控媒体条件、原格式阅读和既有导航/草稿流程。尺寸模拟不是实机iPad/iPhone或TC-24真人试用，记录实际命令及截图路径。后续模块继续复用CompactLibrary/WorkspaceNavigation，不引入第二套导航或改变业务契约。

当前问题复验：少量资料仍出现结构化输出错误时，区分JSON语法与schema校验并提供无原文的字段诊断；候选提示增加完整示例，不放宽答案/引用校验，不自动修复或重发，不读取历史原始模型响应或用户密钥。

## 2026-10-16 基础功能优先核查纠正

用户再次强调队长要求：先完成main_idea.md基础功能，功能变更前更新AGENTS.md，实施同步collaboration/gcx、docs/gcx与README；前端优化不代替基础功能。不以自动测试或部分代码覆盖声称M2全部完成，暂停将长课件分批覆盖等扩展列为首要任务。

核查依据：hustudy/Hustudy_requirements.md的FR-16–20、FR-38及FR-18.1–12；main_idea.md第14.1节；实际StudyReportView、报告schema与候选代码。

- 已有实现：课程问答、报告教学字段、逐项引用、结果历史、可编辑Markdown笔记草稿、候选结构/业务校验、预览确认/后台任务/失败提示。不是全部基础功能已验收。
- 部分实现：FR-38的报告标签目前只读展示，虽可在Markdown草稿改文字，未提供逐项标签/理由编辑交互；不能把草稿文字编辑当作标签审阅交互已交付。
- 依赖缺口：ReportLabel目前仅ai_suggestion；teacher_mark/observed_exam的有依据读取、分类显示还未接入。正式候选章节/蓝图映射和试卷集成由M4共同完成。
- 待真实复验：候选JSON失败的提示词修正、三题型/模式及报告学科质量；用户明确暂缓真实调用和参考原题变式测试，不自动调用补验。
- main_idea完整设计中的概念分层/关系、独立难点突破步骤、笔记补充来源并未全部作为独立结构能力实现；需继续对照正式P0验收划分，不能将完整设计默认已覆盖或直接扩展到P1。

下一步优先补齐可独立完成的基础标签审阅/草稿闭环并逐项核查需求；真实调用待限额恢复，跨模块能力记录真实依赖。长资料增强、美化不优先于基础缺口。

## M2-LABEL-REVIEW-01 实施约定（2026-10-16）

先补FR-38标签审阅到笔记草稿闭环。前端复制独立报告快照，逐知识点增删改重点/难点/考点建议及非空理由；保留原始AI标签和来源，不修改AIResult，不把用户改标签升格教师/真题证据。标签审阅后显式进入正文编辑并调用现有笔记接口；新结果/模式切换不覆盖未保存草稿，离页/刷新保护。失效来源拒绝保存由现有服务端再校验。无新DB/schema/依赖，不调用真实模型。同步个人/公共文档，以临时API和固定演示验证。

M2-LABEL-REVIEW-01同时补main_idea 14.1的教学结构：topic增加可选concept_group、related_concepts（目标报告知识点名与关系说明）、breakthrough_steps，report增加可选review_suggestions。旧JSON缺字段按空值兼容，不重写旧AIResult。关系指向必须属于本报告且非自身/不重复，解释依据沿用该topic经校验引用；层次与步骤为AI学习建议，不冒称课程大纲。新提示词v2要求尽可能基于证据填写，不凭空补足。固定自制示例同步提供，前端/Markdown审阅草稿均保留。无数据库迁移。

M2-LABEL-REVIEW-01已按上述约定实现，实际87后端/17前端/4Chrome验证见docs/gcx/basic_acceptance.md；旧“标签只读/缺少独立教学字段”的核查作为修正前历史保留，最新实现以该验收为准。教师/真题来源、真实学科质量、M4正式组卷仍未标完成。

## M2功能入口命名（2026-10-16）

用户确认四个入口改名为资料原文检索、资料问答、学习报告、练习题生成，并在入口下按当前模式显示用途。仅改M2展示和关联浏览器定位；保留本地/真实模型标识、发送前预览确认和结果审阅，不改API/任务/模型调用/数据库。先更新本约定，再修改前端，同步gcx个人记录、README和交接。

## 2026-10-17 M2完整范围审计与持续推进

用户再次明确不按日期拆轮，能做完的独立工作继续做。以docs/gcx/m2_remaining_audit_2026_10_17.md列明R01–R10、C01–C04及V01–V04；多平台是M2职责内扩展，分批/进度计数/预算/续跑/缓存/逐题配额是被前次审计漏报的基础缺口。不把模型拥堵当本地开发停工理由，不擅自自动真实调用/重试或修改其他模块业务。共享契约与迁移按原流程，先补M2可独立契约/适配和模拟验证；已合并旧成果不等于新增待办已经完成。本次仅审计和文档更新，未改运行代码。

## M2-MODEL-53-FLASH（2026-10-17）

用户明确要求将当前运行副本Hustudy-main切为GLM-5.3-Flash。先约定再实现：配置允许旧glm-4.7-flash与新glm-5.3-flash，默认新模型；本机.env只替换HUSTUDY_LLM_MODEL，密钥等其余字节原样保留且不展示。配置脚本提供模型选项并默认新模型。新模型按官方仅支持thinking.enabled，reasoning_effort=low以控制思考预算，保持JSON模式/单次确认/超时/输出上限/引用校验，不展示reasoning_content，不自动发起真实或计费调用，不改数据库或其他模块业务。旧模型/旧历史仍兼容，切换后旧模型预览须重新生成，后台未派发旧模型任务拒绝派发。文档/测试/交接同步，原已上传83项副本不自动改写。

## M3-EDITOR-MATH-01（2026-10-18，fzk）

用户暂时搁置AI识别开发，本轮只优化Markdown编辑器。参考用户截图改为分组线性图标工具栏，保留中文悬浮说明/aria-label、键盘操作及触屏热区；不复制截图素材，不引入另一套图标体系。新增本地LaTeX公式编辑弹窗，行内/独立公式、常用模板/符号、即时预览与错误提示、选区插入和原公式修改；标准$...$/$$...$$保存，笔记预览真实渲染公式。渲染禁用可信HTML/外部资源，限制公式长度及宏展开，不改变UUID双链/图片/安全Markdown。保留撤销、草稿/冲突保护、分屏和专注；只有用户确认插入才修改正文。更新依赖许可与锁文件，覆盖390/1440布局、公式插入编辑撤销及安全回归；同步fzk文档，不提交推送，不继续AI识别功能开发。
