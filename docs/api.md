# Hustudy API（Phase 0）

## 多模型与笔记助手（2026-10-27）

均需Bearer认证并限定当前账户。原 `/api-connection` 继续独立处理智谱配置；高级配置不回显密钥、不进入课程包或账户备份。

| 路由 | 请求与结果 |
|---|---|
| `GET /api/v1/model-connections` | revision、active、builtin、profiles、allowed_hosts；仅配置元数据和configured，no-store |
| `PUT /api/v1/model-connections` | revision、可选id、name、vendor=deepseek/compatible、endpoint、model、key、vision/thinking/json_mode；编辑省略key保留该配置密钥，最多8份 |
| `POST /api/v1/model-connections/active` | revision、profile_id；null选择原智谱；变化令旧发送预览失效 |
| `DELETE /api/v1/model-connections/{id}?revision=...` | 删除自己的非活动配置；活动项须先切换，修订不符409 |
| `POST /api/v1/model-connections/test` | revision、profile_id、confirm=true；只测当前所选模型、发送极短文本，返回connected/model/message |
| `POST /api/v1/note-assistant/preview` | course_id、可选note_id/revision、task=summary/explain/organize/review/custom、scope=full/selection、text、instruction；核对归属/revision后返回完整发送文本、模型/端点及10分钟preview_token，不调用模型 |
| `POST /api/v1/note-assistant/generate` | input为上述原始请求，加preview_token、confirm=true；返回request_id/markdown/model/task/usage/notice，不写笔记 |

正文最多24000字符、instruction最多2000、结果最多12000；预览绑定用户/正文摘要/来源revision/配置。无配置或已变化409、权限404、输入/内部令牌变化422、频率上限429、模型失败502。单账户同时一请求，10分钟最多20次；同一成功请求返回缓存结果，处理中/失败未知请求不重复调用。生成结果采纳只改前端草稿，仍经原笔记保存接口；输出和预览no-store。部署可用 `HUSTUDY_ADDITIONAL_AI_HOSTS` 扩展HTTPS主机白名单。详细[契约](contracts.md)与[使用及验证](fzk/note_assistant_acceptance.md)。

## 标准数据包与课程合并（2026-10-27）

均需Bearer认证，只处理本人有效课程。`selection` 为类别到UUID列表的映射，类别为 `notes/folders/documents/assets/topics/past_papers/exam_papers/ai_results/reports/blueprints`，至少选择一项、最多3000个明确选择；空目录可选择其folder，关联依赖在预览单独说明。

| 路由 | 用法 |
|---|---|
| `GET /api/v1/courses/{id}/packages/catalog?kind=course\|folder&folder_id=...` | 可识别条目元数据；folder_id仅文件夹模式，省略时包含课程全部有效笔记及未归档，提供时限定该目录及后代 |
| `POST /api/v1/packages/preview` | multipart `file` 上传标准ZIP；全包校验后返回目录及preview_id、sha256、expires_at，不写业务行 |
| `POST /api/v1/packages/selection-preview` | `course_id/kind/folder_id` 或 `preview_id` 二选一，加selection；导入可附target_course_id、parent_folder_id、title预检；返回最终目录、实际selection、counts、warnings、selection_sha256 |
| `POST /api/v1/packages/export` | course_id、kind、可选folder_id、selection、可选expected_sha256；直接返回ZIP及可读Content-Disposition文件名 |
| `POST /api/v1/packages/import` | preview_id、request_id、selection、可选expected_sha256／target_course_id／parent_folder_id／title；业务行与成功凭据同事务 |
| `GET /api/v1/packages/imports/{request_id}` | 查询本人的成功结果；无成功记录404，不等于可以换请求ID重建 |
| `GET /api/v1/packages/previews` | 本人的预览ID、时间、大小和摘要；不返回内部路径 |
| `DELETE /api/v1/packages/previews/{id}` | 只移除预览文件和控制记录，不删除已导入内容或成功凭据 |

course包不传target_course_id时新建课程，可用title指定名称；传入本人有效目标课程时追加合并，禁止同时传title或parent_folder_id，不覆盖目标课程信息。folder包必须指定目标课程，可选父文件夹，保留层级和未归档笔记。成功响应含import_id、course_id、folder_id、note_count、folder_count、counts及warnings；counts按实际新建业务对象统计。相同request_id及相同参数返回原结果，不同参数409。

网页确认强制带预览selection_sha256作为expected_sha256；脚本客户端可省略。指纹覆盖所选正文、元数据、关系及文件哈希，文件区临时标识变化不影响稳定性。来源变化返回409及`PACKAGE_SELECTION_CHANGED`，必须重新预览。网络未知、401及普通409不自动重发。预览24小时到期410，每账户最多10份，可主动移除；成功幂等凭据独立保留。格式/预算/关系失败422，越权404，磁盘不足沿全站507。详细预算和迁移见[说明](fzk/portable_packages_acceptance.md)。

## 课程笔记关系图谱（2026-10-26，M3-NOTE-GRAPH-02）

`GET /api/v1/courses/{course_id}/note-graph`：认证只读，q≤200字的标题字面子串，link_state=all/linked/isolated，limit=1..200（默认120），可选focus_note_id定位一跳邻域。聚焦与非空标题/非all状态互斥422，不可访问课程或焦点404。响应为course_id、focus_note_id、nodes（NoteSummary + incoming_count/outgoing_count）、edges（source_id/target_id）、total_nodes/total_edges、node_limit/edge_limit、nodes_truncated/edges_truncated。度数按完整当前课程去重关系计算，totals按筛选/聚焦作用域计算；边最多400条，只含实际返回节点。排除他人/跨课程/回收笔记、自身链接；不读取或返回正文，无写入。完整规则见[契约](contracts.md#m3-note-graph-02)。

> 2026-10-24接手提醒：M2教师强调只读reader是代码集成点，不是现成的标记写入HTTP接口；M1阅读标记入口及M4真题身份确认入口仍待各自成员补齐。M2消费分支完成不等于两标签端到端已完成。[缺失接口、责任与验收](gcx/handoff_2026_10_24.md)。

2026-10-24 QA preview chunk_ids扩为400，显式范围使用完整正文，qa_scope返回mode/coverage/batched/batch_count；batch_progress.kind=qa时total含最终汇总步骤，resume入口兼容QA。逐批原文依据不是最终答案，空批继续、汇总才形成结果；原权限/账户配置/引用/预算保持。[契约](contracts.md)与[验证](gcx/qa_batches_2026_10_24.md)。

2026-10-24 PLATFORM-ACCOUNT-AI-04：`/api-connection`仅当前账户，scope=account；GET返回Cache-Control:no-store，PUT/DELETE按本人revision校验；POST-test严格confirm/revision，不在网络期间持锁。密钥分账户加密不回显，M2/M4后台按owner读取，无共享回退。[契约](contracts.md)与[验证](gcx/account_api_2026_10_24.md)。

2026-10-24 M2-AUTO-LABEL-SOURCES-03：新report preview删除teacher_marks/exam_paper_ids/exam_sources_confirmed（提交返回422），仅保留笔记选项。自动读取阅读标记/确认真题依据，冻结m2_supplement.version=2并复核变化；旧v1手动来源预览409，历史保留。[当前契约](contracts.md)与[验收](gcx/supplements_labels_2026_10_24.md)。

2026-10-24 M2-SUPPLEMENT-LABELS-02：问答/报告preview追加note_ids/notes_confirmed；报告另支持teacher_marks及exam_paper_ids/exam_sources_confirmed。严格确认、5篇/12000字符笔记、20条教师记录/20卷真题上限；冻结m2_supplement，复核修改/撤回，服务端生成事实标签，旧请求缺省空输入兼容。详情见[契约](contracts.md)及[验收](gcx/supplements_labels_2026_10_24.md)。

2026-10-24 M2-EXECUTION-01：问答/报告preview新增max_structure_repairs（严格0–2，默认0），RemoteQueryResponse增加execution执行预算/窗口/调用/修复计数；结果附执行快照。原resume明确同意后开启新窗口、跳过成功批次，修复额度全请求不重置。TASK_BUDGET_EXCEEDED表示本次确认的执行预算已用尽，不当平台不可用。内部状态不是学习历史。[契约](contracts.md)、[说明](gcx/execution_budget_2026_10_24.md)。

## 原文关联笔记分页（2026-10-24，M1-REFERENCE-NOTES-28）

新增GET /api/v1/versions/{version_id}/reference-notes：q≤200、可选chunk_id、offset=0..1000000、limit=1..50（默认6）。响应固定课程/资料/版本/片段身份与真实items/total/offset/limit/checked_at；每项为note_id/note_title/note_course_id/updated_at/citation_count及最近有效引用样本citation_id/chunk_id/locator_type/locator_value/quote_excerpt（≤180字符）。同笔记仅一项，引用数仅当前范围有效逐字引用，按笔记更新时间/UUID稳定排序；不返笔记正文。本人未归课程/已有跨课程引用保留原归属；非法版本/题库原件/不属当前版本片段404。删除/撤回/假引用不纳入。旧GET references列表兼容，改安全元数据投影，不返回Note.content。[契约](contracts.md#m1-reference-notes-28)。


## 课程复习日程（2026-10-24，PLATFORM-COURSE-AGENDA-27）

兼容扩展GET /api/v1/review-tasks：state=pending（默认）/all/completed；period=all（默认）/due（今天及逾期）/overdue/today/upcoming；course_id可选，必须本人未删除课程；q≤200字，按标题字面子串查找；offset=0..1000000、limit=1..100。新增响应course_id（无筛选为null）、counts={pending,due,overdue,today,upcoming,completed}，按课程/标题基础集合统计，列表再按状态/时间筛选。today为账户时区日期；total真实分页，按due_date/id稳定排序；原items仅ReviewTask元数据。无课程旧独立计划只在不筛课程时保留，移出错题/删除课程排除；404不泄漏外部课程。旧GET不改变默认可见范围/排序，不改写计划、作答或掌握。[契约](contracts.md#platform-course-agenda-27)。


## 阅读知识点导航（2026-10-23，M1-READING-NAVIGATOR-25）

无接口或数据契约变化：当前报告内关键词/页码筛选、每页8项和逐点讲解均本地执行。当前阅读页仅用于反查原citation，不查询或修改Topic/笔记；原文读取和笔记保存沿既有端点与授权，翻PPT不因页码同步重新请求原件。见[契约25](contracts.md#m1-reading-navigator-25)与[验收](zhy/materialhub/reading_navigator_acceptance.md)。

## 当前PPT总结与知识点摘记（2026-10-23）

无新端点/schema：阅读专用视图仍通过study-reports/preview提交当前唯一version_ids和空chunk_ids，沿服务端全可用文字/分批预算；提示词版本现为zhipu-study-report-v7。知识点页码从服务端citation.locator只读派生，摘记用原notes接口保存本知识点精确引用与用户标题；request_id/正文/标题/引用同冻。见[契约24](contracts.md#m1-ppt-companion-24)与[体验](zhy/materialhub/ppt_companion_acceptance.md)。

## 公共后端连接（2026-10-23，PLATFORM-CLOUD-ACCOUNT-22）

接口/认证协议保持。前端显式VITE_API_BASE_URL优先，未配置时开发为http://127.0.0.1:8000/api/v1、生产同源/api/v1；所有认证读取和文件下载沿统一基址。部署与现有账号迁移见[云端账号说明](zhy/shared_platform/cloud_accounts.md)，不是GitHub账号库同步或自动云部署。

## 资料上限与阅读AI集成（2026-10-23）

原有`POST /courses/{course_id}/documents`、`POST /documents/{document_id}/versions`单文件上限现为30MiB（31457280字节，含上限），超限仍422且不入库/不建任务。前端单批20份/100MiB保持；Office原格式输入与部署代理同步。阅读AI复用既有study-reports/remote-queries及notes接口，无新AI端点；笔记保存传冻结request_id，未知结果不重放为新身份。见[契约20](contracts.md#m1-upload-limit-20)、[契约21](contracts.md#m1-reader-ai-21)。

## 资料处理服务状态（2026-10-23，M1-UPLOAD-RELIABILITY-19）

认证GET `/api/v1/processing/status`返回`state=ready/starting/unavailable`、`checked_at`与受控`message`；只读核对本机worker锁/有界新鲜心跳，不创建任务，不返回PID/路径/数据库信息/其他账户队列。`ready`只表示服务连接状态，不是任务完成或时延保证。原`/health`继续仅表示API/数据库可用。开发生命周期托管、生产外部守护与上传不自动重放见[契约19](contracts.md#m1-upload-reliability-19)及[部署准备](zhy/shared_platform/worker_deployment.md)。

## M1最新版本资料检查（2026-10-23）

GET `/api/v1/courses/{course_id}/material-health?issue=attention&q=&offset=0&limit=12`：issue支持attention/all/text/parse/index/preview/processing，返回最新版本元数据、当前问题/正文标记、本页最新阶段任务与匹配范围counts。只读、同账户有效课程，真实分页；不返回正文/文件路径/租约。恢复复用既有POST `/jobs/{id}/retry`，检查页不新建任务。课程工作台materials.counts增加attention_materials（当前资料份数），原failed_jobs仍为历史任务数。[契约17](contracts.md#m1-readiness-17)。

## M1原文关联错题与复习摘要（2026-10-23）

GET `/api/v1/versions/{version_id}/learning-links`兼容15，kind新增mistake、counts增加mistake。错题项补source_relation（citation/version）及review.mastered/pending_count/due_count/next_due_date；响应增加today/timezone，按账户时区统计到期。整版本来源只在无引用且source_version_id匹配时纳入整版本查询，不用于片段；坏引用不降级。复用原分页/权限/只读及无题干答案契约。[详细边界](contracts.md#m1-source-review-16)。

## 2026-10-23 资料学习关联（M1-LEARNING-CONNECTIONS-15）

`GET /api/v1/versions/{version_id}/learning-links?kind=all&q=&offset=0&limit=12[&chunk_id=<uuid>]`：kind仅all/note/qa/report/topic，q最多200字标题字面搜索，offset≤1000000、limit1–50。先验证本人有效课程/material版本及可选片段；仅列至少一条当前有效逐字原文引用的笔记、完整grounded问答/报告和有效知识点，各域SQL适配返回元数据并真实计数/去重/分页。响应course_id/document_id/version_id/chunk_id、items、counts、total/offset/limit/checked_at，无正文/题干/答案/摘录/路径/模型配置；旧AI无顶层引用不猜关联。无写入或新迁移，401/404/422保持统一错误。[完整契约](contracts.md#m1-learning-connections-15)。

## 2026-10-23 M1选择范围导出与任务定位

`POST /api/v1/courses/{course_id}/material-exports`新增可选`document_ids`（1–100个唯一UUID）。省略/null兼容原课程包；选择时服务端核对全部归属、捕获当前全部版本，保存既有sources_json.request，失败重试不扩大范围。相同request_id只接受相同课程/选择集合，范围不同409，越权404、空/重复/超限422。响应新增scope=course/selected和selected_count，下载/重试/移除接口不变；选择包只包含固定版本的来源图片，原预算/hash/撤权保持。[完整契约](contracts.md#m1-scoped-export-14)。

`GET /api/v1/courses/{course_id}/jobs/page`已有kind=all/PARSE/INDEX/PREVIEW和status=all/pending/failed/cancelled/succeeded，本轮前端补齐组合筛选与原版本回跳。JobResponse.document_id/resource_id分别为资料/版本UUID；不使用文件名猜定位，无新增任务接口或schema。

## 2026-10-23 课程学习记录（PLATFORM-RECORDS-10）

`GET /api/v1/courses/{course_id}/learning-records?kind=all&q=&offset=0&limit=12`：kind仅all/material/note/qa/report/attempt/mistake，标题q最多200字，offset 0–1000000，limit 1–50。返回course_id、items（WorkspaceItem元数据，资料含版本UUID）、total、counts（标题匹配的各类型计数）、offset/limit、checked_at。SQL分页、同一read snapshot及归属/删除过滤；401/404/422沿统一错误。AI报告使用可读标题，绝不返回笔记/AI正文、题干/答案/作答或路径。仅当前可用内容汇总，不是不可变操作日志；打开目标时原接口重新授权。完整[契约](contracts.md#platform-records-10)。

M1-READING-TOOLS-05（2026-10-22）：阅读书签在浏览器按auth/me.id与课程隔离；版本对照复用GET documents/{id}/versions与versions/{id}/chunks，无新增API、数据库或迁移。回跳重验document.course_id、版本归属及chunk.version_id/UUID，缺失不得静默回退。书签不属于Note/Citation或账户备份。[契约](contracts.md#m1-reading-tools-05)。

## LEARNING-HUB-04：知识点只读聚合（2026-10-22）

| 接口 | 行为 |
|---|---|
| `GET /courses/{id}/learning-topics?q=&state=all&offset=0&limit=12` | state=all/needs_review/without_questions；limit≤50，q≤200。items为Topic元数据、含子标签的confirmed/pending题目记录数及当前needs_review错题数，返回total/offset/limit/checked_at/course_id；无题干/答案/笔记正文 |
| `GET /courses/{id}/learning-topics/{topic_id}` | 本考点元数据/计数、固定版本人工确认sources（失效不返回原文/资料名）、关键词candidates、M3同源/同标签候选notes、当前mistakes与PENDING reviews；含账户today/timezone。关系类别独立，不自动创建任务或修改统计 |

Pydantic输出白名单；有效本人课程、只读快照，错配/删除404，合并409且details.target_id仅本人同课程目标，超出2000 Topic/20000题目/20000错题预算422。不改变原抽题/答案隔离。确认原文复用`PUT /topics/{id}/sources`与revision；练习仅通过URL预填Topic，最终仍经原抽题校验。本机资料视图无服务端写入。[契约](contracts.md#learning-hub-04)与[实现/验证](zhy/integration/learning_hub_acceptance.md)。

## 学习连续性与按需目录（2026-10-22）

以下均为已登录用户的只读接口，无新迁移；旧接口保持兼容。

| 接口 | 返回与边界 |
|---|---|
| `GET /notes/catalog?offset=0&limit=200` | items/total/offset/limit；limit≤200，只含有效本人笔记id/course_id/folder_id/title/tags/revision/updated_at；排除撤权课程，保留全局笔记，无正文 |
| `GET /courses/{id}/note-matches?q=&tag=` | 原标题/正文/标签搜索规则，返回匹配ids；最多20000，超限422；课程归属校验 |
| `GET /notes/{id}/backlink-options` | 反链来源元数据；源/目标均须本人可访问，无正文 |
| `GET /courses/{id}/question-directory?offset=0&limit=200` | items/total/offset/limit，limit≤200；题号/状态/revision/Topic ID/70字符题干摘要/展示去重hash，不返回答案/解析/完整正文 |
| `GET /past-questions/{id}` | 已授权且未移出题目的原管理question_payload，含paper_id；作答期间禁止管理读取，详情失败可重试 |

笔记管理仅选中时读取正文；AI资料选择复用documents/page，每页12份、所选版本跨页独立保留。阅读笔记复用POST /notes及Citation原子创建，不新增AI接口。本机恢复副本无后端写入接口，恢复后仍走原revision/request_id。[完整契约](contracts.md#platform-continuity-03)与[使用及验证](zhy/integration/continuity_acceptance.md)。

## M1资料批量整理与引用目标（2026-10-22）

- POST `/api/v1/courses/{id}/documents/organize`：items含唯一id及expected_updated_at，1–100项；可选category、tags_mode（keep/add/remove/replace/clear）及tags。200返回items元数据与changed；404无权/撤权/非material，409快照冲突，422操作/最终标签超限，失败整批不写。
- PATCH `/api/v1/documents/{id}`增加可选带时区expected_updated_at，409的details.server_document为当前元数据；旧省略调用兼容。
- GET `/api/v1/courses/{id}/note-options?q=&offset=0&limit=20`：只返回本人当前课程有效笔记id/title/updated_at及total/offset/limit；limit≤100、q≤200，标题字面匹配，空查询按最近更新排序，不返回正文。

完整规则见[契约](contracts.md#m1-organize-02)，[使用/验证](zhy/materialhub/organize_acceptance.md)。


## PLATFORM-LEARNING-LOOP-02：工作台与复习计划（2026-10-22）

| 接口 | 契约 |
|---|---|
| `GET /courses/{course_id}/workspace/{domain}` | domain=materials/notes/study/practice。授权有效课程后由本域只读适配器返回course_id/domain/counts/recent/checked_at；最多6项近期元数据，不含笔记正文/题干/答案。各域独立失败/重试，统计使用只读快照 |
| `GET /mistakes/{mistake_id}/sources` | 沿原作答验证课程/归属，返回course_id与最多50项历史来源的version_id/chunk_id/document_id/title/locator/availability；失效来源不返回可访问文档身份，不猜测关联，不写历史成绩 |
| `GET /review-tasks?state=pending&offset=0&limit=20` | state=pending/all，limit 1–100。本人可访问的分页计划及账户today/timezone，排除已删课程或移出错题；返回items/total/offset/limit。旧today接口保留 |
| `GET /attempts/{attempt_id}?course_id={course_id}` | 新增可选课程复核，错配404；原省略参数调用保持兼容。不从最近100项列表猜测作答所属课程 |

计划创建/完成及改期复用原接口；改期继续传expected_due_date，409不重放。完成计划不改变错题掌握或每日答对数。前端result/mode/tab/attempt等参数只用于经授权定位，无自动生成/提交/远程发送。实现及验证见[全站整合验收](zhy/integration/learning_loop_acceptance.md)。

## M4-BANK-01 用户题库（2026-10-19）

完整补齐接口：PATCH /topics/{id}（revision/name/aliases）、POST /topics/{id}/merge（revision/target_id/target_revision）、PUT /topics/{id}/sources（revision/version_id/chunk_id/quote）；POST/GET /courses/{id}/exam-analyses、GET /exam-analyses/{id}及/gaps；POST /past-questions/{id}/split（revision/parts）、POST /courses/{id}/question-bank/merge（question_ids/revisions/stem）、GET /courses/{id}/question-bank/papers、PATCH /past-papers/{id}/metadata（expected_revision/year/variant/provenance/duplicate_of），PATCH /review-tasks/{id}（expected_due_date/due_date）。所有变更仍检查归属/课程，校正冲突409；拆合只对同卷当前题目，父题历史不重复计分。新迁移/备份版本为0020，显式兼容0019及此前版本。统计报告返回输入样本/修订、未知值和真实分母；资料/笔记/图片候选不等于已确认匹配，掌握度只从已判定作答计算。

以下均在 `/api/v1`，本人课程资源；404归属不可访问，409并发/状态冲突，422字段/题量不足。

| 方法/路径 | 行为 |
|---|---|
| POST /courses/{id}/question-bank/import | 201；title、content或version_id（二选一）、可空year、provenance；自动规则识别并持久化草稿，重复内容返回原题库身份 |
| GET /courses/{id}/question-bank?offset=0&limit=50 | items/total/offset/limit；校正管理DTO含答案，进行中作答禁止访问 |
| PATCH /past-questions/{id} | revision、stem、question_type、options、answer、blank_answers、unique_answer、topic_ids、points、explanation；保存后题目/所属卷回DRAFT，冲突409 |
| POST /past-papers/{id}/confirm | 对整份题库校验；四选项/正确键/标签/填空唯一性及逐空答案齐全后确认，缺失返回逐题原因 |
| POST /courses/{id}/question-bank/draw | 201；request_id(UUID)、topic_ids、count(1–100)、可选question_type、duration_minutes、title；匹配任一标签，不重复；相同request_id/条件返回原卷，不同条件409；不足422 |
| GET /courses/{id}/question-bank/statistics | 可抽题数/题型/标签涉及数、已确认题库数、未知年份/分值、已知分值；仅描述已导入样本，不预测考试 |
| GET /courses/{id}/exam-papers | 最近100套元数据及本人作答ID/状态；不含答案 |
| GET /attempts/{id} | 恢复本人已保存答案、冻结题目、deadline_at、grading；题目为考生白名单 |
| POST /attempts/{id}/self-grades/{qid} | 提交后对非唯一填空传correct布尔；返回自评状态，相同自评请求幂等，不混入自动得分 |

现有蓝图generate改为从题库满足题型/标签数量/分值配额，失败不落半套试卷。原include_answers与review进行中阻断，通用响应剔除答案/源题ID/引用原文等。唯一填空保存作答后在grading返回对错；答案只在提交后result返回。grading状态correct/incorrect/unanswered、pending_self_review/self_correct/self_incorrect、submitted；解答不设正确性，score仅自动题小计。新快照冻结题目、选项顺序与时长。

旧 /courses/{id}/question-drafts/preview、/demo 返回410；旧预览不能确认，旧已排队生成任务在worker派发前FAILED，不调用Provider。历史候选查询保留；AI问答/报告接口保持。账户备份格式0020，旧0012–0019包显式补M4新增默认字段。

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

## M4-IMPORT-IMAGE-02

POST /courses/{id}/question-bank/import新增default_topic_ids；响应bank_data新增content_profile/import_warnings。POST /courses/{id}/question-bank/images（request_id/title/asset_ids/layout:single|double/default_topic_ids/year）202显式排队，按内容hash去重；GET /courses/{id}/question-bank/image-jobs恢复任务。PATCH /past-questions/{id}新增illustrations（asset_id/box:[x,y,w,h]/alt）与images_reviewed；坐标规范化0–1，未审核不能确认。GET /question-bank/illustrations/{asset_id}?course_id=…&box=x,y,w,h 返回经授权、实际裁剪的PNG、no-store。DELETE /past-questions/{id}?revision=…软删除；POST /courses/{id}/question-bank/batch使用question_ids/revisions/action:delete|tag/topic_ids，原子校验。source_images只在审核返回，考生白名单仅增加审核后的illustrations；不返原图或答案。后台BANK_OCR独立租约/限时，失败仅显式重试；无新迁移。

## M4-PDF-ZIP-03 / AI-EXTRACT-04

POST /courses/{id}/question-bank/archives：multipart ZIP，201返回entries（path/kind/status/version_id或asset_id/error），文档供自动轮询后import，图片不自动OCR。GET question-bank增加paper_id；自然题号排序。GET /question-bank/ai-capabilities返回固定模型/配置状态；POST /courses/{id}/question-bank/ai-preview使用BankImport版本范围，201返回paper_id/model/endpoint/expires_at/sources；GET /past-papers/{id}/ai-preview读取有效预览；POST /past-papers/{id}/ai-confirm使用confirm_remote_send:true，202单次任务；GET /courses/{id}/question-bank/ai-jobs仅状态元数据，不轮询返回整篇原文。源失效状态SOURCE_UNAVAILABLE且不返回正文，配置变化/过期拒绝派发。BANK_EXTRACT与AI_ANALYSIS并发互斥，模型固定glm-4.7-flash，不影响原M2问答/报告配置。
# M4-TOPIC-INDEX-01

无新路由。`POST /courses/{id}/question-bank/import` 及共用导入服务产生的 `bank_data.topic_index` 包含 `version`、`existing[{topic_id,name,method,reason}]`、`candidates[string]`、`auto_topic_id`、`auto_assigned`。`method=name` 表示名称/别名命中，`sample` 表示已确认题干的关键词相似；数值排序依据不作为正确概率返回。自动匹配只填充没有人工/默认标签的新题草稿。

`GET /courses/{id}/question-bank` 在账户/课程授权和进行中考试限制下重新计算当前页建议，以反映题干和词表变化；只读，不修改历史数据。创建备选沿用 `POST /courses/{id}/topics`，本题选择沿用带 revision 的 `PATCH /past-questions/{id}`。修改后清除历史自动分配标记。分析最多取同账户同课程2000道已确认题干作参考，不读取答案；单题最多返回8个已有推荐和3个新标签备选。
# M4-TOPIC-AI-02（覆盖本地索引）

题库上传不再进行短语推荐/自动分类。`POST /past-papers/{id}/topic-ai-preview` 接收 `question_ids`（1–32个），返回 `preview_id`、`input.questions[{question_id,revision,stem,options}]`、`input.topics[{id,name,aliases,revision}]`、模型/端点/过期时间；不会发模型请求。`GET`同路径读取持久预览或任务状态，来源撤销时不返回输入。`POST /past-papers/{id}/topic-ai-confirm` 需要 `confirm_remote_send:true` 和 `preview_id`，返回202，创建BANK_EXTRACT；相同预览重复确认返回既有任务，跨窗口更换预览返回409。

完成后每题 `bank_data.topic_index` 版本为 `bank-topic-ai-v2`，包含 `existing[{topic_id,name,method:"ai",reason}]`、`candidates` 和 `reason`。不自动选用/创建标签。结果增加题目revision，题库回到草稿；修改题干/选项清除建议，人工标签选择沿用既有PATCH乐观锁。详细边界见 docs/m4/topic_ai_acceptance.md。
# M4-PDF-OCR-04

`GET /courses/{course_id}/question-bank/pdf/{version_id}`：只读授权版本，返回页数、疑似扫描/空白页号 `ocr_pages` 及本地组件状态 `ocr_available`；不OCR、不建题。PDF检测在30秒子进程中进行。

`POST /courses/{course_id}/question-bank/pdf/{version_id}/ocr`：明确用户操作，接收 `request_id,title,year?,default_topic_ids,layout(single/double),force_ocr`，返回202的BANK_OCR任务；同请求不同范围409，重复有效范围复用既有任务。`force_ocr:false` 保留正常文字页，仅OCR缺文字页；true整份OCR。

既有image-jobs接口增加 `pdf_version_id`、`force_ocr`，图片保存来源版本/页号；题目 `bank_data.source_version_id` 及新试卷快照保留来源ID。抽题/新作答/AI标签预览验证该来源仍有效，旧快照不重写。备份验证PDF源版本、任务、图片与课程，兼容历史无该字段备份。识别不更改M1解析/索引状态。
# M4-LIBRARY-DELETE-05

专用文件库：`POST /courses/{id}/question-bank/files` 上传原件，返回202的原解析Job；`GET`同路径返回题库文件和关联旧来源（附library_scope）；`POST .../files/{document_id}/move`显式将旧来源划入question_bank，不改变UUID/版本。原件下载继续使用同一授权版本接口，资料阅读列表/分页/搜索/导出排除question_bank。

单题DELETE及原batch接口增加响应revisions映射；`POST /courses/{id}/question-bank/restore`接收revisions，整库撤销另带paper_id/paper_revision。仅允许撤销人为删除、revision完全匹配的题目，恢复草稿。`POST /past-papers/{id}/delete`要求revision与question_snapshot（当前题目id/revision集合SHA-256），原子软删除整份题库并取消识别任务，响应changed/revisions/paper_id/paper_revision供撤销。题库列表新增question_count/question_snapshot；旧试卷/作答快照不变。0021迁移与旧备份兼容见docs/m4/library_delete_acceptance.md。


### M4 视觉与ZIP选择增量（2026-10-20）
- POST /courses/{id}/question-bank/archives/inspect：multipart ZIP，返回经预算/路径/CRC校验的中文成员目录，不保存成员或发模型；archives上传可附selected_paths JSON字符串，只保存选中成员，空/越界/重复列表422。
- PDF OCR请求与BankImageImport新增engine local|ai、confirm_remote_send、questions_only（默认true）、classify_topics。ai必须显式确认且配置就绪；仍用BANK_OCR持久任务。图片/PDF的图片顺序和配置不可在同request_id重放时改变。
- POST /past-papers/{id}/vision-resume：{confirm_remote_send:true}；仅本人同课程失败AI识别、原配置且尚无题目时续跑；成功页不重发。
- POST /past-papers/{id}/recognition-cancel：取消本人尚未完成的识别/归类租约，不删已入库题目/原件/历史。
- image-jobs新增engine/completed_pages/auto_topic_status，1305按服务繁忙展示。公开题库元数据不含视觉检查点、配置指纹或内部原文信封。完整备份验证检查点页的原图顺序/归属/结构，只恢复终态任务。


### M4 Markdown / GLM5.3增量（2026-10-20）
图文转写、文本拆题、标签归类模型统一glm-5.3-flash；模型/提示词身份进入发送指纹，旧预览拒绝切换模型后继续发送。新题/校正bank_data.content_format=markdown；题干、选项、解析为Markdown，简单HTML/TSV/矩形分列表格转换GFM，原始来源引用偏移不变。
GET /past-questions/{id}/markdown：本人有效题目的UTF-8 text/markdown附件，仅题干/选项，不带答案；拒绝跨用户/来源失效及进行中考试读取，未保存内容不导出。归类v3允许最多8项合法候选（建议1–3），完整展示不截断，已有标签优先/用户确认仍保留。


### M4 标签检索与批量核验（2026-10-20）
GET /mistakes 可传 topic_id，响应 topics 含 id/name/aliases/revision，旧题快照不变，名称按本人当前词表及合并链解析。GET /courses/{id}/question-bank 支持 topic_id，过滤后分页/total。POST /courses/{id}/question-bank/batch 新增 action=confirm，沿用 question_ids/revisions；全选校验后原子确认，422问题映射、409修订冲突均不部分写入。整份有效题全部确认后题库才CONFIRMED。

2026-10-20 抽题范围增量：topic_ids可省略或为空，空选从当前课程全部合格确认题中抽取；多选按任一标签匹配，不再限制最多12个抽题标签。单题标签上限不变。保持题型筛选、去重、题库不足显式失败和课程归属校验。


### 2026-10-21 M4 标签层级与自动分离
TopicCreate/TopicEdit支持parent_id（UUID或null；旧PATCH省略则保留），TopicResponse返回parent_id。层级保存在既有sources_json.hierarchy.parent_id，6级/同课程/无环/revision保护；备份验证层级，引用和合并保留元数据，合并迁移直属子节点。无迁移。父标签过滤、抽题、错题包含后代，原始题目标签快照不冗余改写。
PDF Request / BankImageImport的questions_only默认false表示自动识别与答案分离，true显式仅题目；旧任务持久配置不回写。每页自动模式2次有界调用，第二次前重新验证任务/来源/配置/取消租约，失败无自动网络重试。输出支持逐空blank_answers、content_profile，核验source_status=absent候选不入库，控制字符/错误选项/重复题号/缺题干拒绝。局部OCR仅辅助，不作为语义结论。


2026-10-21：DELETE /api/v1/topics/{id}?revision=N 删除本人同课程空标签（200 status=deleted）；revision必填≥1，无归属404、修订冲突/子标签/题目/历史合并或试卷引用/资料依据409，失败不改数据。同课程写锁，不重写旧快照。已有文件导入直接复用版本的规则/AI预览/PDF-OCR接口，无上传副本或新增识别API。


2026-10-21 M4-TOPIC-DELETE-SELFREVIEW-03覆盖前述空标签删除限制：DELETE /topics/{id}?revision=N 允许有效非空标签，软删除并返回affected_questions，当前有效题解除关联/子标签提升，历史快照不变；仍检查归属、修订和活动作答。POST /attempts/{id}/self-grades/{qid} 支持提交后所有非自动判分题（包括历史解答、缺标准答案题），自动判分题422、未交卷409、自评冲突409、同值幂等；错误写入Mistake且不修改自动score。


2026-10-21：POST /api/v1/courses/{course_id}/question-bank/save，items含1–100个BankQuestionEdit+question_id。沿用单题校正协议与权限/图片检查，拒绝重复ID，课程锁/每题revision校验，整批事务提交；失败回滚。200返回changed和revisions，不自动确认。原PATCH /past-questions/{id}仍兼容，共用校正服务。


2026-10-21 M4-REDO-API-GUIDE-05：GET /mistakes/daily-progress 返回账户时区date/target/completed/done/remaining_ids；POST /mistakes/{id}/redoes(request_id UUID)幂等开始，POST /mistakes/{id}/redoes/{rid}/submit(answer)冻结本次输入并规则判定，非自动题NEEDS_SELF_REVIEW后POST .../judge(correct)。同值提交幂等、冲突409，空答案422，无归属/已移出404。DELETE /mistakes/{id}仅已重做正确可软移出；旧错题快照与重做记录保存在detail_json附加元数据，备份验证结构及归属。
GET/PUT/DELETE /api-connection 为仅当前登录账户可操作的个人配置（无密钥回显）；PUT含revision/model/key（可留空保留），DELETE含revision；POST /api-connection/test含revision与confirm=true，仅明确确认后发送最小测试。状态configured与test_status分离，测试期间配置变化丢弃迟到结果。固定智谱端点/现有模型，原M2/M4 Provider复用，无新增迁移。

2026-10-21 M4-REDO-GOAL-08：GET /mistakes/daily-progress?goal=N（0–1000，默认3，0暂停）额外返回goal；target=min(goal,待掌握与今日有效掌握的不同Mistake ID并集)。available为未掌握数，completed只计当前掌握期从今日开始的题，最新错误撤销掌握与当日计数。GET /mistakes追加mastered/mastered_at，未掌握优先；重做/正常练习再次错误将已保留或移出同源题恢复，relapses只追加历史事件，不重复同一作答错误。DELETE仅当前已掌握可移出。目标由浏览器按账号保存；后端不新增用户设置表。

2026-10-21 M4-REDO-EXTRA-09：daily-progress.completed不再按target截断，可大于goal/target；done仍由completed>=target判定。客户端比例分母为用户goal，题量不足单独说明有效target。每日达标不限制start/submit/下一题，重复去重和再错撤回不变。

2026-10-21 M4-DISPLAY-REFERENCE-11：question_payload和新题库试卷快照新增可选display_group={key,label,order}，按本人原卷ID/显式题号生成，未知题号null；题库列表分页前按中文/数字自然顺序排序。考生public_question可含分组，不含answer/explanation，交卷result仍返回原文解答与解析。旧快照无分组保持兼容，无新接口/迁移。

## M4完整题干上下文增量（2026-10-21）

新抽题和蓝图组卷仍按子题计数；Question公开快照新增可选context_stem（安全Markdown原大题上下文）、context_illustrations（已审核插图），供作答页及整道题弹窗使用，不携带其他题答案/解析。内部context_sources仅用于同账户同课程来源校验，考生接口不下发；开始作答再次校验来源有效性。完整上下文超预算返回422，不截断；历史快照缺字段仍兼容，不重写。题目校正保存同内容标签选择时保留topic_index并设置selection_reviewed=true，新AI归类覆盖该标记，避免人工取消被自动重新勾选。

## M4审核与批量标签增量（2026-10-21）

POST /courses/{id}/question-bank/batch新增action=tag_add（去重追加），保留action=tag为替换。整批先校验归属/revision/追加后每题最多5标签，超限422且无部分写入；显式标签决定标记selection_reviewed。保存与批量核验后同步题库review_status，仅非SUPERSEDED有效题全部CONFIRMED且非空才确认。未改业务字段的保存保持题目核验状态，真实修改回到DRAFT。批量save响应新增needs_review布尔值，供提示所选题是否仍需核验，changed/revisions兼容保留。

标签上限追加规则：新设置/保存/导入/合并每题最多5标签，历史快照不删改。批量tag_add超限422详情包含limit=5及over_limit_questions数组，每项含question_id、paper_id、paper_title、number、tag_count、limit，收集全部超限题后整批拒绝；前端据此显示精确题库/题号而非只报笼统失败。

## M4-RETIRE-FILL-BLANK-16（2026-10-22）

新来源题和新抽题仅single_choice/solution；导入文本与AI旧输出fill_blank统一保存为solution，原blank_answers在缺答案时连接为参考解答。BankQuestionEdit/BankDraw/QuestionTypeQuota兼容接收旧fill_blank请求并归一为solution，公开题型枚举移除fill_blank（历史Paper及Attempt快照读取兼容仍保留）。旧填空来源启动时在线备份后幂等转换、revision递增，旧空答案元数据归档在retired_fill_blank；不重写试卷/作答/错题原始快照。账户恢复仅转换本次恢复的来源题，其他账户不受影响；新redo副本转solution，已存在redo保持。无schema迁移或真实模型调用。


## M4严格本地录入与批量身份（2026-10-28）

- `POST /courses/{id}/question-bank/files`、`POST /courses/{id}/question-bank/archives`新增表单`mode=local|ai`，默认local。本地仅严格UTF-8 Markdown，ZIP仅选中的Markdown，全部预检后保存；AI上传保留多格式，上传不代表确认发送。
- `POST /courses/{id}/question-bank/import`新增`strict_markdown`；本地文件/粘贴入口传true，原文读取校验SHA-256，使用M1原始Unicode偏移建立逐题引用及来源版本。旧内联调用兼容，不改变历史题或远程识别策略。
- `PATCH /past-papers/{id}/metadata`支持`exam_identity:{kind:exercise|past_exam,confirmed:boolean}`，身份操作要求显式expected_revision；来源/年份/卷别变化撤销原确认，来源变化与确认不能在同一请求完成；服务端维护身份revision/UTC时间。
- `POST /courses/{id}/question-bank/metadata-batch`接受`items`（1–100项），每项paper_id、expected_revision及可修改元数据；归属/删除/修订/代表卷关系全部校验后单事务保存。冲突409整批不修改，返回changed/revisions；不签署官方真实性。
- `POST /courses/{id}/question-bank/batch`新增`action=review_topics`，明确核对现有1–5个合法知识标签后标记selection_reviewed；不替换标签、不确认真题身份，沿用每题revision与整批预检。
- gaps响应新增current_pending/current_mastered，历史judged_count/error_count不回写。真题只读依据包含identity_revision/paper_metadata_revision，身份撤销/重确认使旧快照失效；完整账户备份保留声明，课程包导入清除确认并提示重新核对。


### M4-PAPER-PRACTICE-19（2026-10-28）

- `GET /courses/{course_id}/question-bank/practice-papers`：仅本人当前课程，最近200份未移除题库的`id/title/year/question_count/eligible_count/available/reason`，无题干答案；作答期间可读。
- `POST /courses/{course_id}/question-bank/papers/{paper_id}/practice`：`{request_id: UUID, duration_minutes: 1..180}`，返回原有PaperResponse草稿。整卷最多500题，不按随机抽题的100题限制截断；全部有效题目须已确认、来源有效。保留原题号与选项顺序及卷内重复题；公开题目新增可选`source_number`。幂等键与来源卷、时长绑定，跨账户/课程404、变参或未交卷409、校正未完成/超限422。沿原review/start/answer/submit接口。
- 保存答案仍以同一attempt_id/question_id覆盖；练习历史每个attempt只返回当前状态，不追加阶段行，不删除不同次作答。


### M4-ATTEMPT-DELETE-MAJOR-20（2026-10-28）

`DELETE /attempts/{attempt_id}?confirm_delete=true`：删除本人有效课程下该次作答、关联Mistake（含其重做快照）及ReviewTask，并清理其他错题上该作答的relapses事件；不删除来源试卷、题库或其他作答。必须显式确认，缺确认422，不可访问/已删除404；事务内完成，可删除进行中作答但不代提交。返回`deleted/mistakes_deleted/review_tasks_deleted`。前端点击前提示永久删除范围、未保存内容丢弃，成功清除该次恢复指针。

新练习题快照可含`whole_stem/whole_illustrations/source_number/practice_unit=major`；公开接口只提供题干、图表和原题号，不含答案解析。整卷按明确大题分组显示一次完整题干，子问仍使用独立UUID和原保存/判分接口。整卷列表增`major_question_count`，`question_count`仍为独立作答项数。旧快照保持兼容，缺完整题干不得拼造原文。


M4-DEEPSEEK-22：GET /question-bank/ai-capabilities新增vendor/endpoint字段（不含凭据），用于显示当前账户实际模型与发送目的地；既有configured/model/vision_configured保持。DeepSeek使用已存在的Chat Completions结构化适配，文字与图片任务沿现有预览/确认/账户修订路径，无重复Key表或新的自动调用接口。


M4-TOPIC-BATCH-RECOVERY-23：topic-ai-preview的question_ids可空（本人该卷全部待归类题），非空最多5000题；完整范围≤400万字符，预览返回batch_count。内部每批≤32题/24000字符为单次模型预算，不再限制用户整次32题；每批前复核租约、来源、修订和配置，事务采用。题库papers列表新增recognition元数据(status/error/completed_pages/total_pages/engine)，无正文；复用vision-resume恢复检查点。重复原题号独立保存为有页位置的草稿并警告，不推断续接。

M4-BANK-UX-DEDUPE-24：BankImport新增可选request_id（UUID），同请求同字段幂等，同键变参409，跨账户/课程404。不同请求或未指定请求时不按内容hash合并原题库。去重仅由分析和蓝图调用显式开启，按NFKC规范化及去首尾空白后的题干相同判定，忽略整卷duplicate_of标记作为过滤条件。默认题库/随机/整卷池保留重复。


M4-AUTO-CLASSIFY-26：POST /courses/{course_id}/past-questions/{question_id}/auto-classify，JSON {revision:int>=1,confirm_remote_send:true}，202返回原BankTopicJob结构；auto_apply标识自动采用任务。只接受本人当前未归类题，陈旧revision/已归类409，越权或异课程404，未同意422。沿原任务查询/取消及配置校验，成功自动关联/创建标签且不改正文或答案，失败保留原数据；AI关联selection_reviewed=false。


M4-27：POST /courses/{course_id}/past-papers/{paper_id}/auto-classify，{revisions:{题目UUID:revision},confirm_remote_send:true}，202后台任务，单库自动分批/事务采用。PATCH /past-questions/{id}新增year（省略保持，null未知，1900–2200整数）；年份仅本题，统计按此值优先。详见docs/xtc/m4_analysis_bulk_edit_2026_10_28.md。


M4-BULK-VALUES-29（2026-10-28）：上传与校正批量工具新增年份/分值，各字段支持不修改、统一设置、设为未知。勾选题目或全选本页后应用，分值是每题值，年份仅所选题；原草稿/修订/归属检查，冲突整批拒绝，改变回草稿，旧作答保留。POST /courses/{course_id}/question-bank/batch-values，question_ids/revisions及可选year/points，省略保持、null未知；最多100题，事务提交，无AI调用或迁移。


M4-IMPORT-VALUES-30（2026-10-29）：题目年份/分值移到源码折叠区上方；严格Markdown可用三级年份/分值字段自动设置，AI扫描和文本元数据沿原文读取保存。ans6两稿更新演示2023年与5/10/15分（17题总170分），明确虚构字段，仅local。78后端通过/2跳过、6Chrome、TypeScript/构建/Ruff通过，无真实模型或日常写入，人工待接收；详见docs/xtc/m4_import_values_2026_10_29.md。


M4-SELF-SCORE-37（2026-10-29）：明确分值的自评题改为输入0至满分整数得分，替代对错按钮；未知分值题仍按对错自评。交卷后展示已评得分，全部题目分值明确才显示总分，待自评明确提示；部分得分视为未完全答对，错题与统计一致。新快照冻结points_known，未知分值内部占位不计分，旧题库快照缺标志不猜分值。POST self-grades支持score或correct互斥模式，原评分同值重试幂等/不同值拒绝。Chrome两种汇总流程通过，相关后端得分范围与幂等通过。无迁移/模型或日常题目写入。先前发布在GitHub树上传阶段网络中断，没有合并；本轮评分验证后续提交，网络恢复再合并。
