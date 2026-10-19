# Hustudy API（Phase 0）

## M3-TRASH-01（2026-10-18）

下列路径均在`/api/v1`下。回收站为当前账户全部课程，GET不触发清理。单篇DELETE /notes/{id}?revision=N仍返回204，现记录删除时间和到期时间，允许恢复。

| 接口 | 请求/响应与约束 |
|---|---|
| GET /notes/trash?offset=0&limit=50 | limit1–200；返回items（无正文）、total、全部id/revision的snapshot；包含course_name、deleted_at、purge_after、restore_requires_course |
| POST /notes/trash/batch | action=trash/restore/purge；notes为1–200个不重复{id,revision}；fallback_course_id为原课程不可用时显式恢复目标；全部归属/状态/revision先校验，成功{affected} |
| POST /notes/trash/empty | {snapshot}；与当前账户全部回收站快照一致才原子清空，成功{affected}；新删除/恢复/策略变化使旧快照失效，409且无部分删除 |
| GET /notes/trash/policy | {retention_days,revision}；无自定义策略返回30/0，null代表关闭 |
| PUT /notes/trash/policy | {retention_days:1–365整数或null,revision}；账户写锁内校验旧revision，重算已有删除记录的到期时间并递增各note.revision；返回新策略 |

批量状态/版本冲突409，越权或对象缺失404，重复/超限/无效天数422。彻底删除不会删除图片或资料。原目录不存在时恢复未归档；原课程不可用而未指定本人有效fallback_course_id则422/404。UTC期限、worker清理与0016备份兼容详见[共享契约](contracts.md#m3-trash-01)。

## M3-ORGANIZE-IMPORT-EDITOR-01（2026-10-18）

所有接口在`/api/v1`下并检查当前用户归属：

| 接口 | 请求/响应与约束 |
|---|---|
| GET /note-folders?course_id=… | 返回本人有效课程的文件夹；id/name/course_id/parent_id/revision/时间字段。 |
| POST /note-folders | `{course_id, name, parent_id?: null或UUID}`；201；每课500个、最多6级、同级名称不区分大小写去重。 |
| PATCH /note-folders/{id} | `{revision, name?, parent_id?}`；parent_id未传保留、null移到根；200，旧版本409，循环/过深/重名422。 |
| DELETE /note-folders/{id}?revision=N | 仅空文件夹204；含有效笔记/子文件夹或版本冲突409；越权404。 |
| POST/PATCH /notes | 追加可空folder_id；创建默认未归档，更新未传保留、null移出；同账户同课程校验，和正文共用revision。NoteResponse及409详情包含folder_id/server_folder_id。 |
| POST /notes/batch | `{notes:[{id,revision}], add_tags?:[], remove_tags?:[], folder_id?:null或UUID}`；1–200个不重复笔记；成功返回更新后的NoteResponse数组。先移除再添加标签、去重且总数≤12；先校验全部条目再原子更新，409/404/422均不部分写入。 |
| POST /notes/import-markdown | multipart `file,course_id,request_id,tags(JSON字符串),folder_id(可省略)`；201 NoteResponse。仅.md/.markdown，UTF-8/BOM、≤2MiB；NUL/非UTF-8/非法标题或标签422，过大413。标题为文件名去扩展名；相同UUID/内容复用原笔记，已变化409，不覆写。 |

选择ZIP自动按文件夹树分配安全路径，根images保留给图片，未归档笔记根目录导出；跨目录图片与双链转换为相对路径。不增加外部AI接口，分类建议在浏览器本地计算。0015 NoteFolder/Note.folder_id与账户备份兼容见[契约](contracts.md#m3-organize-import-editor-01)、[验证与操作](fzk/note_organization_acceptance.md)。

## M3-CITATION-LIFECYCLE-01（2026-10-18）

GET `/api/v1/notes/{note_id}/citations`追加可空`document_id`、`document_name`、`version_no`，来源经M1授权重查；失效来源保留原摘录/定位及不可用状态，不补造名称。POST同路径仍201，同笔记相同version_id/chunk_id/quote返回既有引用，最多50条，超限422；创建笔记中的citations也去重。重复提交在笔记写锁内判断，引用不改变正文revision。

新增DELETE `/api/v1/notes/{note_id}/citations/{citation_id}`，本人有效笔记+本笔记引用才允许移除，成功204，不存在/越权404。只移除该关联，原资料/笔记正文/其他引用保留；来源反查更新，旧导出包引用该ID时下载404要求重建。失效引用仍可移除，无新迁移。[契约](contracts.md#m3-citation-lifecycle-01)、[M3审计及验证](fzk/m3_completion_audit.md)。

## M3-BATCH-IMAGES-01（2026-10-18，当前行为）

POST `/api/v1/note-exports`：`{request_id: UUID, note_ids?: UUID[], include_images?: boolean}`。note_ids省略为当前全部有效笔记，显式数组须1–2000个不重复ID；include_images默认true，页面始终true，API显式false保留兼容。创建冻结所选ID，部分不存在/越权整体404，非法参数422；同request_id不同选择/图片选项409。重试沿用原范围，之后新增笔记不自动加入。

响应在既有字段上新增`layout: simple | legacy`。新包根目录为所选标题命名Markdown，无sources/manifest/README；仅这些笔记实际引用的有效图片进入images，按Asset ID去重，不递归加入链接笔记或其他图库图片。没有图片时不创建空目录。相对链接URL编码，完整解压后阅读。旧记录/旧排队任务保留原参数与字节。请求参数存既有sources_json.request，不需要新迁移；下载内部hash/权限和撤权校验保持。GET `/notes/{id}/export`的Content-Disposition改为UTF-8标题文件名，页面保持一致。

图片管理复用原M1分页/元数据PATCH/DELETE/引用查询；两处批量上传入口每批1–20张、单张非空≤10MiB，逐张顺序调用既有POST `/courses/{id}/assets`。部分失败保留成功，网络/认证/限流/服务错误停止队列，无自动重放；未完成项显式重试。未新增M1后端行为。[契约](contracts.md#m3-batch-images-01)、[证据](fzk/note_batch_images_acceptance.md)。下面复杂包布局仅用于历史说明；新创建请求以上述规则为准。

## M3-IMAGE-NAMING-01（2026-10-17，验收反馈修复）

NoteExport响应新增`filename`，由创建时间和账户时区生成`Hustudy-笔记知识库-YYYY-MM-DD_HH-mm-ss-SSS.zip`；下载接口的Content-Disposition与此一致。新包按课程/标题命名，原路径字段和hash语义保持，以manifest为准；旧包内布局须重新导出才更新。无新迁移或新接口。

笔记编辑器直接上传复用`POST /api/v1/courses/{id}/assets`，PNG/JPEG/WebP、最大10MiB；服务端仍验证实际图片内容与归属。上传成功才插入asset引用。规则见[公共契约](contracts.md#m3-image-naming-01)，本轮证据见[验收反馈修复](fzk/note_batch_images_acceptance.md)。

## M3-PORTABLE-NOTES-01（2026-10-17，本地待集成）

下列路径均以`/api/v1`开头，需Bearer认证。知识库ZIP独立于单篇.md和账户备份；范围为本人全部有效已保存笔记/引用图片，不受当前课程筛选影响。

| 方法 | 路径 | 输入/输出 |
|---|---|---|
| POST | `/note-exports` | 严格`{request_id: UUID}`；202返回NoteExport，幂等重发返回同一记录 |
| GET | `/note-exports` | 最近20条本人导出记录 |
| GET | `/note-exports/{id}` | 单条记录和任务状态 |
| POST | `/note-exports/{id}/retry` | 202，仅失败且未达尝试上限；活动任务重复重试返回当前状态 |
| GET | `/note-exports/{id}/download` | ZIP附件；未成功409，来源撤回/越权404，文件hash不符409 |
| DELETE | `/note-exports/{id}` | 204，移除派生文件/记录；活动任务取消并撤销租约 |

NoteExport响应为`{id,created_at,snapshot_at,filename,sha256,size_bytes,counts,availability,job}`。counts含notes/assets/citations/files；availability为pending/active/unavailable；job复用JobResponse（NOTE_EXPORT、QUEUED/RUNNING/SUCCEEDED/FAILED/CANCELLED、尝试次数/错误/进度）。每账户同时1个活动任务，最多20条记录，3次尝试；预算与来源清单见[契约](contracts.md#m3-portable-notes-01)。派生zip_path、内部来源索引不暴露。

DELETE `/notes/{id}?revision=N`：当前UI发送保存版本；并发变化409.details包含server_revision/server_title/server_content/server_tags，原数据保留。旧无revision调用兼容；删除不存在/越权404。POST `/notes`新增可选request_id UUID以防网络重试重复创建；同账户、未变化且初始内容/标签/来源完全相同时返回原笔记，已变化409含server_id，删除/越权404，旧调用可省略。更新跨课程关联笔记时客户端不发送页面course_id。

新账户备份schema_revision为0014_note_exports，显式兼容0012/0013；NOTE_EXPORT控制任务/派生表不进入完整业务备份。其余版本拒绝；0012仍由M3适配器补空tags。本轮验证见[fzk验收](fzk/m3_completion_audit.md)。下面0013说明保留为上一切片历史。

## M3-NOTE-TAGS-01（2026-10-17，功能分支待集成）

- 所有Note响应新增 `tags: string[]`。POST `/notes` 可传 `tags`，缺省[]；PATCH `/notes/{id}` 可传tags，与title/content共用revision原子保存，省略保留、[]清空、null返回422。
- 规范：最多12项，每项trim后1–32字符，拒绝控制字符，精确去重并保序。冲突409的details新增 `server_tags`，原 `server_title/server_content/server_revision` 保留。
- GET `/notes?course_id=…&q=…&tag=…`：q最多200字符，匹配标题/正文/标签的字面子串；tag最多32字符，精确匹配一个标签。参数可组合；本人归属/课程有效性/删除过滤不变。GET `/courses/{id}/note-search?q=…` 也匹配标签，返回结构与分页不变。
- 例：`PATCH /notes/{id}` 请求 `{"revision":1,"tags":[" 期末 ","期末","重点"]}`，成功标签为 `["期末","重点"]`，revision递增。非法更新不修改正文或标签。
- 完整账户备份schema_revision为0013_note_tags；旧0012由M3适配补空标签后继续严格校验。参见[公共契约](contracts.md)、[fzk验收](fzk/note_tags_acceptance.md)。

2026-10-17 M2-TOPICS-REUSE：RemoteQueryResponse增加可空reusable_result；POST /remote-queries/{id}/reuse请求{result_id: UUID}，返回已有AIResultResponse，不创建任务或模型调用，失配409/预览归属404。三种任务预览均提供命中信息；新候选信封per_question_topics=true、提示词v5，逐题topic_ids仅允许本次所选非空不重复子集。QA在首个sources元素保存request_scope（version_ids/chunk_ids）区分检索相同但选择范围不同；此元数据不发送给模型。旧v4历史仍可读。[契约](contracts.md)、[实现](gcx/topics_reuse_2026_10_17.md)。

## 2026-10-17 M2真实资料增量（优先于旧6段说明）

报告preview保留原路径，version_ids≤20、chunk_ids≤400；完整正文≤240000字符，超限422且不截断。report_scope.batched=true、coverage.batch_count/warnings，RemoteQueryResponse新增可选batch_progress={total,completed,max_calls,chars}。每批≤8000字符/32子段，确认覆盖整份分批计划，worker一次处理一批。

新增`POST /api/v1/remote-queries/{id}/resume`，Bearer与严格`{confirm_remote_send:true}`，202；仅停止的分批报告，重验来源/模型，跳过成功批。无确认422、跨账户404、配置变化/已有任务/任务不允许恢复409。取消/丢失租约不自动重发。内部checkpoint与中间草稿不进入普通历史；中间草稿通过RemoteQuery.result可见，partial=true/error_code=PARTIAL_REPORT，不是完整成功。

最终result.study_report_sections=[{title,report}]，每节独立报告/证据；仅一批仍兼容study_report。部分失败保留已完成sections，status仍失败并明确partial。候选preview最多128段/32000字符，不再截去每段2000字符后的正文；超限422。来源子段带chunk_start，Citation偏移仍相对原chunk。输出/引用格式与旧历史兼容，细节见[本轮契约与验证](gcx/real_materials_2026_10_17.md)。

## 2026-10-16 M2候选/演示/精确范围

- GET `/api/v1/courses/{id}/question-draft-context`：可用Topic/已确认原题摘要，不含原题答案。
- POST `/api/v1/courses/{id}/question-drafts/preview`：CandidateRequest，201返回不可变设置/材料/原题预览；沿用remote-queries确认/状态/取消。GET同课程`question-drafts`最近20条，GET `/question-drafts/{result_id}`读取单条。
- POST `/api/v1/courses/{id}/question-drafts/demo`：固定自制演示，未知输入insufficient_evidence；不创建模型任务。
- POST `/api/v1/courses/{id}/study-reports/demo`：ReportPreviewRequest，完整固定教学演示；旧`/versions/{id}/study-reports`演示入口转用同一实现，未知材料不再返回通用成功模板。
- 报告preview/demo新增可选chunk_ids（最多6）；普通问答原有chunk_ids现可从前端选择。GET `/api/v1/courses/{id}/ai-results`最近20条普通问答，排除报告和候选。

参数、枚举兼容、章节范围映射与失败语义见[公共契约](contracts.md)，[公开QuestionDraft schema](gcx/question_draft_schema.json)及[验收](gcx/candidate_acceptance.md)。


## 2026-10-16 教学报告（M2-STUDY-REPORT-01）

- POST `/api/v1/courses/{course_id}/study-reports/preview`：`{"goal":"理解本章","version_ids":["UUID"],"study_mode":"systematic"}`；201返回RemoteQueryResponse、request_kind=study_report、report_scope/coverage，尚未发送模型。
- POST `/api/v1/remote-queries/{id}/confirm`：`{"confirm_remote_send":true}`；202入队。GET同一路径查询、POST `/cancel`取消。普通问答接口保持兼容。
- GET `/api/v1/courses/{id}/study-reports`：最近20条报告结果；GET `/api/v1/study-reports/{result_id}`：单份持久结果。均校验本人/有效课程；响应AIResultResponse，成功含result.study_report、answer Markdown、citations、coverage、prompt_version，失败含原因。
- 旧POST `/versions/{id}/study-reports`保留演示兼容，real模式返回409引导新预览流程。

覆盖预算/字段/不可变信封定义见[contracts](contracts.md)，手工示例及限制见[gcx验收](gcx/study_report_acceptance.md)。


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

## 2026-10-16 报告教学结构与标签审阅补充

现有study_report响应增量字段：topics[].concept_group（string/null）、related_concepts（[{target,relation}]）、breakthrough_steps（string[]），顶层review_suggestions（string[]）。省略按空值兼容，旧AIResult不重写。学习建议不是教师/历史证据，related_concepts的target必须为本报告其他知识点且不重复。前端标签审阅为独立快照，用户编辑留存于Markdown，使用现有POST /notes保存；无新端点、无AIResult更新。权威约束见contracts.md及gcx/basic_acceptance.md。

## 2026-10-17 智谱模型配置兼容

/api/v1/ai/provider根据当前配置返回glm-5.3-flash（新默认）或glm-4.7-flash及对应模型文档。端点/业务schema不变，预览继续冻结model/endpoint，配置变化拒绝确认/派发旧请求。新模型thinking.enabled+reasoning_effort.low，最终JSON仍经原结构和引用校验，reasoning_content不返回。

## 2026-10-19 M3 识别文本插入与AI整理停用

识别GET/POST/DELETE归属和预算保持，result.text改为parts.text以空行连接，不注入页号/时间Markdown标题；parts保留定位。识别流程不调用POST /notes，前端将确认文本交给当前笔记编辑器。

POST /api/v1/note-captures/{id}/organize在登录/归属检查后返回410；capabilities.ai恒false，model为空，ai_unavailable_reason明确停用。worker取消QUEUED/RUNNING NOTE_ORGANIZE并清除租约，旧结果不删。PUT /api/v1/note-ai/config返回410；GET仍脱敏返回旧凭据元数据、configured:false和停用原因，DELETE仍按revision清除。无有效M3凭据解析/Provider派发或服务器密钥回退，不改M2接口。请求结构不合法仍由原schema返回422。

[共享契约](contracts.md#m3-capture-text-01)、[验收](fzk/capture_text_acceptance.md)。
