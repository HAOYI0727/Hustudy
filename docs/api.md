# Hustudy API（Phase 0）

服务默认运行在 `http://127.0.0.1:8000`，OpenAPI 地址为 `/docs`。

| 方法 | 路径 | 说明 | 状态 |
|---|---|---|---|
| GET | `/health` | 数据库和服务健康检查 | 已实现 |
| POST | `/api/v1/auth/register` | 注册并返回 bearer token | 已实现 |
| POST | `/api/v1/auth/login` | 登录并返回 bearer token | 已实现 |
| GET | `/api/v1/auth/me` | 查询当前用户 | 已实现 |
| GET/POST | `/api/v1/courses` | 当前用户课程列表/创建 | 已实现 |
| PATCH/DELETE | `/api/v1/courses/{course_id}` | 当前用户课程更新/删除 | 已实现 |

认证使用 `Authorization: Bearer <access_token>`。错误响应按 `docs/contracts.md` 的 `error.code/message/details/request_id` 形态返回。资料、笔记、AI、真题和考试 API 将在对应阶段追加。

## 当前 P0 可运行接口（2026-10-09）

以下接口已接入 FastAPI，并由前端工作台调用：

| 模块 | 已覆盖接口 |
|---|---|
| 资料 | `POST /api/v1/courses/{id}/documents`、`GET /courses/{id}/documents`、`GET /documents/{id}/versions`、`GET /versions/{id}/chunks`、`GET /courses/{id}/search`、`GET /jobs/{id}`、`GET /versions/{id}/original`、`DELETE /documents/{id}` |
| 笔记与图片 | `GET/POST/PATCH/DELETE /notes`、`GET /notes/{id}/backlinks`、`GET /notes/{id}/citations`、`POST /assets`、`GET /assets/{id}` |
| AI | `POST /courses/{id}/ai-queries`、`GET /ai-results/{id}`、`POST /versions/{id}/study-reports` |
| 真题与试卷 | 课程考点、真题导入/拆题/确认、蓝图、试卷生成/审阅、作答保存/提交 |
| 复习 | `GET /mistakes`、`GET/POST /review-tasks`、`POST /review-tasks/{id}/complete`、`POST /feedback` |

演示模型固定标记为 `demo`；真实 Provider 尚未配置。资料解析支持 Markdown/TXT，PDF/DOCX/PPTX 依赖安装后启用；扫描 PDF 会返回可观察的失败状态。

### NoteGraph 工作台增量（2026-10-13）

`GET /api/v1/notes/{id}/export`：归属检查后返回 UTF-8 Markdown 附件，包含标题及原始正文。当前是单笔记文本导出，不含图片文件和来源清单。

`PATCH /api/v1/notes/{id}`：通过 SQL 条件更新原子校验 revision。旧版本返回 409，`error.details` 包含 `server_title`、`server_content`、`server_revision`，客户端保留本地草稿；已删除或跨用户资源返回 404。

### 工作台查找消费约定（2026-10-13）

前端课程查找复用 GET /courses/{id}/search?q=… 与 GET /notes?course_id=…；搜索响应已有 document_id/version_id/chunk_id，跳转按三者定位。笔记在课程列表匹配后通过 GET /notes/{id} 重新载入。无新增 HTTP 接口；搜索当前最多 50 个片段，属于字符串匹配。

### MaterialHub 与跨模块来源契约（2026-10-13）

以下均使用 /api/v1 前缀和 Bearer 认证。上传返回 202 ProcessingJob，必须运行独立 worker；不再在请求生命周期直接解析。

| 方法 | 路径 | 行为 |
|---|---|---|
| POST | /documents/{id}/versions | 为现有资料导入不可变新版本；重复内容返回已有任务 |
| GET | /versions/{id} | 版本归属、资料身份、文件 metadata 与独立状态 |
| GET | /versions/{id}/preview | 授权 PDF；未完成/失败返回 409 含原因；删除后 404 |
| GET | /courses/{id}/jobs | 最近最多 100 个有效资料任务 |
| POST | /jobs/{id}/retry | 仅 FAILED 且尝试未达 3 次可入队（202）；其他情况 409 |
| GET/POST | /courses/{id}/assets | 图片列表/上传（PNG/JPEG/WebP，≤10 MiB，实际解码预算） |
| GET | /assets/{id}/references | 图片引用笔记，按所有者过滤 |
| DELETE | /assets/{id} | 标记不可用，正文保留，读取 404 |
| GET | /attempts/{id}/result | 仅提交后返回答案与解析，进行中 409；跨用户 404 |

版本响应补充 original_filename/mime_type/size_bytes/sha256、preview_error/tokenizer_version；任务补充 attempt_count/max_attempts。解析成功并索引成功才可搜索。课程 search 已替换旧字符串包含匹配为 FTS5（zh-bigram-v1）和 BM25，score 仅排序指标。

POST /notes 可带最多 50 个 citations，每个含 version_id/chunk_id/quote；服务端在同一事务验证有效版本、原文摘录和课程归属并创建笔记。非法来源不留下半成品笔记。旧版本引用保留，不静默指向新版本。资料删除撤销所有读取/检索与新模型上下文资格。

PUT /attempts/{id}/answers/{question_id} 验证试卷题目、选项与服务端时限。提交原子状态转移，重复提交返回已保存结果，不重复创建错题事件。include_answers=true 在当前用户仍有进行中考试时拒绝；考生界面使用独立结果接口。

### M1 资料整理与阅读关联（2026-10-13，M1-ORGANIZE-01）

- `PATCH /api/v1/documents/{id}`：部分更新 name/category/tags，返回 DocumentResponse（200）。例如 `{"name":"第2章复习","category":"核心章节","tags":["期末","数据通信"]}`。字段去首尾空格、标签精确去重；拒绝 null/未知字段/空名称、分类超过 40 字、标签超过 12 个或每项超过 32 字（422）。清空标签传 []；清除分类传“未分类”。非所有者/删除资料 404。版本/文件名/引用不改。
- `GET /api/v1/courses/{id}/documents?category=核心章节&tag=期末`：服务端按课程/归属/未删除/精确标签过滤；响应包含 category/tags 和带 UTC 时区的 created_at/updated_at。
- `GET /api/v1/courses/{id}/search?q=数据&category=核心章节&tag=期末&latest_only=true`：追加上述过滤及 version_no。latest_only 默认 false 兼容旧调用；前端查找默认只查最新，用户可包含历史。最新版本未完成解析/索引时不退回旧内容。score 是排序指标。
- `GET /api/v1/versions/{id}/references?chunk_id=<uuid>`：返回 citation_id/note_id/note_title/chunk_id/quote/locator_type/locator_value。仅当前用户未删除笔记和有效引用；改名读取最新笔记标题；指定片段不属该版本或非所有者均 404。前端按引用展示卡片，统计不同笔记数。
- `GET /api/v1/courses/{id}/jobs`：补充 document_id/document_name/version_no，使任务记录可读；VersionResponse 补充 UTC created_at/updated_at。上传返回结构及状态不变。

迁移 0004 加 category、tags 和分类索引，启动前执行升级，JSON1 可用性在迁移时验证。M1 原文→笔记查询消费 M3 只读 `services/note_references.py` 接口；无笔记/试卷表变更。测试见 `backend/tests/test_material_organization.py`，交接 [003](../collaboration/handoff.md#h-20261013-zhy-003)。

### M1 页级预览与截图来源（2026-10-14）

既有 GET /versions/{id}/preview 继续返回授权 PDF；前端改为本地 PDF.js 按页渲染、翻页/页码/缩放，成功渲染后可保存当前页图片。不会加载 PDF 附带的交互脚本，也不提供 OCR；正文选文仍使用文本阅读区。

POST /api/v1/courses/{id}/assets 保持原接口，新增 query source_version_id/source_page（成对提供，page 为 1-based 整数）；alt ≤500 字。校验有效版本属于当前用户/课程、预览已完成、页号在实际 PDF 页数内，然后验证图片实际类型/字节/解码预算。无来源图片返回 null 来源；失败不写文件/数据库。未就绪 409，越界/不成对 422，非归属/删除来源 404。

Asset 列表/上传响应新增 source_version_id/source_page/source_locator_type。类型由来源格式决定：PDF page，PPTX slide，DOCX preview_page；后者不等同 Word 页码/正文 block。来源与图片创建后不修改。浏览器提供的图片来源标记不是服务器对其像素真实性的鉴定。

GET /api/v1/assets/{id}/metadata 返回原 Asset 字段及 sha256、UTC created_at、source_document_id/source_document_name/source_version_no/source_availability。只有所有者可读；来源删除后 availability=unavailable，保留失效定位；文件 GET 404、课程资产列表排除。课程删除同时撤销普通图片/截图读取。GET 图片使用 Cache-Control: no-store；旧上传和 M3 UUID 嵌入保持兼容。

0005 新增来源外键与索引；SQLite 在真实事务中保留/恢复原图片引用，失败回滚。完整迁移与旧引用保留/中途故障测试见 test_migrations.py。图片入口移入 M1 routers/assets.py 和 services/assets.py；NoteGraph 保留其笔记和反链职责。

### M1 人工 PDF 补录来源（2026-10-14，M1-TRANSCRIPT-01）

全部使用 /api/v1、Bearer 与归属/有效版本检查。仅原始 PDF；DOCX/PPTX 预览不能用这套接口冒充原始页。

| 方法 / 路径 | 输入与返回 |
|---|---|
| GET /versions/{id}/transcripts | 该用户全部草稿/当前/历史/撤回记录，按页及创建时间排列 |
| POST /versions/{id}/transcripts | `{page:1,text:"人工文字",supersedes_id:null}`；201 DRAFT，未建立 Chunk |
| PATCH /transcripts/{id} | `{revision:1,text:"核对文字"}`；仅草稿可改，revision +1；旧 revision 409 |
| POST /transcripts/{id}/confirm | `{revision:2}`；200，确认人/UTC 时间/Chunk UUID；相同请求在未发生后续变更时返回同一结果 |
| POST /transcripts/{id}/withdraw | `{revision:3}`；200 WITHDRAWN，引用 unavailable，不回退旧版本 |

文本去首尾空白，1–20000 Unicode 字符；page 为严格正整数，版本最多 500 条记录、总文字 200 万字符。服务端检查 PDF 预览已就绪/实际页数；尚未就绪 409，类型/越界/文本/配额错误 422，跨用户或删除资料 404。草稿冲突 409.details 包含 server_text/server_revision/server_status；客户端保留本地文字。

确认正文不可变：以同版本/页当前确认记录 ID 创建独立修订，再确认；旧记录 SUPERSEDED/旧 Chunk/旧 Citation 均保留原文，检索与新模型上下文只取当前 CONFIRMED。新稿与旧当前记录冲突 409，草稿留存。WITHDRAWN 失去检索与新引用资格，已存引用标不可用；原文件/版本内容不改。

Chunk/Citation 追加 source_kind（extracted / manual_transcript）。阅读 Chunk 响应还包含 transcript_id/transcript_status/confirmed_at，检索含 transcript_id；转录原文偏移 [0,len(text)) 针对补录文字。DocumentResponse 新增当前最新版本 confirmed_transcript_count，原 parse/index 状态保持真实。M2 接入共享 indexable_source 条件，仅扩展来源消费，不新增真实 Provider；M3 只显示来源类型并保存真实 Citation 分类，不自动改笔记正文。

0006 新表/部分唯一索引/来源字段；原 UUID 保留。必须重启旧资料 worker 加载新的提取/人工来源区分；scripts/dev.sh/worker.sh 仍为启动入口。本轮已重启此前本会话启动的 worker，未终止用户另起的进程。

### M1 图片整理与分页查找（2026-10-14，M1-ASSET-ORGANIZE-01）

Asset 的上传、旧列表、metadata 响应追加 name/tags/revision/created_at/updated_at；旧数组列表仍兼容 M3。name 是展示名，original_filename 是不可变原文件名，alt 为说明。

- `PATCH /api/v1/assets/{id}`：如 `{ "revision":1, "name":"进程状态图", "alt":"第二章的状态转换示意", "tags":["第二章","重点"] }`。字段可部分提交，至少一个整理字段；name 去空白后1–255字，alt ≤500字可清空，tags 最多12项/每项1–32字、去空白去重。revision 严格正整数。未知字段、null、空补丁 422；非所有者/已删除/来源失效 404；过期 revision 409，`error.details.server_asset` 为最新完整 Asset，不能自动覆盖。
- `GET /api/v1/courses/{id}/assets/page?q=状态&tag=重点&origin=captured&sort=newest&offset=0&limit=12`：返回 `{items:[Asset],total,offset,limit,tags:["第二章","重点"]}`。q ≤200字，是名称/原文件名/说明/标签的字面包含，ASCII 大小写忽略，`%`/`_` 不作为通配符；tag 精确匹配。origin 为 all/captured/external，sort 为 newest/oldest/updated/name。limit 默认12、1–48，offset 默认0、0–100000；非法枚举/预算422。tags 为当前课程全部有效图片的去重候选（最多200），不随当前过滤减少。跨账户课程404。

所有查询/计数/标签候选与整理写入使用同一授权条件，来源资料删除的截图排除；改名不变 UUID/hash/文件/来源页或已存笔记正文。查找不读取图片内文字、不是 OCR/语义检索。0007 只追加列、旧展示名回填，迁移失败整体回滚可重试。前端每页12或24张，删除最后一张时回到仍有结果的最后一页。

### M1 任务控制与索引重建（2026-10-14）

- `POST /jobs/{id}/cancel`：200，取消本人有效资料的PARSE/INDEX/PREVIEW排队或运行任务，撤销租约/对应版本状态CANCELLED；重复取消返回同记录，成功/失败任务409。原件/切片/引用保留。后台子进程可能在60秒预算内继续结束，其迟到结果不会写入。
- `POST /jobs/{id}/retry`：202，FAILED/CANCELLED恢复同任务、已用尝试数不重置，最多3次；已经QUEUED/RUNNING返回原记录；已成功、上限耗尽或同类型其他活跃任务409。INDEX需有效可索引正文，否则409。
- `POST /versions/{id}/reindex`：`{"request_id":"<UUID>"}`，202返回INDEX任务；必须有成功提取正文或当前确认人工来源。重复UUID返回同一记录（可能已完成/失败/取消）；不同请求已有活跃INDEX时409.details.active_job_id。失败/取消索引需恢复原任务，不能重建新任务绕开其上限；成功后可显式新建重建记录。非法UUID/未知字段422，来源不存在/删除/跨用户404。

同版本锁及租约条件写串行化控制/完成；worker领取时原子更新对应版本RUNNING，索引异常也检查原租约；取消/恢复不能被旧结果覆盖。预览转换每尝试独立输出；失去租约只清理本次未挂载文件，原PDF不删除。FTS失败回滚；Chunk UUID、原文、Citation不变，扫描PDF原parse状态仍真实。无数据库新增字段/迁移；需要重启旧worker加载新语义。当前课程任务列表只返回授权M1任务，仍限最近100条，不是分页交付。

### M1 课程资料包（2026-10-14，M1-EXPORT-01）

| 方法/路径 | 输入/输出 |
|---|---|
| POST /courses/{id}/material-exports | `{request_id:UUID}`，202 MaterialExportResponse；相同请求返回同记录，不同请求已有活跃导出409 |
| GET /courses/{id}/material-exports | 本课程最近20条导出记录 |
| GET /material-exports/{id} | 本人导出范围/快照时间/hash/大小/counts/availability及ProcessingJob |
| POST /material-exports/{id}/retry | 202，失败且未达3次上限；不重置尝试次数 |
| GET /material-exports/{id}/download | application/zip附件/no-store；未完成409，已删除或撤回的包内来源404，包文件损坏409 |
| DELETE /material-exports/{id} | 204，撤销下载并取消任务，移除生成文件；保留课程原件/引用 |

全部Bearer与本人课程过滤，跨用户404、非法请求UUID/未知字段422；空课程409，单课程最多20条保留记录。0008 MaterialExport追加表/外键，后台MATERIAL_EXPORT租约任务处理；SQLite一致读快照，120秒/256MiB总内容/16MiB元数据，2000文档/10000版本/50000片段或人工来源/10000图片预算。失败不挂载半成品；租约过期恢复或明确失败，清理中断产物。本机存储不足也失败而不改变原资料。

ZIP含manifest.json/README.md、originals/previews/text/assets；UUID命名，文件逐项字节/SHA-256校验，源路径必须位于本人课程存储根。metadata保留原文件名/版本/定位/Unicode偏移与source_kind；成功提取正文、已确认及历史确认人工来源，排除草稿/撤回/删除/越权资料；不含FTS/SQLite/服务端路径/配置密钥。截图保留原版本/页，DOCX预览不冒充正文定位。现有包不随改名/新版本重写；包内来源删除/人工撤回后撤销后续下载，已下载本地副本不能撤销。

范围是M1课程资料，**不含笔记、AI、真题、试卷、作答、复习**，不能恢复导入；FR-14/15完整父需求尚未完成。`python3 scripts/verify_material_package.py <zip>`可离线验证格式/路径/成员/字节/hash，不提取文件或启动数据库。响应不返回文件系统路径；下载使用Bearer Blob。

## 2026-10-14 共享课程整理（PLATFORM-COURSE-01）

- POST /api/v1/courses：{"name":"操作系统","description":"学习目标","category":"专业必修","tags":["大二","期末"]}，201。旧name/description请求继续可用；未分类/[]/revision=1为默认。名称去首尾空白且不能为空，分类≤64字，标签≤12个且各≤32字，描述≤5000字；未知字段422。响应追加category/tags/revision与UTC时间。
- GET /api/v1/courses?q=操作&category=专业必修&tag=期末&sort=updated：本人课程数组；q≤200，名称/描述/分类/标签字面包含（ASCII大小写忽略，%/_不是通配符）；category/tag精确匹配，sort=newest（默认）/updated/name。过滤条件取交集。未新增分页；首页对本人列表本地筛选。
- PATCH /api/v1/courses/{id}：{"revision":1,"name":"操作系统专题"}只改名称；未提交描述/分类/标签保留。至少一个整理字段、revision严格整数≥1；description:null清空描述，tags:[]清空标签，name/category/tags:null拒绝。成功200、revision+1；旧revision409.details.server_course，跨账户404，参数422。旧PATCH调用方必须补revision。
- 课程整理不更改Document/Version/Chunk/Note引用UUID，课程标签不自动传播。0009仅追加课程列。当时的删除关联撤权待办已由下节0010补齐；该历史整理验收不代表FR-02全部交互验收完成。见[验收](zhy/shared_platform/course_organization_acceptance.md)。

## 2026-10-14 课程删除（覆盖旧删除说明）

GET /api/v1/courses/{id}/deletion-preview返回{course:CourseResponse,counts:{documents,versions,assets,material_exports,notes,ai_results,past_papers,exam_papers,attempts,review_tasks}}，数量为同一数据库读取快照。资料/笔记/图片统计当前有效对象；M4关联复习包含已完成记录。跨账户/已删除课程404。

DELETE /api/v1/courses/{id}?revision=3：必须当前revision，缺少/非法422、陈旧409.details.server_course、不可访问/重复删除404、成功204。旧客户端必须补revision。0010追加Course.deleted_at；逻辑撤权，无恢复入口，非物理擦除。清理通过模块接口同事务执行，失败全回滚；保留失效来源UUID/元数据和外部笔记正文，不把笔记变成无课程的有效笔记或复习变成无错题的孤立任务。

相关正文/文件/检索/模型/任务/试卷/作答接口撤权；所有者可读既有图片失效元数据以显示availability=unavailable，不能下载。其他课程、账户和独立复习不变。原件等可能保留磁盘，已下载副本不能撤销；完整备份恢复未实现。新模型/解析写入检查有效父课程；只取消活跃任务，历史终态保持。[验收](zhy/shared_platform/basic_acceptance.md)。

## 2026-10-14 智谱真实课程问答

- GET /api/v1/ai/provider：认证后返回provider/configured/model/endpoint、文档与协议入口、核对日期/政策未核实说明/预算，不返回密钥或密钥片段。
- POST /courses/{id}/remote-queries/preview：{query,version_ids:[],chunk_ids:[]}，201 RemoteQueryResponse；query≤2000、版本≤20、片段≤6，实际片段≤2000字符/总8000。为空范围则关键词选最新，显式版本/片段归属校验；未配置/无证据409，越权404，参数或密钥出现在输入422。预览保存15分钟，不调用模型。
- POST /remote-queries/{id}/confirm：{confirm_remote_send:true}，202；必须严格布尔true且无多余字段。只使用服务端快照；同预览重放幂等，过期/配置变更/来源变化/同课程活跃任务409。返回job的AI_ANALYSIS resource_id为RemoteQuery ID；max_attempts=1。
- GET /remote-queries/{id}、POST同路径/cancel：本人有效课程；返回来源快照、模型/端点、expires_at/consented_at/dispatched_at、job与可空AIResult。取消活跃任务/预览，已完成不能改历史409。GET /jobs/{id}支持此类所属资源验证，旧M1任务API不负责取消AI。
- AIResult仍GET /ai-results/{id}读取；model_mode=real，结果含answer/citations/quote_hash/model/review_status/使用量，异常error_code与安全message。读取重新校验引用availability；原文校验不保证解释正确，UNREVIEWED必须人工核实。
- 旧POST /ai-queries mode=real改为409，要求预览流程；demo数组/结果兼容。study-reports mode=real明确未接入，不返回伪真实报告。真实问答不自动驱动M4出题。

0011新增remote_queries；M2服务支持课程/资料/人工来源生命周期取消，课程删除预览counts新增remote_queries。发送派发边界与预算见[contracts](contracts.md)，真实输出/故障与隐私限制见[验收](zhy/integration/zhipu_qa_acceptance.md)。

## 2026-10-15 共享可靠性/分页增量

认证响应字段及Bearer不变，新token为固定HS256标准JWT，旧两段token返回401并重新登录；401附WWW-Authenticate: Bearer。setup初始化后端随机签名密钥，普通网页不配置密钥。空间不足新增507/error.code=INSUFFICIENT_STORAGE/request_id，已保存原件不覆盖。

新增GET /courses/{id}/documents/page：q/category/tag/state(all/ready/processing/failed)/sort(recent/name/size)/offset/limit，返回items/total/offset/limit/stats/categories/tags。GET /courses/{id}/jobs/page：status(all/pending/failed/cancelled/succeeded)/kind(all/PARSE/INDEX/PREVIEW)/offset/limit，返回items/total/offset/limit/pending_count。limit1–100，过滤后分页/UUID稳定排序，旧数组接口仍兼容；归属404/参数422，无迁移。

## 账户备份/恢复（0012）

POST /backups→202控制记录；GET /backups返回本人最近50条，GET /backups/{id}状态/hash/字节/各表数量；GET /backups/{id}/download只有已成功export且来源资格仍有效、包hash匹配才能下载。POST /backups/restore multipart file+confirm=RESTORE_EMPTY_ACCOUNT→202；只向空账户/无同库UUID冲突恢复，全部业务写入一事务，失败清理新文件。DELETE /backups/{id}→204，只允许终态，移除文件/控制记录，不删除恢复的业务数据；运行中409、越权404、非法确认/文件422。

备份ZIP不包含凭据/密钥/可重建课程ZIP字节；保留业务UUID、hash/关系/UTC/时区，不自动执行模型。支持格式/预算/恢复规则见contracts，实际验证见zhy/shared_platform/account_backup_acceptance.md。

## 可诊断与恢复的预览

GET /material-capabilities（Bearer）返回native_pdf、office_available、office_status、message、installation_url，不暴露本机路径；发现可执行程序不保证所有课件一定转换成功。可配置后端HUSTUDY_LIBREOFFICE_PATH。

POST /versions/{id}/preview-jobs（无需正文）→202 ProcessingJob。活跃返回已有记录；失败/取消重试原记录、保留次数上限。可用预览409；旧PPTX缓存页号不匹配且没有有效截图时可新建恢复任务，有截图时409要求人工核对。Markdown/TXT422、原件缺失404、归属/删除404。安装转换器后无需重传文件，用户从阅读区显式重试。

PPTX导出包括隐藏幻灯片并核对页数；GET preview与截图拒绝旧错位缓存，不能把PDF第N页静默冒充原PPT第N张。DOCX继续标preview_page，正文引用仍docx_block。PDF.js使用同版本legacy显示层/worker，以支持缺少新Map方法的Safari。详情见[本轮验收](zhy/materialhub/preview_recovery_acceptance.md)。

## M1-SEARCH-02 分页知识查找

- `GET /api/v1/courses/{id}/search/page?q=滑动窗口&latest_only=true&offset=0&limit=12`：资料FTS/BM25结果，支持原category/tag过滤，稳定score/chunk UUID顺序；返回items/total/offset/limit。旧search数组接口仍限50条，新分页可查看全部命中。
- `GET /api/v1/courses/{id}/note-search?q=滑动窗口&offset=0&limit=12`：M3只读适配器，题名/正文包含完整关键词，updated_at降序/UUID平分；items只含id/title/excerpt/updated_at。只查当前有效课程未删笔记，不混入无课程笔记。
- 页大小1–100、offset≥0、q≤200字符；空/无检索词返回空页，材料超过100个去重token为422；跨用户或已删除课程404。每次请求的计数/页内容使用同一SQLite读快照，跨页更新可能改变排名/数量。
- `excerpt={text,start_offset,truncated_after,highlights:[{start,end}]}`，最多260个Unicode字符；highlights针对excerpt.text，左闭右开；仅显示摘要，不可用于Citation生成。文本不得当作HTML。材料item保留document/version/chunk/locator/source_kind/score等来源字段，但不返回完整text；score不是可信度。

## M1 原格式预览消费

PPTX/DOCX直接预览使用现有授权GET `/versions/{id}/original`，不新增公开文件URL；前端请求支持AbortSignal，卸载/切换取消。`preview_status`与GET preview仍表示原PDF或转换兼容PDF，不由客户端原格式渲染成功覆盖。无数据库变更或新业务API，原格式本地状态不代表后端解析/索引已成功。图片截图来源仍由既有PDF页校验。
