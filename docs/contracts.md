# Hustudy 共享契约（Phase 0）

根目录是唯一工程根。四个业务模块通过 `backend/app/schemas`、服务接口和 API 交互，不能直接读写其他模块的表。成员 A 统一维护数据库迁移。

## API

- 前缀：`/api/v1`
- 资源 ID：UUID 字符串；时间：带时区 ISO 8601，数据库按 UTC 保存。
- 归属错误统一按 404 处理，避免泄露其他用户对象是否存在。
- 创建资源返回 201；异步任务入队返回 202；参数错误返回 422。
- 统一错误形态：`{"error":{"code","message","details","request_id"}}`。

Phase 0 已落地：`/health`、`/api/v1/auth/register`、`/api/v1/auth/login`、`/api/v1/auth/me`、课程 CRUD。其余接口按阶段增加，不在骨架中伪装为可用。

## 共享对象

`Citation` 固定包含 `version_id`、`chunk_id`、`locator`、`quote`、`availability`；`locator.type` 为 `slide/page/heading/docx_block`。后续 M1 必须验证 quote 属于对应 chunk，M2/M3/M4 只能消费校验后的对象。

处理任务状态为 `QUEUED → RUNNING → SUCCEEDED/FAILED/CANCELLED`。文档版本的 `parse_status`、`preview_status`、`index_status` 必须分开保存。

## 模块边界

| 模块 | 目录/表的所有权 | 对外依赖 |
|---|---|---|
| M1 MaterialHub | `services/materials`、解析器、文档/版本/chunk/asset/job | 共享认证、课程、Citation |
| M2 AI Study | `ai`、`services/ai`、StudyReport/AIResult | M1 只读 Citation/ChunkRef |
| M3 NoteGraph | `services/notes`、笔记/双链/引用 | M1 Citation；M2 可审阅草稿 |
| M4 ExamPilot | `services/exams`、真题/Topic/试卷/复习 | M1 来源；M2 题目草稿；M3 回源 |

## 2026-10-13 共享集成切片

- HTTP 错误的 `error.request_id` 与 `X-Request-ID` 响应头相同；未匹配路由也使用统一错误对象。结构化 HTTPException.detail 保存在 details，校验错误须可 JSON 序列化。
- 前端按 features/materials、ai、notes、exams 拆分；共享展示组件位于 components，App 仅维护会话、课程选择和导航。课程切换重新挂载业务工作区，防止旧草稿误存进新课程。
- 蓝图表单从题数与每题分值计算总分，不改变现有 API schema。本轮无数据库字段变更。

## NoteGraph 工作台增量（2026-10-13）

对应 FR-10–14：复用现有笔记 CRUD/backlinks；新增 GET /notes/{id}/export 返回 text/markdown 附件（正文原样保留，含标题，不打包图片）。更新用 id/user_id/revision/deleted 联合条件执行原子 UPDATE；冲突 409.details 返回 server_revision/server_title/server_content。前端自动保存约 2 秒，冲突暂停自动保存并保留本地草稿；用户可显式载入服务端版本。没有数据库字段变更。

## 2026-10-13 工作台导航与查找契约

共享层新增课程内查找页，复用 GET /courses/{id}/search 和 GET /notes?course_id；搜索结果使用现有 document_id/version_id/chunk_id，不按文件名猜定位。M1 接收 initialTarget（documentId/versionId/chunkId），按指定版本读取并定位；M3 接收 initialNoteId，仅从本课程列表定位并重新读取。所有跳转沿用未保存笔记保护。无数据库和 HTTP API 变更；前端补全现有搜索响应类型。查找页的资料与笔记结果分组，不混合评分。

## 队长 M1 可靠资料闭环（2026-10-13）

需求：FR-03–09/13/16/36，NFR-06/07/10。输入为当前用户课程的四格式文件；输出为不可变版本、定位切片、独立解析/索引/预览状态、持久任务。允许修改共享 DB/迁移、M1 models/schemas/repositories/services/routers/workers/tests、前端资料与公共 API；M2/M3 只经有效来源 repository 接入。M4 内部出题/作答表本切片不改。

- DocumentVersion 新增原件名称/MIME/字节/hash、preview_path/preview_error、tokenizer_version；历史版本元数据回填，引用 chunk 不因新版本重建。
- ProcessingJob 新增 attempt_count/max_attempts、lease_until/lease_token。SQLite 条件 UPDATE 领取、过期租约重排；PARSE 完成后入队 INDEX/PREVIEW；worker 独立进程，API 只入队。失败由用户显式 retry，达到最多 3 次需调整资料或人工排查，不能通过重复上传相同内容重置上限。
- POST /documents/{id}/versions 新版上传；POST /jobs/{id}/retry；GET /versions/{id}/preview（PDF）；GET /courses/{id}/jobs；GET /courses/{id}/search 改为 FTS5 关键词 BM25；稳定中文相邻二字 token v1，与原文偏移完全分离。
- 共享 active_version/checked_chunk 验证归属、课程、未删除、版本、摘录，供 M2/M3 使用。资料删除撤销原件/预览/切片/检索及新引用资格，保留 Citation 元数据并标 unavailable。
- Alembic 冻结初始 schema + M1 增量 revision；旧无版本库只在初始列校验通过后接管，迁移前 SQLite backup；不使用任意最新模型 create_all 代替历史迁移。

M1→M3：新增 GET /versions/{id} 返回授权版本身份。NoteCreate 可选 citations（最多 50 条），所有摘录预校验后与笔记同事务写入，保证 AI 草稿不丢结构化引用。前端笔记来源卡及 AI 引用都通过授权版本 API 回到 M1 指定片段。原件/预览使用 Bearer 请求获取 Blob，URL 不携带令牌。

图片边界：M1 负责实际图片解码校验、课程图片列表、受控读取/删除与引用查询；M3 根据 `![[asset:UUID|说明]]` 同步 AssetReference。客户端 MIME 不作为真实类型依据，限制 10 MiB/2000 万像素、单帧、PNG/JPEG/WebP；图片删除保留笔记正文并让资源读取失效。

M4 辅助集成范围（无表结构变更）：蓝图题型项由 schema 验证非负整数数量、正整数分值与已支持题型；章节数量合计必须等于总题数。作答验证题目归属该卷、选项/判断值是否合法、截止按 attempt.created_at + 蓝图时长计算；进行中的作答不能通过 include_answers 参数读取答案。提交后答案由单独结果接口读取。默认复习日期按 User.timezone 计算。此辅助不将 Mock 演示出题视为完整双来源生成或历史统计验收。
## 2026-10-13 M1 资料整理与引用导航契约（实现切片 M1-ORGANIZE-01）

需求：FR-07/09/13、NFR-06/09/10。输入为当前用户课程、有效 Document/Version 与整理字段；输出为资料元数据、带版本来源的筛选命中、当前版本的引用笔记。主责 zhy，共享/M1；M3 只增加只读引用查询 service interface，不修改笔记表/正文；M2/M4 内部实现不变。

- 迁移 0004：Document 新增 category（≤40 字，默认“未分类”）、tags（JSON 字符串列表，最多 12 个、每项 1–32 字，去重）；不改变不可变 DocumentVersion、Chunk 或 Citation。列表/版本响应补充 UTC created_at/updated_at 及版本文件 metadata，供排序/版本详情使用。
- PATCH /documents/{id} 仅接受 name/category/tags，拒绝未知字段、空名称、null 和超预算标签；部分字段更新，不覆写未提交字段。重命名只改变展示名，所有旧引用身份与原文件名不变；已删除/非所有者 404。
- GET /courses/{id}/documents 可按 category/tag 筛选；GET /courses/{id}/search 增加 category/tag、latest_only（默认 false 保持兼容）；过滤在服务端按所有者/课程/有效状态执行，latest_only 只取最高版本号，即使该版本仍在索引中也不退回旧版本。SQLite JSON 标签检索保持精确匹配，不使用字符串包含。
- GET /versions/{id}/references?chunk_id=… 输出 note_id/note_title/citation_id/chunk_id/quote/locator；仅当前用户未删除笔记与有效引用，按引用更新时间排序。指定 chunk 不属于该版本返回 404。由 M3 的只读 service 提供查询，M1 路由不直接读 M3 表。
- 前端引用笔记跳转消费既有 onNote；公共 SVG 图标、按钮/状态反馈、悬浮与焦点样式沿用全站基础；动效在 prefers-reduced-motion 下关闭。新增整理面板留存未保存草稿，不由后台任务轮询覆盖。

受影响消费方：M1 列表/阅读、课程查找、M3 笔记入口；交接 ID H-20261013-ZHY-003（已实现、待接收），接收/复验由成员本人填写。无新增 P1/P2 范围。

## 2026-10-14 M1-PREVIEW-ASSET-01 契约变更意图

需求 FR-06/07/08/37、NFR-06/09/10；输入为已授权版本 PDF 预览和当前页截图，输出为带不可变版本与确定预览页号的 Asset。M1 拥有 Asset；现有定义位于 models/notes.py，本轮只改 Asset 字段及图片 HTTP 入口，不改 Note/Link/Citation/AssetReference 表和 M2/M4 内部。

- 0005：Asset 增加 nullable source_version_id 外键、source_page（1-based 预览 PDF 页）、source_locator_type（page/slide/preview_page）。外部上传默认无来源；来源绑定与文件内容创建后不修改，防止静默回源到新版。DOCX 只标 preview_page，不映射为正文 block。
- POST /courses/{id}/assets 保留既有 alt query 与文件上传，新增成对 source_version_id/source_page；服务端校验所有者、课程、有效版本、预览就绪、实际 PDF 页数和图片解码预算，非法来源不写记录/文件。来源类型由原文件格式推导，不接受客户端任意定位类型。此记录表示用户在该页保存的图片，不作为服务器核实像素与原页完全一致的证明。
- GET /assets/{id}/metadata 输出归属过滤的源文档 ID/最新展示名/版本号/页号/定位类型及可用性；现有列表响应追加来源字段。原件/预览/图片均走 Bearer Blob，不在 URL 放 token；来源文档删除或课程删除后，衍生截图也撤销读取/检索资格，保留引用失效行为。
- PDF.js 使用安装包内 worker、字体和 CMap；不加载远程 CDN。页级阅读包含页码输入/前后页/缩放/渲染失败与原件下载降级；仅成功渲染且匹配当前版本/页时可保存截图，页面切换取消过期渲染。截图像素预算受限，不宣称 OCR/原文已识别。
- 图片回源消费 M1 前端导航 (documentId/versionId/previewPage)，M3 图片语法和保存方式保持兼容。既有普通图片仍可读取，未关联来源显示“外部图片”。共享界面沿用 Icon/按钮/面板，减少动效与窄屏适配保留。

交接 H-20261014-ZHY-001；受影响 M3 图片消费方，M2/M4 仅需了解新的只读源图片契约。实现和验收结果后续追加。

## 2026-10-14 M1-TRANSCRIPT-01 契约变更意图

范围 FR-04/07/08/09/13 与扫描真题 FR-39/40 的 M1 来源依赖，NFR-06/10。输入为当前用户 PDF 版本/实际页号/人工文本；输出独立草稿、确认记录和可引用 Chunk。只改共享来源/M1 与 M2/M3 来源消费适配，不修改 M4 拆题/统计，不改变笔记正文。

- 0006 新建 ManualTranscript（user/version/page/text/hash/revision/status/supersedes_id/confirmed_by/confirmed_at/chunk_id），给 Chunk 和 Citation 追加 source_kind，默认 extracted；旧版本/切片/引用 UUID 不变。page 为原 PDF 页，文本 Unicode 字符偏移 [0,len(text)) 针对转录，不冒充文件提取偏移。
- POST /versions/{id}/transcripts 创建 DRAFT；PATCH /transcripts/{id} 仅修改草稿文字，用 revision 乐观锁；POST /transcripts/{id}/confirm 显式确认、记录当前用户与 UTC、原子创建人工 Chunk 和 FTS 索引。仅真实 PDF 且预览就绪、页号确实存在时可建/确认；限制每条 20000 字、每版本 500 条、总 200 万字。未知/未确认内容不进入检索/引用。
- 确认内容不可变；修订创建独立 DRAFT，supersedes_id 指向同版本/页当前已确认记录。确认新版将旧记录标 SUPERSEDED，但旧 Chunk/旧引用仍保持原文。一次只能有一个当前确认版本；并发确认冲突返回 409，不静默合并。
- POST /transcripts/{id}/withdraw 标 WITHDRAWN，保留记录、撤销其新引用/检索与已存 Citation 可用性；不自动回退旧修订。GET /versions/{id}/transcripts 提供本人草稿/当前/历史列表；来源资料删除后所有接口 404。
- 阅读与搜索返回 source_kind=manual_transcript、transcript_id/status/确认时间；Citation 保存真实 source_kind。人工 Chunk 的可检索资格独立于原 PDF 解析失败状态；确认不会把扫描件 parse/index 伪改为成功。worker 的解析只处理提取正文，索引重建保留人工来源，不能删人工正文；共享检索与 M2 上下文只选当前确认补录，旧引用依然可回源至历史正文。
- PDF 阅读增加“补录本页文字”，草稿管理/明确确认、历史修订、撤回及冲突保护；全部控件沿用公共样式。PDF.js 图像用于对照，未实现 OCR；人工文本不自动进入远程模型。

交接 H-20261014-ZHY-002，受影响 M3 Citation 和 M2 上下文；实现/测试与成员接收另记。

## 2026-10-14 M1-ASSET-ORGANIZE-01 契约变更意图

需求 FR-37 的改名/说明/标签与 FR-09 的 M1 图片整理支持，NFR-06/07/10。输入为本人课程图片与展示元数据；输出可筛选分页的图片目录及冲突反馈。只修改 M1 Asset、图片服务/API/界面、共享迁移和类型；M3 笔记正文/引用表、M2/M4 内部不改。

- 0007 追加 Asset.name（≤255 字）、tags（最多12个、每项1–32字）、revision（初始1）；旧图片以 original_filename 回填展示名，tags=[]，不重建图片/引用表。alt 保持既有图片说明（≤500字）。UUID、原始文件名/hash/字节/来源版本页号不修改。
- PATCH /assets/{id} 接收 revision 与 name/alt/tags 的部分更新，拒绝未知/空补丁/null/非法标签。同所有者、有效来源、未删除及 revision 条件原子更新；冲突409.details.server_asset 返回最新元数据，前端保留本地输入并显式加载服务器版本，不能自动覆写。
- GET /courses/{id}/assets/page 返回 items/total/offset/limit/tags；limit 1–48、offset 0–100000，默认12。q（≤200字）是名称/原文件名/说明/标签的字面包含查找；tag 精确匹配；origin 为 all/captured/external；sort 为 newest/oldest/updated/name。过滤/计数/标签候选均只包含当前账户课程有效资源，来源删除的截图不纳入分页与计数，稳定排序以UUID打破平局。标签候选取当前课程全部有效图片，最多200个；不检索图中文字，不声称语义检索。现有 GET /courses/{id}/assets 保持数组响应，供 M3 插入图片兼容消费。
- 前端图片库提供搜索/标签/来源/排序/分页，图片整理草稿和409恢复、引用位置跳转。沿用公共图标/样式/焦点/减少动效；跨课程或离开页面的未保存整理草稿纳入现有导航保护。

交接 H-20261014-ZHY-003，受影响 M3 图片消费者只需兼容新增字段；插入图片下拉框显示新名称，插入仍使用原 UUID。此处仅适配来源展示，不改笔记保存业务。人工接收与最终验收待填。

## 2026-10-14 M1-JOB-CONTROL-01 契约变更意图

FR-05/09、NFR-06/07/10，输入本人有效资料版本/任务，输出明确的取消、恢复与重建状态。只修改共享M1任务服务/worker/接口/测试及资料界面，不修改M2–M4业务表/正文，无数据库新增字段。

- POST /jobs/{id}/cancel：仅PARSE/INDEX/PREVIEW的QUEUED/RUNNING可取消，200 CANCELLED；重复取消返回原记录，已成功/失败409。清除租约、对应版本状态CANCELLED；取消未完成解析时，尚未创建的索引/预览标CANCELLED。已保存原件/切片/引用不删除。子进程可在60秒预算内结束，但取消后的结果不写回；不声称立即杀死子进程。
- POST /jobs/{id}/retry：支持FAILED/CANCELLED，保留原任务和已消费尝试次数，最多3次；重复请求遇到已QUEUED/RUNNING返回同一记录；同版本/类型有其他活跃任务409。恢复解析时未创建的依赖状态回PENDING，解析完成再排依赖；失败/取消的依赖不会自动换新任务重置预算。
- POST /versions/{id}/reindex：202，输入 `{request_id:<UUID>}`，同请求重复返回同一INDEX任务；不同请求已有活跃INDEX时409并返回active_job_id，避免重试丢失响应后创建第二任务。只有成功提取正文或当前确认人工来源可重建；失败/取消INDEX需先恢复原任务，不能重置其上限。成功旧任务后可显式新建重建记录，原Chunk/来源/原件不变。工作区FTS重建同事务完成，失败回滚，不删除旧引用；原PDF解析状态不被人工来源伪改。
- 版本锁和任务租约条件写串行化取消/恢复/重建/领取；旧租约完成和索引异常路径都必须先条件写，避免取消被迟到结果覆写。预览输出每次独立文件，丢失租约后清理本次未挂载输出，不能覆盖其他尝试的PDF。
- 前端显示独立任务状态、取消后恢复、重试预算和选中版本的索引重建；明确“取消停止结果写入，后台处理可能稍后结束”。沿用公共图标/控件。资料/任务分页仍是后续切片，不在本轮宣称完成。

交接 H-20261014-ZHY-004，xtc/fzk/gcx只消费既有来源状态；接收与最终验收按实际填写。

Safari局部视觉检查发现原生下拉框未采用既有字段尺寸/圆角；共享CSS关闭单选框原生appearance并使用自制SVG箭头，保留原生select语义/键盘操作和多选框行为，各模块沿用同一规则，无新增资源依赖。

## 2026-10-14 M1-EXPORT-01 契约变更意图

FR-14/15/37的M1文件/来源导出依赖、NFR-06/07/10。输入本人课程，输出可校验课程资料ZIP；本轮只交付M1资料包，不含笔记/AI/考试/作答，不是完整个人备份，不支持恢复。M2–M4只消费既有来源契约，无其业务表修改。

- 0008新MaterialExport：Owned UUID/UTC、course_id、job_id、zip_path/sha256/size_bytes、sources_json/counts_json、snapshot_at；请求UUID作为导出ID，ProcessingJob type=MATERIAL_EXPORT。仅后台worker生成，120秒/256MiB内容/16MiB元数据/50000切片预算，ZIP流式写入临时文件。失败可原任务重试，最多3次，租约过期恢复；不写半个成功包。
- POST /courses/{id}/material-exports `{request_id:UUID}`→202 ExportResponse，重复请求返回同记录；不同请求已有活跃导出409，单课程最多20条记录（删除后可再次生成）。GET同路径列最近20条；GET /material-exports/{id}、POST /material-exports/{id}/retry、GET /material-exports/{id}/download、DELETE /material-exports/{id}。
- worker在一致SQLite读快照中选本人未删除资料/全部版本、成功提取Chunk、CONFIRMED/SUPERSEDED人工来源与有效课程图片；包含原件、可用预览、来源JSON和UTF-8文本。DRAFT/WITHDRAWN补录、被删/越权资源排除；截图仍指旧版本。路径使用UUID/固定目录，源路径必须在本人课程存储根内；文件大小/hash与版本或Asset记录匹配，否则失败。不复制FTS/数据库/密钥/服务端路径。
- manifest.json含format=hustudy-material-package/schema_version=1/课程/资料/版本/片段/确认补录/图片元数据/每文件路径+sha256+字节；README.md明确范围与校验。快照时间与来源UUID保留，仅供阅读/后续模块导出契约，不宣称可回灌全部学习记录。
- 完成时只认可原租约及仍存在的导出/课程；失败/租约失效清理本次临时产物。删除课程/导出取消关联任务并撤销下载。下载检查所有快照来源仍有效：包内资料/图片删除或人工来源撤回→不可用；改名或补新版本不改变旧包；校验ZIP文件hash，损坏409。已下载的本地副本无法撤销。
- 前端资料页增加“课程资料包”，显示范围、预算、排队/处理/失败/重试/下载/hash/删除与后台轮询，沿用统一控件；Blob下载只携带Bearer。导出不自动发送模型或外部服务。

交接H-20261014-ZHY-005，通知各模块M1来源文件清单可用；完整账户备份/恢复和M3知识库ZIP继续待办，不把本切片当父需求Done。补充资源边界：最多70000个ZIP成员，数据库先计算原件/正文UTF-8字节预算，再加载正文，避免先把超预算正文全部载入内存。

移除导出记录与完成写回串行化；仅取消QUEUED/RUNNING任务，已SUCCEEDED/FAILED任务保留真实历史终态，资源移除仍使资料包接口404。最终风险测试补此终态保持，避免把成功生成历史改成“取消”。
## 2026-10-14：共享课程整理契约 PLATFORM-COURSE-01（FR-02/09，A02）

本切片输入本人 Course，输出整理元数据与过滤后的课程列表；不读取/修改 M2–M4 内部表。新增 Course.category（≤64字，默认未分类）、tags（最多12个、各32字、去重）、revision（初始1）。0009仅追加列，不改变 UUID/课程关系/资料版本/引用。历史课程使用默认值。

POST /courses 可带 category/tags；name 去首尾空白且不能为空，description 空白归一为 null。GET /courses 保留数组契约，新增 q（≤200，名称/描述/分类/标签字面查找）、category/tag 精确过滤及 sort=newest/updated/name；始终按 user_id 过滤。分类/标签属于课程，资料自己的分类/标签独立，不自动传播。

PATCH /courses/{id} 改为真正局部更新：必须提交 revision 与至少一个整理字段；只更改已提交字段，description:null 清空描述、tags:[] 清空标签，name/category/tags:null 拒绝。原子条件更新并增加 revision，旧版本返回409.details.server_course；越权404。旧改名调用方须先读 revision 再提交，前端本轮同步适配。冲突不静默覆盖，本地草稿保留，用户可显式加载服务端内容或确认以本地草稿再次保存。

课程首页统一卡片/分类与标签筛选/整理对话框，编辑时阻止意外离开。课程删除及关联对象撤销的完整跨模块验收不在本切片，不据此将 FR-02 父需求标完成。交接 H-20261014-ZHY-006 待本人接收。

## 2026-10-14：课程删除与基础验收 PLATFORM-COURSE-DELETE-01（FR-02，TC-01/23）

共享课程新增deleted_at（UTC，可空）；0010只追加列，历史课程默认有效。课程删除是逻辑撤销，没有产品恢复入口，不宣称为完整备份或物理擦除。保留Course/Document/Version/Chunk身份用于有效笔记的失效来源；所有课程查询/写入只接受deleted_at为空的本人课程。

新增GET /courses/{id}/deletion-preview返回当前Course及影响数量：M1资料/版本/有效图片/资料包、M3有效笔记、M2结果、M4真题/模拟卷/作答/关联复习。数量是预览时快照，删除针对整门课程而不是固定ID子集。DELETE /courses/{id}?revision=N必须提供当前revision，旧revision409、不可访问404、成功204；旧DELETE调用方同步补revision。UI展示影响与无恢复入口，输入当前课程名确认。

同一事务锁定Course并校验revision，通过模块服务接口清理：M1标记资料/图片不可用、取消关联QUEUED/RUNNING任务并清租约、撤销检索；M3软删除课程笔记、标记Citation不可用（保留外部笔记正文/引用元数据/双链）；M2清理课程AI结果；M4先删除关联复习任务再清理课程真题/试卷/蓝图/考点与级联作答/错题。独立复习任务、其他课程与账户不变。模块失败全事务回滚，迟到worker不写回。终态任务保留历史，关联资源读接口撤权。

先通过本条与handoff007通知xtc/fzk/gcx，待本人评审/接收。共享协调器不直接操作M2–M4内部表，各模块提供count/retire服务；不重写生成/评分/笔记编辑。隔离测试数据库与自制样例验收，不删除已有用户课程。

## 2026-10-14 M2-ZHIPU-QA-01：智谱真实课程问答

用户明确选择智谱GLM-4.7-Flash并提供后端密钥。接口核对官方模型/对话补全/结构化输出文档；使用https://open.bigmodel.cn/api/paas/v4/chat/completions、model=glm-4.7-flash、Bearer、非流式JSON、thinking disabled。密钥仅后端SecretStr/忽略的.env，不进入页面/库/日志；测试强制假密钥与MockTransport。普通阅读/笔记/检索/演示不依赖远程配置。

本轮只实现真实课程问答，不将教学报告或M4真题生成直接切为真实。M1提供有界只读上下文选择/验证接口，M2只消费同课程/本人有效版本及当前确认人工来源；关键词检索默认最新版本，允许显式限定版本或选中片段。最多6片段、每片段2000字、合计8000字，问句2000字。引用只能来自实际送出片段、摘录确实存在；grounded不表示语义正确或正确率。

新增RemoteQuery（0011）：本人课程、query、来源快照JSON、model、endpoint、过期UTC（15分钟）、consented_at/dispatched_at、job_id、result_id。预览不调用模型，确认只提交预览ID/确认布尔值，服务端保存的原问句/原文作为唯一输入，不接受前端重写片段。确认检查未过期/配置未变/原来源仍有效，旧来源409；同预览确认幂等。每课程最多20个待保留预览，限制一个活跃远程任务；完整结果持久化为AIResult、model_mode=real及待核实标记。

GET /ai/provider返回已配置标识/模型/目的地/官方链接与核对日期，不返回密钥。POST /courses/{id}/remote-queries/preview返回完整发送预览；POST /remote-queries/{id}/confirm只在明确确认后202入队AI_ANALYSIS；GET详情、POST取消。发送前在课程锁内重新核对快照并记录dispatch，网络等待不占SQLite写锁；取消/删除在派发前阻止调用，派发后仅撤销后续结果写入，已发出的请求无法召回。来源在请求中删除/撤回则不保存grounded结果。

持久worker统一租约180秒、HTTP读取45秒/总预算60秒、响应≤1MiB、输出≤2048tokens；结构严格schema/枚举/引用校验，坏JSON/假引用/鉴权/限流/超时明确provider_error，不展示供应商原错误体或思考内容；无自动网络重试/结构修复，失败或过期运行租约需重新预览确认，不能在无人确认时重复发送。

课程/资料删除通过生命周期接口取消相关AI任务并撤销读取；旧有效结果/草稿不因新调用失败而覆盖。资料发送确认展示实际片段与用户问题、目的地，模型接口文档已核对；保留期限/训练用途/远程删除政策未核实，明确标注而不作隐私承诺。交接H-20261014-ZHY-008通知xtc/fzk/gcx，待本人接收。M2开发在zhy集成会话完成，不冒记为成员本人贡献。

新增课程删除counts.remote_queries（预览/任务记录）；worker只领取resource_id对应本人RemoteQuery的AI_ANALYSIS，不接管未来其他分析资源。LLMProvider.answer接口固定为结构化结果与状态，ZhipuProvider实现；真实失败不自动切为本地演示。生成草稿时固定引用列表，后续新结果不改变已有草稿。

## 2026-10-15 PLATFORM-AUTH-02：标准JWT与会话失效反馈

正式A02/FR-01/NFR-06。保持注册/登录返回access_token/token_type/user、Bearer调用和用户UUID不变；密码hash及数据库不迁移。新访问令牌改为PyJWT生成的三段HS256 JWT，固定issuer=hustudy-local、audience=hustudy-api、token_use=access；必须有UUID sub/jti和整数iat/nbf/exp，严格检查签名、算法、用途、有效期及归属。拒绝旧两段令牌、none/其他算法、错误issuer/audience、畸形或过大令牌；401附WWW-Authenticate: Bearer。不保留旧格式兼容入口，升级后重新登录，已有课程/资料不变。

JWT签名密钥至少32字符且不使用已知开发占位；setup通过独立脚本初始化随机密钥，只替换空值/已知占位，保留现有有效密钥和GLM配置，忽略的.env权限0600。前端会话失效明确说明重新登录，不再无提示回到登录页；不记录或展示令牌/密钥。影响M1–M4所有授权调用，但无业务表/schema变化，成员通过统一依赖消费；交接010跟踪实施/验证，接收由成员本人填写。

## 2026-10-15 PLATFORM-STORAGE-01：统一文件写入与磁盘保护

正式A04/A05、FR-03/05/37与NFR-01/06/07。共享FileStorage接口及LocalFileStorage适配器，文档/图片采用同目录临时文件→原子发布，数据库提交失败清理；路径在配置根内，拒绝符号链接/越界/覆盖已有文件。归属校验仍由服务执行。

HUSTUDY_STORAGE_RESERVE_BYTES默认64MiB、最少1MiB。原件/图片写前预检字节数，解析/转换检查实际临时文件系统与预算，预览复制采用原子写入，导出预检估计空间并在成员写入前复查。空间不足HTTP507/error.code=INSUFFICIENT_STORAGE；任务明确失败可按原预算重试。预检后ENOSPC/EDQUOT仍捕获并清理未提交产物，既有原件/引用/数据库不覆盖。不是跨进程硬配额或实时空间预留，默认阈值不冒记为用户已确认容量目标。

无数据库迁移，不改变已有路径/UUID/下载URL；M2–M4业务不重写。交接010及验收记录跟踪验证。

## 2026-10-15 M1-BROWSE-01：资料与任务分页

保持旧documents/jobs数组接口兼容，新增GET /courses/{id}/documents/page与/jobs/page。统一items/total/offset/limit，offset≥0、limit1–100；过滤/排序在服务端执行，最后按永久UUID打破同值排序，课程/用户/删除资格在分页及计数前过滤。资料支持q字面子串、category/tag精确、state=all/ready/processing/failed、sort=recent/name/size，返回整课程分类/标签候选及total/ready/processing统计；任务支持status=all/pending/failed/cancelled/succeeded及type=all/PARSE/INDEX/PREVIEW，返回全部课程pending_count。过滤变化回第一页，越界空页回退；处理中的任务即使不在当前页仍触发轮询。

前端资料/处理记录独立分页，保留正在阅读版本和未保存整理草稿；分页外的引用跳转通过单资料GET授权读取，不误报“已删除”。新增上传/重复内容命中、图片回源同样不依赖当前列表页。无数据库迁移，不把本切片等同容量/性能目标已测。

## 2026-10-15 PLATFORM-BACKUP-01：账户快照与空账户恢复

FR-15/NFR-08/A03/A04/A10。共享层协调，各模块通过snapshot/validate/apply适配器导出和恢复自身表，不跨模块直接访问内部业务表。清单格式hustudy-account-v1，固定schema_revision；包含Course、M1资料/版本/正文/图片/人工来源/终态任务、M3笔记/双链/引用、M2结果/已保存发送记录、M4题目/试卷/作答/错题/复习/反馈。保留UUID/UTC/引用/文件hash；账户凭据、密钥、.env、临时文件不导出，用户身份恢复到当前登录账户，仅迁移时区。运行中任务须先完成/取消；恢复不派发模型。可重建课程资料ZIP缓存不复制，元数据保留并标不可下载；FTS重建。

0012新增account_archives，仅控制账户导出/恢复任务与本地文件，业务表不重建。POST /backups入队ACCOUNT_BACKUP；GET /backups及/{id}查看，GET /backups/{id}/download下载。POST /backups/restore接受file与confirm=RESTORE_EMPTY_ACCOUNT入队ACCOUNT_RESTORE；只允许当前账户无任何业务对象，不能覆盖已有数据；同UUID在数据库已有对象也拒绝，保持引用UUID意味着跨账户同库有源对象时不能原地复制，迁往新库/移除源数据后再恢复。并发恢复串行复查空账户，任何失败回滚全部业务写入并清理本次文件。已提交账户不因重试覆盖。

ZIP≤256MiB、解压内容≤512MiB、清单≤16MiB、成员≤70000、总业务行≤100000、处理≤120秒；拒绝路径穿越/符号链接/重复成员/额外文件/错误schema/hash/字段/外键/归属。文件路径在服务端重建，不信任清单绝对路径；删除来源保留失效元数据，不导出已撤权原件或正文。后台单次租约180秒，过期不自动重做恢复；用户可重新上传/发起新任务。取消已派发模型不在本流程内；任何备份/恢复不会绕过逐次发送确认。

备份下载重新核对所含M1文件来源资格，删除后旧服务端包不可下载；已下载本地副本不能撤销。恢复仅校验结构/引用关系/字节完整性，不证明备份真实性或AI内容语义正确。实现/迁移/往返/损坏/权限证据在zhy共享层验收与handoff追加，其他成员接收由本人填写。

补充：最多50条控制记录，DELETE /backups/{id}仅移除终态记录/其ZIP，不删除恢复后的业务对象；运行中409。最后一次数据库commit故障、过期不重放和真实文件字节/假Citation已加入隔离验收。

## 2026-10-15 PLATFORM-WEB-BASE-01：路由/请求管理/原账户重新登录

对齐既定React Router、TanStack Query、Ant Design基线，沿用现有公共CSS/图标风格。URL保存页面、课程与可选note/document/version/chunk定位，刷新/前后退可恢复；路由器统一执行未保存导航保护，URL中的UUID不替代服务端归属检查。部署BrowserRouter须SPA回退，开发/预览由Vite处理。

统一JSON GET通过QueryClient按访问会话分区，参数不同独立缓存，重叠读取去重；staleTime=0保持每次读取的服务端授权，无持久缓存，退出清空。POST等变更不自动重试，成功递增该会话查询代次并使旧数据失效，写后刷新不合并到写前仍在途的旧列表；文件下载保持不缓存。query key不含原始令牌。

401弹出同一原账户重新登录对话框，保留当前页面和内存中的未保存内容；成功后刷新授权与列表，不重新初始化原编辑草稿。不能把旧账户草稿带到另一账户，切换账户需显式退出/放弃导航保护。Ant Design以主题Provider/Alert/Modal接入，保留原布局，不卡通拼接多套风格；不加载外部字体/CDN。无数据库/API破坏性变更，真实模型仍逐次确认且不重发。

## 2026-10-15 M1-PREVIEW-RECOVERY-01：可诊断与恢复的PDF预览

本切片优先修复用户当前PPTX预览被禁用的问题，对应FR-05/06/36/37、A04/A07/A10。输入为本人有效版本与本机Office转换器，输出为原始PDF或隔离转换PDF、独立预览任务与明确恢复入口。仅修改M1/共享配置/公共前端API及对应测试文档，不修改M2/M3/M4业务算法。

新增GET /material-capabilities（需登录），返回原生PDF可用、Office转换器是否可执行、说明与官方安装文档链接，不返回本机路径或密钥。后端可选HUSTUDY_LIBREOFFICE_PATH指定可执行程序，默认PATH和macOS标准目录发现；程序只作为argv执行，不经shell。解析/预览仍由worker隔离、转换60秒、独立profile、输出PDF校验/资源预算；转换错误映射为可理解原因而非原始进程stderr。

新增POST /versions/{id}/preview-jobs作为显式恢复命令，不接收客户端任务ID。检查归属/有效版本、格式PDF/PPTX/DOCX，原生PDF不依赖转换器。已有成功可用预览返回409说明可直接打开；活跃同类型任务返回202已有任务；失败/取消已有任务使用原记录重试、保留尝试上限，修复后显式重试，不绕过预算。无可用转换器时拒绝新Office任务并说明先修复环境，不把重复点击作为修复。

前端将原件格式和“转换为PDF”与原生PDF区分，显示缺依赖/失败/处理中/纯文本状态。修复环境后可从当前阅读区直接重试，不需重新上传；预览下载失败/渲染错误保留正文、原件入口和重试。前端实际PDF双页/截图回源与Office成功或明确降级纳入Playwright，不以Node PDF渲染代替浏览器验收。无数据库迁移。


预览后续校正：PDF.js显示层与worker统一采用同版本legacy兼容构建，覆盖本机Safari缺少Map.getOrInsertComputed的实际错误。PPTX转换显式ExportHiddenSlides=true，生成后核对PDF页数与原幻灯片数；不一致不发布。读取/截图拒绝旧错位缓存；无截图时可显式重建，有既存截图时拒绝静默重定向并要求人工核对。只变更可重建预览，不改版本原件或chunk引用。

## M1-SEARCH-02：分页知识查找与容量验收（2026-10-15，实施契约）

队长 zhy 会话辅助；FR-09、NFR-01/02、TC-06/21/23。现有数组搜索保留（最多50条供现有AI检索消费），新增 `GET /courses/{id}/search/page?q=&offset=0&limit=12`，返回 `items/total/offset/limit`，沿用分类、标签、latest_only与BM25排序，平分按chunk UUID。所有分页参数服务端校验，limit≤100；空/无有效词返回空页，超过100个去重token拒绝而非静默丢词。每页由同一SQLite读快照计数/读取，翻页间资料变化可改变结果，非冻结快照。

M3提供只读 `services/note_search.py.search_notes` 适配器及 `GET /courses/{id}/note-search`，参数q/offset/limit同上，按题名或正文包含完整关键词查找，更新时间降序、UUID作平分。返回id/title/excerpt/updated_at，不下载全部笔记正文。仅本人、当前有效课程、未删除笔记；无schema/迁移，不改变M3编辑、标签与导出实现；不是笔记FTS或语义搜索。M1前端组合两接口，两类结果独立分页；资料分类/标签只约束资料。摘录纯文本，由React文本节点高亮，不能作为Citation原文偏移。

容量检查使用隔离库、自制资料和独立进程；记录硬件/解释器、样本规模、缓存条件、4并发/每端点100次、p95计算方法与实际数值。首次请求单列，不冒称清空操作系统磁盘缓存。服务端性能通过不等于浏览器、远程模型或人工可用性验收。受影响xtc（旧search_chunks调用保留）、fzk（只读适配器）、gcx（来源identity不变）；待成员本人接收。

M1-SEARCH-02补充解析完整性：PPTX中组合/嵌套组合的文本及表格按形状树顺序展开，仍以原幻灯片序号定位；图片内文字不做OCR。此修复不改变现存不可变版本/chunk，重新导入为新版本后生效。增加自制嵌套形状与表格测试，防止“解析成功但组合文字丢失”。

## M1-NATIVE-PREVIEW-01：按源格式直接预览（2026-10-15）

用户明确要求PPT/PDF/Word原格式阅读，覆盖此前“Office只转PDF”的产品入口约定。首版范围为.pptx/.pdf/.docx，旧二进制.ppt/.doc需另存为对应OOXML；不新增在线编辑、动画/宏/多人服务。PPTX与DOCX从现有授权original接口取得原件，在本地浏览器解析与渲染；PDF仍用PDF.js直接读取原PDF。无需Office转换成功即可打开原格式；转换PDF明确标“兼容预览”，正文视图与原件下载保留。

Office渲染运行于仅allow-scripts的隔离iframe，无same-origin/表单/导航/弹窗权限。父页面仅传ArrayBuffer与随机通道标识，不传token或用户身份；iframe CSP禁止连接及远程图片/字体/媒体/子框架，仅允许自身带nonce脚本、内联样式、本地data/blob图片字体。消息校验source/通道/类型/页码，卸载销毁iframe，旧结果不得写入新版本；渲染失败/超时可手动重试或改兼容PDF。不把原格式渲染结果写成新DocumentVersion或修改Citation。

PPTX分页仍对应原幻灯片序号，包含隐藏页；DOCX浏览器排版页仅是阅读页，不能代替docx_block引用。已有截图仍由PDF兼容页捕获与服务器验证；原格式视图不冒用PDF截图来源。原格式阅读提供前后页、跳页、缩放、PPT演示模式、回文本及原件下载。复杂Office排版/字体/图表/动画存在兼容边界，不能称完整PowerPoint/Word替代。

只改M1前端/公共构建与配置、契约和风险测试，无数据迁移。第三方先核对发布版本、许可证及捆绑声明，再固定锁文件/保留许可。受影响xtc/fzk/gcx仍消费既有UUID/Citation，不需改数据库，待本人接收。

## PLATFORM-RESPONSIVE-01：统一密度与多屏布局（2026-10-15）

用户要求全站适配电脑、iPad、手机，缩小界面字号并优化模块排布。输入为既有路由、课程与模块组件；输出为统一的字号/间距层级、桌面固定导航、窄屏原生模态抽屉和自适应网格。对应 NFR-09/10 及 FR-06/10/17/25 的界面交互；自动布局检查不能代替 TC-24 真实用户试用。

仅修改前端共享壳层、响应式样式、必要的展示容器和浏览器测试；M2–M4 展示层使用公共规则，不改变模块算法、数据表、API、状态机或引用契约。抽屉遵守现有未保存草稿离开确认，导航成功才关闭；支持 Escape、焦点恢复、滚动与屏幕旋转。窄屏允许表格/代码/文档画布在容器内滚动，不能让整个页面横向溢出。触控操作保留足够热区，手机表单避免 iOS 聚焦缩放；阅读字号控制及 Office 源文件排版独立于界面字号。桌面/平板/手机采用浏览器尺寸模拟验收，实机与真人反馈另列待验。

## PLATFORM-VISUAL-02：统一视觉层级与交互状态（2026-10-15）

用户继续要求前端美观、配色协调、文字与按钮适中。输入为现有响应式工作台和真实业务状态，输出为统一主色/文本/边框/焦点/语义状态、清晰的当前工作区标识、侧栏账户、带功能语义的空状态和一致的图标/表单层级。沿用13px界面与20–26px页面标题、44px触控热区；提升过浅/过小元数据的可读性，不继续整体缩字，不更改原格式文档排版。

范围为共享前端组件、responsive.css、登录/帮助、M1–M4必要的展示标签/图标和浏览器验收；无API/schema/迁移/模块算法变更、无新依赖/外部资源请求。导航与草稿保护/远程发送确认保持现有契约；颜色配合文字与图标，不用颜色单独表达成功/失败。真实需求状态决定提示，不能用美化伪造进度或用户成果。验收检查多屏布局、键盘/减少动效、关键文本/按钮/状态配色对比及既有闭环；不能据此宣称全站无障碍认证或真实用户满意度。
