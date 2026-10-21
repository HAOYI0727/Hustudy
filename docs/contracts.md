# Hustudy 共享契约（Phase 0）

## M4-BANK-01 题库抽题（2026-10-19，用户覆盖历史AI拟卷要求）

### 完整M4补齐：M4-ANALYSIS-01（同轮，实施前契约）

0020_exam_analysis基于0019：Topic追加revision=1、merged_into_id可空（应用层校验同课程重定向、禁止循环，旧ID保留）、sources_json={}（用户确认资料Citation）；新增ExamAnalysisReport Owned实体，course_id/FK、input_hash、report_json、status。报告为有界本地确定性计算，POST /courses/{id}/exam-analyses返回201，GET /exam-analyses/{id}和/gaps校验输入hash并标STALE，保留旧快照不覆盖。统计只纳入已确认独立卷/已确认叶子题和映射，未知值单列，主标签分值只加一次、次标签只算涉及；空分母null。Topic改名/合并/资料确认先校验revision，旧题/作答快照不改。材料候选通过M1搜索、笔记候选通过M3只读搜索；关键词候选明确未确认，不标AI或已确认。账户备份升级0020，旧0019及更早包显式补字段/空报告表；课程生命周期清理同步扩展。手动蓝图UI消费题库并精确验证题型/标签配额，替代旧AI三模式，不生成新内容。

POST /past-questions/{id}/split以revision和parts原子拆题，POST /courses/{id}/question-bank/merge以UUID列表/各自revision/合并题干原子合题；同卷限制，旧题SUPERSEDED保留历史但不再确认/计分，新题分值未知不分摊父总分。PATCH /past-papers/{id}/metadata支持expected_revision、可空year、卷别/来源和人工duplicate_of代表卷；同课程根代表卷、禁止循环，重复材料不进抽题/统计。标签别名归一后入库，歧义明确拒绝。旧作答不变，报告输入含样本决定/题目修订/标签修订/来源有效性，变化标STALE。独立题型与标签配额使用整数最大流匹配，不人为预设类型×标签组合。PATCH /review-tasks/{id}通过expected_due_date防止覆盖并发改期。矩阵图片仅按授权元数据候选，不识别图中文字。

新练习只抽取本人课程已确认题库，不生成新题/不调用Provider。M1提供上传/解析版本，M4经full_context/checked_chunk消费正文，扫描件须人工确认转录。普通题库文本用确定性规则识别，不用正则解析模型回复；支持题号、A–D选项、答案/解析/知识标签；不确定先草稿，确认前由用户校正。规则解析有界240000字符/400块/1000题，无静默截断。

0019_exam_bank基于0018追加M4列：PastPaper.bank_meta_json={}（来源版本/来源说明）；PastQuestion.bank_data_json={}（选项、标签ID、唯一性、逐空答案、引用、警告）、revision=1；ExamAttempt.snapshot_json={}（题目/时长冻结）、grading_json={}。旧记录保留默认值；账户备份新格式0019并显式升级旧包默认字段，迁移与漂移/往返测试后待zhy签收。

新增POST /courses/{id}/question-bank/import、GET /courses/{id}/question-bank、PATCH /past-questions/{id}（revision）、POST /courses/{id}/question-bank/draw（request_id/知识标签/数量/题型）、GET /courses/{id}/exam-papers、GET /attempts/{id}、POST /attempts/{id}/self-grades/{qid}。原蓝图generate从题库抽题，拒绝不足/不满足配额；相同抽题request_id相同约束幂等，不同约束409。POST /past-papers/{id}/confirm只确认通过校验的题目。DRAFT→REVIEWED→READY，作答题目与截止冻结。

四选项重排后标准答案同步映射；源题保持原顺序。填空唯一性必须手选true/false，多空答案用有序数组，NFKC+首尾去空白精确比较（区分大小写），不声称语义判分。唯一填空保存后可返回对错，不返回标准答案；提交后才揭示参考答案。非唯一填空pending_self_review由用户提交后自评；解答只submitted/unanswered不判对错、不计自动分。通用考生DTO白名单排除答案/原题ID/来源摘录/映射，作答中禁止题库管理与审阅答案旁路。提交和错题/复习创建幂等，跨账户/已撤权课程404。

<a id="m3-capture-text-01"></a>
## M3-CAPTURE-TEXT-01：识别仅插入文本、停用笔记AI整理（2026-10-19）

按用户最新要求替代旧M3-CAPTURE-01/PERSONAL-AI-CONFIG中的直接新建/AI流程：识别不调用NoteCreate，前端仅从当前笔记编辑区进入，核对文本后替换打开窗口时的选区；没有选区则插入光标处。校验编辑会话与正文快照，发生变化/冲突则保留识别文本并阻止误覆盖；成功插入走原撤销与自动保存。用户自行新建的空白笔记仍可接收文本。实时语音、文件识别/音频转写共用该行为，关闭不插入。

识别result.text改为各parts.text按顺序用空行连接，不人为添加页号/时间Markdown标题；parts的来源位置保留供核对。前端兼容旧任务，从parts提取文本，缺失parts才使用旧text，不用正则删除真实正文。已保存笔记不回写。

POST /note-captures/{id}/organize先鉴权与归属校验后返回410；capabilities.ai恒false。worker取消所有遗留QUEUED/RUNNING NOTE_ORGANIZE，清除租约，不读取凭据或调用Provider；历史结果保留。PUT /note-ai/config返回410，GET只返回停用状态/旧配置元数据，DELETE仍支持归属和revision校验后清除旧密钥。无新表/迁移，不影响M2配置或模型调用。

<a id="m3-editor-math-03"></a>
## M3-EDITOR-MATH-03：图形符号与结构输入（2026-10-18）

用户已确认M3-EDITOR-MATH-02已有功能验收通过。本轮借鉴AxMath文档中的分类符号面板、结构子字段与键盘导航，独立实现常用符号图形按钮/结构图标、最近使用、本地结构填写及原公式参数恢复，改进参数选区与退出结构后的连续输入。只借鉴交互，不复制商业软件代码/图标，不引入计算或识别功能。保留可见LaTeX源码、原数学库/11种生成器及标准Markdown保存；只对识别明确的结构提供字段，未知语法原样保留，不做有损重写。输入变化、嵌套、撤销/重做、401草稿、取消及触屏/键盘操作使用隔离测试验证。无新依赖/API/迁移，先契约/交接后代码；同步fzk文档与README，不提交推送。

图形按钮使用已有本地KaTeX输出与CSS；最近使用只保留当前窗口的静态模板ID。结构识别不执行宏，扫描长度/深度受限，跳过文本、注释、环境名及宏定义等不可确定区域；解析失败不覆盖源码。参数填写与源码共用单一草稿，按偏移修改而非重新序列化整条公式；既有公式的恢复字段不写入数据库。快捷键只在公式输入区域生效，Tab不困住键盘焦点。

<a id="m3-editor-math-02"></a>
## M3-EDITOR-MATH-02：公式工作区扩展（2026-10-18）

用户已确认M3-EDITOR-MATH-01手动复验通过，并要求参考LaTeX速查页扩展项目内公式编写。本轮提供可搜索分类符号/结构库、选区嵌套与参数导航、矩阵/分段/对齐表格式生成、窗口内撤销重做及本地语法速查；覆盖希腊字母、关系/集合/逻辑、运算、定界符、箭头、函数、微积分、线代、字体/重音/间距/颜色/盒子和常用学科模板。继续复用本地KaTeX及标准Markdown公式，不引入完整TeX文档编译或不受限宏包，不下载外部字体/发送笔记。可编辑源码始终保留，复杂结构显式预览确认，取消不写正文；保护旧选区、401草稿、UUID引用与渲染资源边界。先契约/交接后代码，验证全部内置模板、嵌套编辑/矩阵/撤销和双引擎响应式，更新fzk文档，继续不提交推送、搁置AI识别。

无API/schema/依赖变化。生成器仅构造LaTeX，所有内容仍经共享受限渲染与Markdown插入校验；符号库为静态本地数据，参数位置仅窗口内状态，不写入笔记。矩阵/方程组行列有界，超出生成器的内容可直接编辑源码。上轮手动通过不代表本轮新增功能已验收。

<a id="m3-trash-01"></a>
## M3-TRASH-01：笔记回收站与到期清理（2026-10-18）

先提案后本地实现，0016_note_trash待zhy评审整合；[实现与实际验证](fzk/note_trash_acceptance.md)。复用Note.deleted；新增UTC deleted_at、purge_after可空时间。新增note_trash_policies（OwnedResourceMixin、user_id唯一、retention_days可空/1–365、revision≥1），无策略记录等价30天/revision0；null关闭自动清理。旧删除记录从迁移/旧备份升级时起计30天，活动笔记时间为空。策略变更按原deleted_at重算所有已有回收站期限，缩短时可能下次worker立即清除，UI先确认。

保留DELETE /notes/{id}的204兼容语义，新增时间戳；POST /notes/trash/batch支持trash/restore/purge及1–200个{id,revision}，全部归属、状态、版本先校验，原子提交。GET /notes/trash分页返回账户全部课程的回收站摘要（无正文）、总数与由全部id/revision生成的snapshot；POST /notes/trash/empty仅在snapshot一致时清空账户回收站，变化返回409；GET/PUT /notes/trash/policy用revision防覆盖。静态路由在/notes/{id}前注册。GET无删除副作用。

恢复保留原UUID、正文、标签、双链、图片和资料引用；原文件夹已删恢复为未归档，原课程失效须传本人有效fallback_course_id，不能重新激活已删除课程或资料。软删除不删关系；保存指向回收站笔记的UUID仍保留关系以便恢复。彻底删除移除NoteLink/AssetReference/该笔记Citation，不删除Asset或Document。已有导出资格校验继续生效。worker每分钟清理最多200条到期记录，用账户写锁重新核验截止时间，与恢复/策略更新互斥；离线期间不运行，重启处理积压。

完整账户备份schema升0016，M3适配器包含策略、回收站时间且校验其一致性；显式兼容0012–0015。普通MD/ZIP不包含回收站。前端继续中央列表勾选，批量移入回收站与回收站管理弹窗，彻底删除/清空确认、草稿与401/409保护不变。无新依赖或外部模型调用。

<a id="m3-layout-drag-01"></a>
## M3-LAYOUT-DRAG-01（2026-10-18，交互契约）

中央笔记管理列表集中选择、批量标签/移动/导出；侧栏只显示文件夹和笔记标题。管理与编辑切换保留未保存草稿、撤销历史；文件夹筛选不强制切换或覆盖正在编辑的笔记。导入/导出/标签/推荐等在模态对话框内，键盘焦点限制在窗口内，关闭返回触发点；请求处理中阻止关闭，导入关闭后重开保留每文件请求UUID及结果。拖动仅接受本页创建的内部对象：单篇或最多200篇选中笔记通过既有POST /notes/batch移动，文件夹通过PATCH /note-folders/{id}变更parent_id；携带拖动开始时的revision，失败不更新本地归属。文件夹不能移入自身/后代，服务端保留同课程/深度/重名校验。未归档接收笔记、根目录接收文件夹；同目标无操作，列表仍按名称排序，不新增手工序号。触屏/键盘继续使用移动按钮。无API/schema/备份/worker变化。

<a id="m3-organize-import-editor-01"></a>
## M3-ORGANIZE-IMPORT-EDITOR-01（2026-10-18，实施契约）

0015_note_folders提案新增M3 NoteFolder（id/user_id/course_id/parent_id/name/revision/created_at/updated_at），Note新增可空folder_id，旧笔记默认未归档。父子与笔记须同账户同课程，最多6级/每课500文件夹，同级名称不区分大小写去重，移动拒绝循环。GET/POST /note-folders、PATCH/DELETE /note-folders/{id}均鉴权；修改/删除携带revision，冲突409；删除仅允许无子目录/有效笔记的空文件夹。Note创建/更新追加folder_id，未传保留、null移出；与正文共用revision。由zhy整合迁移，现有UUID引用保持。

POST /notes/batch接收1–200个{id,revision}、add_tags/remove_tags及可选folder_id，先锁定账户、检查全部归属/版本/标签上限，再原子更新；任一冲突409、越权404、超限422，均不部分写入。标签改名/合并/删除使用此接口移除旧标签并可选加入新标签，处理范围在界面明确展示。

POST /notes/import-markdown接收一个multipart文件、course_id、folder_id、request_id与JSON tags。仅.md/.markdown、UTF-8（可含BOM）、每份≤2MiB，无NUL；标题为文件名去扩展名，正文完整保留，返回NoteResponse。前端一次最多20份，顺序导入、统一标签/文件夹，逐项展示成功或失败；重试沿用相同request_id与内容，不重复创建，不自动重放认证/网络失败。图片附件不随单独MD文件隐式上传，界面提前说明。

新选择ZIP按NoteFolder树分配安全路径，未归档笔记位于根目录；根images保留给引用图片，目录/文件重名按稳定UUID顺序分配可读序号，层级相对图片/双链有效。账户备份升级0015并包含文件夹，0012/0013/0014恢复显式补空目录集合及folder_id=null；验证循环/跨课程/深度和名称规范，按父先子后恢复。

分类建议为本地规则，以文件夹名及已有笔记标题/标签解释推荐依据；只推荐当前课程未归档笔记，不自动移动，不宣称模型推理。编辑器增强不改变Markdown存储或安全渲染契约。

<a id="m3-citation-lifecycle-01"></a>
## M3-CITATION-LIFECYCLE-01：资料引用管理与保存恢复（2026-10-18）

POST /notes/{id}/citations按本人笔记+version_id+chunk_id+精确quote去重，重复返回同一Citation（兼容201），不重复反链。新建笔记的citations同样去重，每篇新建/追加最多50条；追加超过返回422。同笔记引用写操作取得SQLite写锁，和删除笔记串行；保持来源授权及逐字校验。无新表/迁移，旧重复记录不自动删除。

新增DELETE /notes/{note_id}/citations/{citation_id}：仅本人有效笔记且引用属于该笔记可移除，204；笔记/引用不存在或越权404。移除不删原资料/正文/其他引用，也不修改笔记正文revision；引用ID不可变，因此按指定引用删除不覆盖其他窗口编辑。后续反查不再列出此引用，已有导出包引用该ID时撤销下载。来源已失效仍可移除。

CitationResponse追加可空document_id/document_name/version_no，仅经M1 active_version/active_document接口取得本人有效来源；失效来源不补造元数据。GET列表重新判断有效来源，失败不显示空结果冒充无引用。页面独立刷新/重试/确认移除，保留未保存正文；旧字段及M2创建草稿协议不变。

前台活动页停止输入2秒启动自动保存，隐藏页不发新自动保存请求，回到前台重新计时；已发请求可以完成。网络失败保持原恢复策略，401/409/业务失败仍等显式处理，不因visibilitychange自动重发。

<a id="m3-batch-images-01"></a>
## M3-BATCH-IMAGES-01：选择导出与批量图片（2026-10-18）

覆盖下方历史默认值：新建POST /note-exports的include_images默认true，页面始终发送true；API显式false仍兼容，已冻结请求/旧包不变。ZIP只包含选择笔记的标题.md及其实际引用的有效图片，images按Asset ID去重；不包含未选笔记、其他图库图片、清单或重复原文。路径URL编码，整包解压后可由标准Markdown阅读器加载。已删除图片显示不可用，外部URL不抓取，文件损坏拒绝生成。

两个前端上传入口共用顺序批处理，最多20张、每张非空且≤10 MiB、PNG/JPEG/WebP；仍逐张调用M1授权上传/真实类型校验，不新增批量后端或跨模块写表。成功按选择顺序插入，失败列出文件名且仅显式重试未完成项；认证/网络/限流/服务错误停止队列，网络响应丢失提示先核对图库，避免盲目重复上传。编辑器上传期间输入不丢失，切换/离开有保护。无迁移/依赖变化。

<a id="m3-simple-export-01"></a>
## M3-SIMPLE-EXPORT-01：日常笔记导出与图片管理（2026-10-18，默认值由上节更新）

本轮用户要求覆盖下方历史复杂知识库包布局。POST /note-exports接收request_id、可选note_ids（1–2000个唯一UUID；省略为当前全部有效笔记）、include_images（默认false）。创建时冻结选择ID，worker取这些笔记的已保存快照；缺失/越权选择整体拒绝，不静默加入其他笔记。相同request_id只接受相同选择/图片选项，重试不扩大范围。参数存既有sources_json.request，无新迁移；老记录保留旧布局，响应layout=legacy，新包layout=simple。

新ZIP根目录只放“笔记标题.md”，同名/大小写/非法字符按已有安全命名分配序号；不生成sources、manifest、README。选中笔记之间转换相对链接，未选择的目标显示“未随包导出”，不冒称已删除；未选图片时保留说明和“未附带图片”文字，勾选include_images时增加images/图片名称.ext并转换链接。资料引用以可读摘录/定位附在Markdown，仍验证来源和hash；校验留在内部，无CMD使用要求。单篇下载头和页面下载名统一标题命名。旧包不重写，页面明确旧版需重新导出。

笔记页复用M1 AssetLibrary及已有权限/revision接口管理所属课程图片：预览、名称/说明/标签、查找/引用位置及确认删除。图库未保存或正在操作时阻止切换笔记；图片变化刷新插入选项和正文预览，引用保持UUID。删除图片保留笔记正文并显示失效，不隐式删除笔记内容。

<a id="m3-image-naming-01"></a>
## M3-IMAGE-NAMING-01：图片上传和可读导出名称

本轮覆盖先前仅UUID命名的ZIP布局：下载名为`Hustudy-笔记知识库-YYYY-MM-DD_HH-mm-ss-SSS.zip`（创建时间，账户时区），NoteExport响应新增filename，下载接口与页面使用同一名称。无新数据库字段/迁移；既有记录也可按创建时间命名，但旧包内路径保留，须重新生成才能使用新布局。

新包notes/课程名/笔记标题.md、sources/课程名/笔记标题.md及assets/课程名/图片名称.ext。路径清理控制字符/Windows非法字符、保留名、末尾点/空白、限制长度，按大小写不敏感规则分配唯一名称，同名用（2）、（3）等编号。UUID始终保留manifest实体ID。所有目标路径预先分配；跨课程/同名笔记链接按实际相对路径进行URL编码，图片同理。清单格式1和哈希字段不变，读者/校验器以manifest路径为准，不拼接UUID文件名。

笔记编辑器新增上传并插入：复用POST /courses/{id}/assets，PNG/JPEG/WebP、最大10MiB，实际解码/归属由M1校验。保存到被编辑笔记所属课程，未分类笔记使用页面所选课程；上传成功插入既有asset UUID语法并更新选项，来源未知不补造。上传阻止切换/离页，上传中继续输入则完成后追加到最新正文而非覆盖输入；失败保留原草稿、无无效占位，不自动重传。原有图库选择仍可使用。

<a id="m3-note-tags-01"></a>
## M3-NOTE-TAGS-01：笔记标签（2026-10-17，fzk 分支提案）

输入是本人笔记的 tags 字符串数组，输出为持久化、规范化的有序标签；关联 FR-09/10/11、C02/C08/C09。先记录契约，再实施；迁移0013_note_tags由 fzk 在功能分支提供，待 zhy 评审整合，未合并/签收。

- Note 新增 JSON tags，非空默认[]；0012旧笔记回填[]，不改正文、UUID、引用、revision或时间。
- POST /notes 可省略tags（[]）；PATCH /notes/{id} 可省略（保留）、[]（清空），显式null拒绝。最多12项，单项trim后1–32 Unicode字符、禁止控制字符；按大小写敏感的完整文本去重且保留输入顺序。tags与title/content在同一次revision更新中原子保存。409.details追加server_tags，既有冲突字段保留。
- GET /notes 可选q（≤200字符，标题/正文/标签子串）、tag（≤32字符，单标签精确匹配），与course_id和归属同时过滤；不把用户输入当LIKE通配符。note-search继续独立分页，增加标签匹配而不改返回字段；标签命中不伪造正文高亮。
- 笔记编辑器可添加/移除标签，标签随正文自动保存，冲突显示服务器标签；本地标签输入/草稿保留，重新登录不重置。列表可组合关键词与单标签筛选；双链目标依然来自未筛选列表。
- 完整账户备份schema_revision升级0013_note_tags，标签经M3适配器导出/校验。只对0012_account_archives旧备份显式补缺失tags=[]；新版本缺字段/非法标签仍拒绝，旧版本程序不能恢复新备份。单笔记.md正文导出格式保持，独立知识库ZIP留下一切片。
- 共享影响仅备份版本协调与Note响应附加字段；M2旧createNote不传tags仍有效。验证使用隔离临时库，不自动发送真实AI请求。

## 2026-10-17 M2-TOPICS-REUSE（最新增量）

- 新候选信封`per_question_topics=true`，提示词v5。模型每题返回`topic_ids`非空、无重复且属于请求所选Topic的子集；不再统一附加全部目标。按题展示知识点名称并在既有QuestionDraft JSON保留；旧信封不重写。此项只校验关联范围，学科相关性仍需人工审阅，不冒称已实现知识点题数配额。
- 三种真实任务预览响应增加`reusable_result`（可空）：只匹配本人、同课程、相同规范化请求信封/实际来源快照、相同模型/端点及当前提示词版本，且原任务成功、结果grounded/real/完整、全部引用仍可用、考点/参考原题未变化。仅检查最近100条相同请求的成功记录，失败、部分报告、演示和旧提示词均不复用。复用不以历史列表代替依赖检查，不含密钥作为缓存键。
- POST `/remote-queries/{id}/reuse`，请求`{result_id: UUID}`，返回既有`AIResultResponse`。仅未提交且未过期的本人预览可用；服务端重新匹配与校验来源/模型/依赖，失配409，归属不存在404。不创建Job、不改原AIResult、不调用模型。用户仍可选择勾选确认后重新生成；预览命中不自动取代生成。
- 复用匹配包含正文hash和偏移等完整来源快照、报告学习模式、候选考点/原题快照及题型/数量/分值等约束；匹配保守，资料名称等元数据变化也可能不命中。无需数据库迁移或新共享schema表。

## 2026-10-16 M2-CANDIDATES-01（当前增量）

用户取消M2按日期分段的限制，按依赖持续推进。本轮继续复用RemoteQuery/AIResult/AI_ANALYSIS，无迁移。候选请求以`hustudy:question-drafts:v1\n`加严格JSON保存，普通问答禁止此保留前缀。确认/派发/完成均复核有效来源及M4只读依赖快照。不得直接查询或写入M4业务表，使用exam_ai_context适配器；适配器只负责读取与快照校验，不commit。

- GET `/courses/{id}/question-draft-context`：本人课程Topic与已确认原题摘要（无答案）；原题必须题目和父试卷都CONFIRMED。不提供教师标注/历史频率/个人掌握度。
- POST `/courses/{id}/question-drafts/preview`：goal、version_ids、可选chunk_ids（≤6）、chapter_id（必须为范围中的版本UUID）、topic_ids（1–4个）、type（single_choice/boolean/short_answer）、count（1–6）、points（正数≤100，最多2小数）、difficulty_label、mode（historical/variant/weakness）、original_past_question_ids（≤6，variant必需）。接受M4旧枚举true_false/history_blueprint/topic_variant/weakness_practice并规范化，输出只用需求标准枚举。所有配置、原题正文、目标Topic和实际材料须在确认预览可见。
- 当前M4没有章节UUID实体：候选chapter_id是资料版本UUID，chapter_ref_kind=document_version。不得直接把该ID当正式蓝图章节；M4必须映射并执行蓝图配额/状态/总分检查。historical只按用户指定结构生成，weakness无作答数据时明确自选弱项，不能编造历史统计或个人掌握度。
- 候选结构含服务端question_id、chapter_id、type、stem、options、answer/rubric、points、explanation、topic_ids、difficulty_label、mode、original_past_question_ids、material_citations、generation_status=draft。数量/类型/分值/题干hash/选项/布尔答案/rubric和引用均校验；拒绝同批重复及与参考原题完全规范化相同的题干。模型输出只能选择提供的参考ID，不能制造依据。
- GET `/courses/{id}/question-drafts`、GET `/question-drafts/{id}`：持久候选与失败历史。成功候选是UNREVIEWED，只有课程作者/集成方使用，不是考生接口，不能将含答案JSON传给正式作答页。
- POST `/courses/{id}/question-drafts/demo`：仅项目自制fixtures/materialhub_demo.md完全匹配的有效来源，固定Topic与确定性题例；未知材料返回insufficient_evidence，不调用Provider、不创建任务。不冒充真实生成。演示输出也经过相同校验。
- 报告预览新增可选chunk_ids，服务端逐个校验归属/版本/有效性，按选中片段选择（原接口不传时保留顺序选择）。普通问答同样支持显式片段。覆盖快照包含用户实际选取的范围，不静默扩大发送。
- GET `/courses/{id}/ai-results`：最近20条普通课程问答（排除报告/候选），读取重新验证引用。错误只白名单返回供应商数字code和有限Retry-After秒数，不返回原始body/message或密钥；未知429不猜额度原因，不自动发送重试。

## 2026-10-16 M2-STUDY-REPORT-01 契约

成员gcx负责M2、xtc负责M4。教学报告复用RemoteQuery/AIResult及AI_ANALYSIS；不改数据库schema。RemoteQuery.query以保留前缀`hustudy:study-report:v1\n`加JSON保存服务端生成的请求信封（goal、scope_version_ids、coverage、study_mode）；普通问答拒绝此前缀。预览/确认/worker均使用同一不可变信封，不能由确认正文替换范围。既有备份JSON原样保留，恢复不派发。

- POST `/courses/{id}/study-reports/preview`：goal（1–2000字符）、version_ids（1–20个UUID）、study_mode（preview/systematic/revision）。按版本正文顺序选取有效片段，最多6段/每段2000字符/共8000字符；返回实际覆盖数量和截断提示，绝不声称自动完整覆盖全章。空范围返回409/details.status=insufficient_evidence，不调用模型、不写成功报告。
- 沿用 `/remote-queries/{id}` 的GET/confirm/cancel；响应新增request_kind（qa/study_report）和report_scope（普通问答为null）。确认严格true、15分钟过期、单次派发、来源复核/取消租约与问答一致。单次报告输出上限6000 tokens，绝不自动重发。
- GET `/courses/{id}/study-reports`：最近20条本轮报告结果（含失败），GET `/study-reports/{id}`：本人有效课程的持久结果。响应沿用AIResultResponse，成功result含study_report、可导入笔记的answer Markdown、去重citations、scope/coverage、model、prompt_version及UNREVIEWED。
- 模型只输出严格结构：status/ reason/ report；grounded须有summary、learning_goals、prerequisites、learning_sequence、topics（解释、misconceptions、labels、evidence）、examples和3–5个self_checks。每个知识点/例题/自测均有实际发送原文evidence；模型不能指定持久ID/审阅状态/来源版本。服务器转换为Citation并分配topic UUID；标签仅ai_suggestion，本轮未接教师/真题证据。
- Citation来源失效时，顶层及报告内引用同步unavailable；报告保持历史文本，不再允许失效来源保存新笔记。候选结构与事实正确性分别验收，schema通过不代表学科事实通过。

M4候选接口本轮仅在docs/gcx/m2_plan.md记录后续对接计划，不宣称已实现；正式QuestionDraft应遵循需求附录，并先统一M4判断题/模式枚举。

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

### 完整固定报告与公开候选结构补充

POST `/courses/{id}/study-reports/demo`接受ReportPreviewRequest，固定自制资料返回完整StudyReport；未知输入/不含目标片段返回insufficient_evidence，不写成功报告、不创建AI任务。旧版本演示端点转用此实现，报告历史同时包括zhipu-study-report-v1/demo-study-report-v1；query.history排除它们。

`schemas.question_drafts.QuestionDraft`为服务端持久/交接结构，生成前的ModelQuestion与它分离；规范化题干hash放结果顶层stem_hashes。JSON schema发布于docs/gcx/question_draft_schema.json。Chapter临时版本身份、真实目标依赖和正式试卷边界仍按本节定义，不凭可导出就声称已接通M4。所有样例均为自制资料，不含用户密钥。

## 2026-10-16 M2结构化输出诊断补充

保持既有错误响应形态。Provider语法错误使用INVALID_JSON，结构不符保持INVALID_OUTPUT并在message中给出最多3项schema白名单字段路径及固定中文原因；禁止返回模型原文、未知字段名、输入值或Pydantic原始错误。提示词可增加输出示例，不改变QuestionDraft契约，不自动重发。

## M2-LABEL-REVIEW-01：FR-38标签审阅草稿

AIResult及其中ReportLabel保持不可变，本轮不新增API或数据表。前端维护独立报告/引用快照与用户标签列表，每知识点0–3项，每项kind限key/difficult/exam、reason去空白后1–1000字符；拒绝相同kind重复标签。原始AI标签与用户整理在保存的Markdown中分段留存，用户整理不宣称teacher_mark/observed_exam或整报告已审阅。显式从标签审阅转正文编辑后，用户确认通过现有POST /notes保存，Citation按快照交由M3现有接口重新检查。切换模式或新AI结果不改变该草稿；替换/返回重建正文前确认，取消/失败不覆盖其他笔记。

M2-LABEL-REVIEW-01同时补main_idea 14.1的教学结构：topic增加可选concept_group、related_concepts（目标报告知识点名与关系说明）、breakthrough_steps，report增加可选review_suggestions。旧JSON缺字段按空值兼容，不重写旧AIResult。关系指向必须属于本报告且非自身/不重复，解释依据沿用该topic经校验引用；层次与步骤为AI学习建议，不冒称课程大纲。新提示词v2要求尽可能基于证据填写，不凭空补足。固定自制示例同步提供，前端/Markdown审阅草稿均保留。无数据库迁移。

## M2-MODEL-53-FLASH（2026-10-17）

用户明确要求将当前运行副本Hustudy-main切为GLM-5.3-Flash。先约定再实现：配置允许旧glm-4.7-flash与新glm-5.3-flash，默认新模型；本机.env只替换HUSTUDY_LLM_MODEL，密钥等其余字节原样保留且不展示。配置脚本提供模型选项并默认新模型。新模型按官方仅支持thinking.enabled，reasoning_effort=low以控制思考预算，保持JSON模式/单次确认/超时/输出上限/引用校验，不展示reasoning_content，不自动发起真实或计费调用，不改数据库或其他模块业务。旧模型/旧历史仍兼容，切换后旧模型预览须重新生成，后台未派发旧模型任务拒绝派发。文档/测试/交接同步，原已上传83项副本不自动改写。
# M2引用失败反馈补充（2026-10-17）

M2-REPORT-CAPACITY：报告v6。取消把短展示建议当生成硬约束：learning_goals/prerequisites/review_suggestions各≤32项、learning_sequence≤64项、topics≤32项、examples≤12项、misconceptions/breakthrough_steps/related_concepts≤32项、每处证据≤64条、总去重引用≤256条；summary≤8000、explanation/answer≤12000、question≤6000，名称仍≤200，标签理由仍≤1000、关系描述≤3000。不截断/丢弃超过旧上限的内容，逐项解析与引用校验不变；来源范围/响应1MiB/token预算不变，自测3–5及标签合法来源保留。报告专属中文字段与实际/允许数量诊断，不放宽问答/候选schema。M3单篇50引用仍不变，超限报告需按更小范围整理笔记。历史v5允许读取。

M2-REPORT-SELFCHECK：报告v5。严格ReportOutput/TeachingReport/ReportExercise契约不放宽；模型接收层单独DraftSelfCheck只允许缺省/空evidence被识别为无依据原题。生成时丢弃该类自测，保留有引用自测；以已逐字校验的知识点解释/原文摘录/例题作为基础自测模板补足3项，再按严格TeachingReport校验。新题generation_origin=rule_generated和validation_notices由服务端生成，页面/Markdown/笔记提示保留。不把无引用原题挂到任意引用、不解析原始供应商错误体、不额外调用模型；非法引用/其他缺字段仍失败。

分批可见性补充：运行中已完成部分通过一个明确partial=true的内部AIResult中间草稿呈现（prompt_version=m2-report-progress-v1），该草稿允许随完成计数更新，不改写已发布成功/失败结果。普通历史不列内部草稿；最终/失败产生独立公开结果。前端按结果ID、状态及完成计数更新，不会因草稿ID相同漏掉新部分。取消后的已完成草稿仍可读，按部分保存笔记遵守M3原50处引用上限。

M2-REAL-MATERIALS：新报告预览batched=true，最多400正文片段/240000字符，超限明确422而非隐式截断；全文保留，按8000字符/32段分批，批次计划及最多调用数在确认前显示。每次worker只处理一批，批次成功checkpoint使用内部prompt_version=m2-report-checkpoint-v1的AIResult，ID为请求/批序确定UUID，不进入普通历史。父任务有批次数/成功数/预期字符，成功批不重发；失败/取消/租约失效需POST remote-queries/{id}/resume与confirm_remote_send=true显式确认；恢复重验来源/配置，旧恢复备份不自动发送。单批总预算120秒，网络超时不自动重试；未完成报告不显示为完整成功。最终result.study_report_sections保留每批独立教学报告，result.answer为分节Markdown，不额外AI汇总调用；学习报告每节3–5自测，不虚构跨节推理。源片段超过2000字符时拆连续子段并保留chunk_start，引用偏移还原到原chunk。

候选上下文最多128段/32000字符，超限提示缩小范围；普通问答仍为相关片段检索，不宣称整份课程分析。报告/候选证据支持当前请求内excerpt_id（400字符连续原文），兼容旧source_id/quote逐字检查。选项重复仅比较Unicode规范化并保留标点/大小写/空白，不再删除代码运算符。答案只有唯一精确匹配选项正文时可转为该选项ID并明确提示，其他情况不猜测；题型/标签/引用保持校验。用户资料不自动发送，BYOK/共享解析器不在本次改动。

M2-REPORT-STRUCTURE：报告提示词v3。可选related_concepts只保留指向本报告其他唯一知识点的首条有效链接；自指、不存在与重复链接删除，服务器在study_report.validation_notices及Markdown中写固定提示并计数，不含被删模型内容，不猜测或重写目标。知识点重名、必填结构缺失、错误标签与引用仍整次拒绝；报告重名/顶层状态不一致提供固定安全说明。新提示不在模型JSON中接受validation_notices，该字段由服务端生成。UI将INVALID_OUTPUT/INVALID_JSON显示为“输出格式不符”，既有provider_error兼容。

M2-QA-EXCERPTS：问答提示词v2将已确认的sources.text按最多400字符切成连续摘录，以sources[].excerpts[{excerpt_id,text}]发送，原文字符不增加、不改写；source_id保留，编号仅在当前请求内有效。模型evidence优先输出{excerpt_id}，服务端从本次摘录表恢复source_id/quote，再执行原文/归属/撤权校验。未知编号整次拒绝，兼容旧{source_id,quote}并严格检查，不接受两种格式混填。不改报告/候选Evidence、API预览来源或持久化引用结构，无额外请求/自动重试。编号选择仅证明引用存在，不证明答案受其支持。

INVALID_CITATION仍使用provider_error兼容状态；错误消息区分片段ID不在发送范围、摘录不是对应片段连续原文，不包含模型返回值。M2结果徽标展示“引用校验失败”，不得据此宣称平台不可用。候选提示版本升v3，强调source_id与版本/Topic/原题ID不同；不改变精确引用规则、不自动修复或重发。历史失败结果不改写。

<a id="m3-portable-notes-01"></a>
## M3-PORTABLE-NOTES-01 补充契约（2026-10-17，工作区待集成）

知识库ZIP范围为当前账户全部有效笔记（包括跨课程及未分类），不受页面搜索筛选影响。持久NoteExport关联NOTE_EXPORT ProcessingJob；请求UUID幂等，每账户最多20条记录且同时1个活动任务，最多3次尝试。租约180秒，单次打包120秒、2000篇笔记、10000图片/引用、256MiB文件、16MiB清单预算。失败/取消不发布部分包；删除记录取消租约，迟到worker丢弃输出。

包内notes/为可读Markdown，相对双链指向同目录UUID.md，相对图片指向../assets/UUID.ext；sources/为逐字UTF-8原始正文。manifest.json保留标题/标签/revision/课程UUID、两种正文hash、图片hash及来源定位/Citation摘录hash。失效引用显式标记，不猜测替代来源；不抓取外部图片。来源/笔记/图片删除或撤回后历史包不可下载，重新导出生成当前快照。单篇.md沿用原接口；知识库ZIP不是全账户恢复包。

迁移0014_note_exports只新增派生控制表；账户备份manifest版本升级，0012显式补空tags，0013原样校验，其余版本拒绝。删除笔记支持可选revision查询参数，UI始终发送；旧无revision调用兼容。409返回服务端正文/标签且保留本地，删除后双链显示失效。前端仅网络失败在online/重新可见事件恢复自动保存；401/409/业务错误保持显式重试。

网络失败还可在页面可见且浏览器在线时每15秒恢复保存尝试；后台不主动重试。POST /notes可选request_id UUID作为笔记UUID，同账户重复提交完全相同的初始内容/标签/引用返回原笔记，不复制数据；内容/版本已变化返回409（含server_id），删除/跨账户标识返回404。旧调用不传request_id兼容。编辑器保留第一次创建的请求快照，收到结果后再按revision保存等待期间的新修改，防止响应丢失造成重复笔记。

双链目标从本人全部有效笔记解析；课程目录和标签筛选仍只显示当前课程。跨课打开后提示所属范围，更新不附带当前页面course_id，防止无意移动笔记；图片选择切换到被编辑笔记所属课程。跨课/未分类链接在ZIP中同样转换为相对路径。


## M3-EDITOR-MATH-01（2026-10-18，fzk）

用户暂时搁置AI识别开发，本轮只优化Markdown编辑器。参考用户截图改为分组线性图标工具栏，保留中文悬浮说明/aria-label、键盘操作及触屏热区；不复制截图素材，不引入另一套图标体系。新增本地LaTeX公式编辑弹窗，行内/独立公式、常用模板/符号、即时预览与错误提示、选区插入和原公式修改；标准$...$/$$...$$保存，笔记预览真实渲染公式。渲染禁用可信HTML/外部资源，限制公式长度及宏展开，不改变UUID双链/图片/安全Markdown。保留撤销、草稿/冲突保护、分屏和专注；只有用户确认插入才修改正文。更新依赖许可与锁文件，覆盖390/1440布局、公式插入编辑撤销及安全回归；同步fzk文档，不提交推送，不继续AI识别功能开发。

## M4-IMPORT-IMAGE-02（2026-10-20）

用户授权：支持仅题目/题目与解析的内容判别；显式可选本地图片OCR，批量有序/单栏双栏和按题号切分，保留原图与切分区域核对；附件插图独立上传或从原图裁取，仅经人工确认不含答案的插图可进入作答。源图和OCR文字不作为正确答案依据。题目删除使用SUPERSEDED保留历史并退出题库、统计与抽题，revision/归属/进行中作答保护。批量标签、统一审核确认和较大触控选择控件减少重复动作。

契约：复用0019 JSON字段，无新迁移；PastPaper.bank_meta保存BANK_OCR任务参数与内容判断，PastQuestion.bank_data保存source_images（仅审核）、illustrations（M1 asset UUID +规范化裁剪框/说明）、images_reviewed。BANK_OCR使用ProcessingJob租约，单批20图、每图M1限制10MiB/2000万像素；子进程限时，失败显式重试且不自动发送网络。题号与页图区域关联；跨页续题接续，不确定版面人工拆合。图片读取/附加/裁剪通过M1归属与课程验证，旧快照不重写、备份显式校验新增JSON引用。

接口：POST /courses/{id}/question-bank/images（asset_ids/layout/request_id/title/year）显式入队，GET /courses/{id}/question-bank/image-jobs 查询恢复；DELETE /past-questions/{id}?revision=… 软删除；POST /courses/{id}/question-bank/batch（ids/revisions/action/topic_ids）原子标签或删除。原PATCH新增illustrations/images_reviewed；原import增加default_topic_ids。考生只返回核对后的illustrations，不包含source_images。新增OCR独立依赖锁，不安装语音组件。先自动化隔离测试与本地实际OCR样例，再文档记录；未提交/推送、不代签用户试用。

## M4-PDF-ZIP-03（2026-10-20）

用户指定本机6-ans.pdf复现：PDF上传后自动解析→索引→题库拆分→立即聚焦并展开题目；保留已有资料手动导入入口。针对“题目N+组内编号+无答案标签”按明确问句/指令终止行分离提供的参考解答，稳定组号-小题号，跨页续文不丢；标注规则分离需核对，不验证或改写教材答案。解答题提供参考解答编辑/交卷后查看，仍只检查提交。

新增POST /courses/{id}/question-bank/archives（multipart zip）返回逐条document版本/image UUID/失败/跳过原因；ZIP不写原成员路径，限制50MiB压缩、128MiB解压、40有效文件、20图片、比率200，拒绝绝对/父目录/盘符/重复名/符号链接/加密/嵌套压缩，预检全部后通过M1保存。支持PDF/PPTX/DOCX/MD/Markdown/TXT/PNG/JPEG/WebP，系统杂项显式跳过。文档自动解析与题库导入；图片仅进入待选择列表，不自动OCR。GET题库增加paper_id过滤，原BankImport加解析规则版本以防旧错误导入幂等复用。原文/版本/Citation保留，旧作答不重写，无新迁移；不提交推送、无真实模型、用户PDF不加入公开fixtures。

## M4-AI-EXTRACT-04（2026-10-20）

用户授权核对并接入现有接口免费模型。已核对智谱官方GLM-4.7-Flash页面和发布公告：文本/JSON、同一chat/completions端点，免费模型限流/账户权限仍以平台为准。本机mock且未配置key，不能真实调用或伪造成功；不搜索或输出密钥。M4专用固定glm-4.7-flash复用M2 ZhipuProvider.structured，不改M2问答/报告默认模型。题库AI仅拆分用户已有原文，以schema返回题干/解答/解析的行号，由服务器取回文字；不生成新题或补答案，不直接采纳自由聊天。

新增ai-capabilities、ai-preview（版本+title/default_topic_ids）、ai-confirm（preview ID/confirm_remote_send=true）及ai-jobs；PastPaper JSON保存不可变预览/版本范围/15分钟到期，BANK_EXTRACT持久任务单次派发，确认前无网络；结果有效来源及行号/题目覆盖校验后原子入库。规则与AI两种识别方式明确，AI确认前展示完整发送正文/目的地/固定模型，拒绝不发送。无新迁移、不自动调用模型或填写真人验收。
# M4-TOPIC-INDEX-01（2026-10-20）

上传题库的所有入口共用本地知识点索引：同账户同课程有效 Topic 名称/别名优先，英文术语按词边界匹配，合并标签解析到现行标签；明确命中且没有用户指定标签时自动设置草稿主标签，仍需题库审核。已有默认/原文标签不覆盖。已确认题目题干的关键词相似度仅作推荐，不自动确认、不得解释为正确概率；不读取答案做分类，不发送外网。

题目 bank_data.topic_index 保存导入时依据（版本、建议、自动分配标记）；列表返回最新计算的建议，以支持标签改名/合并和题干校正。已有匹配标签排在全部其他标签前，蓝色高亮并显示依据。无明确名称/别名命中时，从题干抽取最多三个短语作为未创建的新标签备选；点击创建并选中后通过原有题目 revision 保存，未点击不污染词表。新标签最多32字符，原有标签长度契约不变。历史试卷、作答和已确认题目不自动重写；无新增迁移/依赖/真实模型调用。
# M4-TOPIC-AI-02（2026-10-20，覆盖短语索引）

用户反馈短语准确度不足，停用导入/列表中的本地短语推荐及自动分配。知识点改为 AI 语义归类：先预览本次最多32道题的题干/选项、当前课程全部有效标签及别名，明确确认后以 BANK_EXTRACT 持久任务调用现有 glm-4.7-flash Provider，单次发送、不自动重试。新建标签只返回备选，不自动创建；已有标签推荐靠前高亮，建议不覆盖人工标签，用户可一键选用后按原revision保存。

AI输出逐题question_id、已有topic_ids、备选名称和简短依据；严格校验完整覆盖、UUID/标签归属、重复项、长度和数量，非法输出整批拒绝。来源/题目revision/词表/配置/15分钟预览有效期在确认和执行前后复核，撤权或修改后拒绝迟到结果。建议只写题目bank_data且递增revision，已确认题库回到草稿，历史试卷作答保留。配置入口位于题库页“API接入与模型配置”，密钥通过本机终端脚本隐藏输入到后端.env，不回传浏览器；无真实密钥测试、无新增迁移/依赖。
# M4-LOCAL-FILES-03（2026-10-20）

用户要求本地直接上传PDF/ZIP。文件接收与ZIP成员解析已具备，本轮将默认入口独立为“本地直接上传（PDF / ZIP）”，与“从资料库导入”“图片识别（可选）”区分；本地入口无需先选资料库版本，直接复用BankFileImport及现有M1/ZIP接口。保留AI发送确认、图片可选OCR、草稿保护、ZIP预算和逐文件结果，无新后端接口/迁移/依赖。补充ZIP内实际PDF导入的隔离浏览器验证。
# M4-PDF-OCR-04（2026-10-20）

本地PDF/ZIP中的PDF在拆题前逐页检测文字层，空页/极少文字页给出“扫描PDF图片转文字”选项，未确认不OCR且不导入可能漏页的部分题目。混合PDF按页序合并：有文字层页保留提取文本，无可靠文字页本地渲染+OCR；不把两路内容重复导入。可显式对整份PDF强制OCR以处理损坏文字层。最多20页/32MiB/24万字，逐页渲染最大2000万像素，识别子进程限时，超过预算明确失败。

复用M1只读版本授权与Asset写入、BANK_OCR任务、原图审核/插图裁取与题库拆题，不改M1解析/索引状态，不将OCR伪造为已确认资料正文。转换图保存版本/页号来源，任务前后复核版本/图片、租约和账户归属；删除来源撤销结果图片可用性。原图仅供审核，不自动进入考试。首次识别/重试显式点击，结果自动显示题目；可继续使用既有AI知识点归类。无迁移；M4可选OCR锁新增复用已锁定pypdfium2==4.30.0渲染组件及许可证。
# M4-LIBRARY-DELETE-05（2026-10-20）

用户要求便捷删题并将题目文件从资料阅读分离。新增0021迁移意图：Document.library_scope=material/question_bank，默认material；复用统一数据库/不可变版本/授权/解析，不新建第二套用户或数据库。题库专用上传/ZIP走question_bank范围，原件保存question_bank目录；资料列表/分页/搜索/资料导出排除该范围，题库文件库单列原件/解析状态/下载。历史来源无可靠导入用途标记，不猜测搬动；关联旧资料可显式移入题库，UUID/引用/版本/旧作答保留。账户完整备份含两个库，新schema标记0021并兼容0012–0020。

每题标题行提供直接删除，单题/批量删除不再逐题弹确认，以现有软删除状态+revision及可撤销接口保护；只恢复removed_by_user，拆合退出题目不得恢复。整份题库一键删除只确认一次，核对题目集合快照和metadata revision，原子软删除并隐藏该题库，可撤销；原件单独保留，已生成试卷/作答不重写。异步OCR/AI任务取消并撤销租约，避免删后重现。删除/撤销均检查归属、课程和进行中考试限制，不自动调用模型、不提交推送。


## M4-VISION-IMPORT-01（2026-10-20，实施前增量契约）
用户要求图片/PDF的AI转写及AI知识点归类，特殊字符/数学公式原样或LaTeX保留；以私人计组2021–2025 ZIP试卷部分验证。该包试卷与答案分离，默认仅题目，不生成答案。使用官方免费视觉模型glm-4.6v-flash（共用后端智谱Key；不改变M2文本模型），单页顺序处理、严格JSON校验、逐页持久checkpoint、失败仅显式续跑，不重发已成功页。原图/公式源码保留供核对，跨页大题接续、子问保留在大题内，未知文字标记待核对；草稿不等于已审核。归类复用既有语义分类器及当前课程标签/别名，优先已有标签高亮，候选不自动建标签、不覆盖人工选择。上传页提供明确发送范围/模型/题目模式/是否归类确认，确认前零远程请求；权限、源失效、取消/租约与配置变化检查，后续页不继续发送。无新迁移。
ZIP先读取目录供勾选，答案文件默认不选，可删除/移除单项及批量项后上传；已上传列表亦可移除并取消尚未完成识别，删除原件另行明确提示影响，历史试卷快照不重写。ZIP中文旧编码修正，沿用解压预算/CRC/路径拒绝规则，成员名视为数据。测试用隔离库/模拟传输；用户本轮明确授权必要时实际AI转写此ZIP，实际调用记录与模拟证据分开，不输出密钥、不上传私有样例到Git。


## M4-MARKDOWN-53-01（2026-10-20，实施前契约）
按用户最新要求：题库图文转写、文本拆题和知识点归类统一使用项目已有glm-5.3-flash（GLM5.3系列），官方视觉文档已核对，图片使用Base64 Data URL，保持thinking.enabled。配置和预览指纹包含模型身份；旧模型预览/排队任务须重新确认，不静默换模型，旧结果保留。题干/选项/解析保存为规范Markdown源码（SQLite文本及可下载.md，不保存运行HTML）；表格支持结构化表格、明确TSV/简单HTML转GFM，公式LaTeX/特殊字符不改写，不猜测丢失单元格；未知表格结构保留可核对源码。所有题目展示默认安全渲染Markdown/GFM/KaTeX，源码集中在校正入口。新上传/保存时规范化，不重写历史试卷/作答，不引入迁移/依赖、不提交推送。模拟验证模型图片参数、表格边界/权限/源码可逆及渲染。

M4-MARKDOWN-53-01实测增量：GLM5.3可对一道综合题返回超过3个合法知识点候选。候选属于建议而非题目/作答契约；接收上限改为8，仍建议模型优先1–3个。完整显示合法候选，不截断，不自动创建，不影响已有标签优先、未知ID/重复/跨课程/遗漏题目整批拒绝。推荐版本v3并加入预览指纹，旧预览需重确认。


## M4-TOPIC-UX-01（2026-10-20）
错题接口附加归属过滤后的当前标签名/别名，解析合并链但不重写历史快照；支持topic_id筛选。题库列表支持topic_id分页过滤。批量confirm使用全量revision/题型答案/标签归属/插图/来源校验，原子失败；仅全部有效题均确认时整卷CONFIRMED，旧试卷/作答不变。归类默认仅已选与AI语义推荐，其他通过名称/别名搜索最多20项；练习同样搜索选择。考点词表显示当前非删除题数并可跳到标签过滤后的题库，编辑折叠。无迁移、真实模型调用、提交推送。


## M4-DRAW-OPTIONAL-TOPICS（2026-10-20）
随机练习标签可选：空列表或省略topic_ids表示本人当前课程全部合格确认题，非空按任一所选标签并集抽取，保留题型/题数/去重/不足失败/快照/幂等规则。解除抽题标签12个限制（每道题的12标签限制不变），所有标签仍逐个检查课程归属。


## M4-TOPIC-TREE-ANSWERS-01（2026-10-21）
标签父子关系作为Topic.sources_json.hierarchy.parent_id元数据持久化，API公开parent_id；默认旧标签根级，最多6级，禁止循环/跨课程/已合并父节点，revision保护，合并时受控迁移直属子标签。父标签抽题/错题筛选/题库跳转包含所有后代，不改历史题标签和作答。备份验证层级，资料引用更新保留元数据，无迁移。GLM5.3彩色填答分离仅识别原文明确填入答案，将题干还原空格，普通强调/给定数据保留；输出逐空blank_answers，多空不拼成一个答案，唯一性仍用户设置。跨页答案正确合并，不猜答案，写入待审核草稿，逐页进度与确认发送保护保持。用户最新授权允许用原ZIP答案PDF做真实分离样例，文件仅保存在本地，不提交推送。

2026-10-21 用户增量：默认自动判断输入类型，不以文件名/颜色预设；本地像素/版面线索只供AI辅助，AI从原页判断题干、答案、解析，兼容黑白/手写/彩色/无答案。仅答案页无原题时明确提示不能单独造题。贴标签支持已有词表搜索与层级路径，选择子标签自动派生父级归属/查询，不冗余改写历史标签。

2026-10-21：ZIP不再按“答案／解析”文件名默认排除成员，列出所有支持格式，保留上传前选择/删除；内容类型由实际识别判断。为避免重复入库，可自行取消同一试卷的重复版本。


## M4-TOPIC-DIRECTORY-01（2026-10-21）
考点统计主界面按知识笔记目录交互：初始仅未分类入口和根标签，展开逐层显示子标签，选中末级显示原题Markdown。父标签直接关联的题目仍显示“本级题目”，不隐匿。未分类按当前有效标签关联为空判断，支持查看待校正题。仅本页内部拖动标签到另一标签或根级区，沿用PATCH topic revision、课程归属、六级/循环/冲突校验，失败不假更新；保留上级选择按钮供触屏/键盘。历史统计/矩阵/蓝图折叠，主界面不枚举全部标签。无新API/迁移/依赖/真实模型调用，历史试卷和作答不变。

2026-10-21 导入来源修复：从资料库导入同时合并本人当前课程documents与bankFiles，以document UUID去重，名称/原文件名可搜索，已入库papers提供直接打开入口不复制题目；保留文件版本授权和校正草稿保护，题库原件仍不进资料阅读。


## M4-TOPIC-ORGANIZE-02（2026-10-21）
按用户要求直接复用知识笔记FolderLibrary交互：独立展开按钮、整行标签拖动、固定位置的未分类/根级放置区（拖动时只替换提示、不插入节点）、清晰目标高亮与移动结果，保留搜索和按钮归类。父标签、新建所属父级和合并目标采用关键词搜索，不枚举全库；已选路径单独显示，可清空。客户端拒绝自身/后代/超深目标，服务端仍以revision/同课程/深度校验为准，失败不假更新。未保存编辑阻止误切换/拖动。
新增DELETE /topics/{id}?revision=N：课程写锁、本人归属、修订校验；只删除无子标签、题目关联（含隐藏/历史记录）、合并重定向、资料依据和试卷快照引用的空标签，冲突409引导合并或先整理，绝不删除题目/改写旧快照。新建空标签可删除，同名可重新创建；其他来源的旧标签保留。无迁移/真实模型调用/提交推送。隔离API和浏览器测试覆盖删除权限/冲突/引用保护、搜索归类、内部拖动和390/1440布局。


M4-TOPIC-ORGANIZE-02追加：用户要求“从资料库导入”和本地上传完全同效。复用同一个BankFileImport实例及版本处理队列；已有文件只入既有version_id，不重新上传，复用文字规则/AI原文预览确认、PDF扫描检测、本地OCR/整页转图/AI原页公式、知识点归类、进度/取消/重试和自动展示。来源选择不直接走旧的规则导入捷径；两入口共享模式/仅题目/AI归类选项，保留原课程归属与用户发送确认。ZIP本地展开后的每个已保存成员也走该版本队列；不另造ZIP解析方式。

M4-TOPIC-ORGANIZE-02拖动验证增量：保留FolderLibrary布局与目标规则，Windows Chrome原生HTML拖放在自动鼠标测试阻塞，改用本页面PointerEvent阈值拖动、轻量跟随预览、固定根级放置区和指针位置命中；只接受本页按下的标签快照，取消/窗口失焦清理，失败不更新数据，仍保留搜索归类按钮。不是改动知识笔记模块。


## M4-TOPIC-DELETE-SELFREVIEW-03（2026-10-21）
用户最新要求覆盖空标签限制。任何有效标签可删除：metadata软删除保留UUID、历史试卷/作答/旧题快照；当前有效题目只移除此标签及指向它的合并别名关联，保留其他标签，无标签进入“未归类”。直属子标签提升到被删标签原上级（不级联删除子标签），统一课程锁/revision和活动作答保护，统计快照STALE；被删标签不能搜索/归类/AI复用，可同名新建。备份保留删除元数据，无迁移。
允许无标签题和缺标准答案的四选项/填空题经人工核验参与全课程练习；不猜答案，不错误地自动判分。填空唯一性仍需手设，缺答案时转自评。提交后所有非自动判分题（含解答、无答案、历史已完成记录）提供自评正误；自评错题幂等入错题库，不改自动分数，已自评重复同值返回，冲突拒绝。已自动判分题不可借自评覆盖。删除按钮用独立危险操作区，中文影响说明与响应式布局。


## M4-DEEPEST-DISPLAY-BATCHSAVE-04（2026-10-21）
同题在父级和任意深度后代都有归类时，目录正文只保留最深归类处；按题型、规范化题干、选项及插图标识精确判断同题，不用AI/模糊匹配，不物理删除题目或改写标签/历史。父级仍保留子树汇总（同题去重）供查找；兄弟标签可各自展示。层级新建/拖动/修改及题目标签变化后按当前树即时派生。
校正页增加“保存所选（N）”，全选仅作用本页，收集已勾选编辑器当前草稿，复用单题校正协议，以POST /courses/{id}/question-bank/save提交1–100条。服务端课程锁/归属/revision/图片检查，整批事务提交；任一失败全部回滚，页面保留草稿，成功刷新所选修订但不自动核验。未选编辑器草稿不因刷新重置；上传/拆分未处理时阻止批量保存，避免丢草稿。按钮沿用原批量工具栏和响应式样式。
取消导入完成/初始加载/查看已有题库时自动滚动到校正区；每次进入上传与校正页从顶部开始。主动点击对照来源的定位保留。无迁移/依赖/真实模型请求/提交推送。


## M4-REDO-API-GUIDE-05（2026-10-21）
考点管理去掉“管理”折叠，直接展示表单。标签文本仅名称（目录缩进仍表达分级），不显示路径串。反馈从错题页移除，新增左侧独立“使用反馈”路由。
错题可独立重做，快照/用户输入/判定追加保存到原Mistake.detail_json.redoes，不覆盖原题/原作答；请求UUID幂等、同课程串行锁，四选项重新排列并映射原答案，有完整标准答案时规则判断，否则提交后自行判断。成功后用户可明确“移出错题库”或保留；移出仅metadata软隐藏，重做记录和原试卷不删。每日目标=min(3,可用错题与今日已完成题目的并集数)，按账户时区、不同错题ID计数，错误重做也算完成，待自评不算；移出后保留今日完成进度，0题视为完成。重试/刷新/跨账号与删除课程仍严格隔离。
用户最新补充：API无需跟随账号，提供左侧“API接入”新手流程图、官方密钥入口、默认端点/模型、粘贴密钥保存及显式连接测试，说明本机用户共用。复用原智谱Provider，只支持已接入的固定端点/模型，不恢复M3停用AI。密钥加密保存到本机data配置文件，不返回原文/写日志/进入备份；各API/worker读取更新后配置，无需重启。未配置/已保存未测试/测试成功/失败明确区分，状态保留测试时间，测试只在用户显式点击且确认后发送极短测试文本，不发送资料。不自动真实模型调用。无新迁移/依赖；先隔离测试与文档，不提交推送。
## M4-ENTRY-06（2026-10-21）

每次进入真题与模拟卷均从第一个“上传与校正题库”板块开始，不因本地存在作答记录自动跳转；已有记录仍可手动进入练习后恢复。API连接测试按Provider既有 `(结构化结果, 使用量)` 返回契约解包，不将成功响应误报为服务器异常。不自动使用真实密钥测试。

## M4-REDO-MASTERY-07（2026-10-21，覆盖05的每日计数规则）

错题重做打开 `/review?mistake=<uuid>` 独立子页面，支持返回、刷新和待提交草稿恢复。错题列表从未答对的优先，曾答对且保留的标为已掌握，不纳入未掌握题数和待做目标。每日任务置顶并取代旧今日任务侧栏；历史ReviewTask接口/数据保留。

每日按账户时区，仅统计每个Mistake第一次成功重做所在日的进度，自动判对或显式自评正确均可，答错/只提交未自评不计数。曾在往日答对的保留题重复练习不增加进度。目标=min(3,仍在库内未掌握题 + 今日首次答对题)，今日首次答对后移出仍保留当日计数；同题至多一次，跨日只从仍未掌握题生成目标，0题自动达标。以既有redoes历史派生，不改原始作答/历史记录，无迁移或真实模型调用。

## M4-REDO-GOAL-08（2026-10-21，用户追加覆盖07）

每日题数由用户自设0–1000（0暂停目标，初始3仅为可改默认值），当前浏览器按账号保存；GET /mistakes/daily-progress?goal=N校验预算并返回goal。目标=min(goal,待掌握题与当日有效掌握题并集)，不强制固定3。最新完成判断答错会恢复待掌握；同日先对后错撤销此题的有效计数，再答对同题至多计一次。连续正确的掌握期以首次正确日计入，旧日已掌握题重复正确不增加今日数。

从重做和正常练习的自动/人工错误同步恢复；本人同课程且有相同source_question_id的历史错题复用身份，追加relapses事件、取消移出状态，不重写原始作答快照。同一作答题错误事件幂等，判断事件保留时间和单调sequence防止相同时刻顺序歧义，备份校验引用与结构。无迁移或真实模型调用。
## M4-REDO-EXTRA-09（2026-10-21）

每日目标是最低要求，不限制继续重做。completed返回当日当前有效掌握的不同错题完整数量，不再截断至target；展示分母为用户设置的goal，题量不足仍按原有效target判定达标并注明。达标或暂停后，只要库内有题仍可继续；独立作答页支持继续下一道。重复同题不加数、错误撤回及跨日规则保持不变，无迁移或真实模型调用。
## M4-VISION-VERIFY-FIELDS-10（2026-10-21）

依据本机实际失败元数据：视觉核验返回漏source_status时仍严格拒绝，不默认visible、不自动真实重试。修正ANSWER_PROMPT被VERIFY_PROMPT复用时，字段白名单/JSON示例遗漏source_status却又要求必填的冲突，白名单与示例均明确包含该字段，核验阶段继续必须给出visible/uncertain/absent。原图不存在题目的absent去除和uncertain人工核对保持。超时110秒边界、用户显式续跑与已完成页保留规则不变，无迁移、密钥变更或自动重发。
## M4-DISPLAY-REFERENCE-11（2026-10-21）

交卷及错题重做提交后，原题有参考答案/解答/解析时直接展开安全Markdown展示，无原文解答则明确未提供，不调用AI编造。进行中仍不下发/显示答案。按用户确认，同一原卷的大题子问自动按原题号顺序合并展示，保持独立题目ID/题型/答案/判分；不同原卷不混组，不按题干猜大题，不重写历史试卷。新快照附加可选display_group，旧快照保持原展示；题库分页前按中文/数字题号自然排序。

AI文件/图片转写及知识点归类明确展示排队/等待AI返回，并显示“AI也会犯错，请仔细甄别”；恢复页面的进行中任务也显示，不自动重试或额外调用模型。标签上级搜索、自定义输入与创建按钮采用统一网格对齐，兼容手机。AI学习删除练习题生成入口及本地练习子模块，练习统一在真题与模拟卷；历史候选结果与旧API兼容保留，不因移除入口删除数据。无迁移/新依赖/真实模型调用。
## M4-COMPLETE-CONTEXT-TAGS-12（2026-10-21，用户更正优先）

保持原子题抽样和题数/判分，不改为大题抽样或新增组合题型。新抽题/蓝图快照除当前子问题干外，携带同原卷、显式同大题的完整题干上下文（含其余子问与拆分父题，仅供理解条件），不携带其答案/解析；独立区域区分本次作答子问。只复用有归属且来源仍有效的数据，删除内容不回流，审核过的插图才进入考生上下文。不能确定归属不跨题猜补，超出有界完整上下文预算显式失败不截断。旧题/旧作答快照不重写。

AI语义推荐中已有且当前有效的标签默认在校正草稿中勾选，用户可取消，保存后生效；备选不自动创建。保存明确选项后记录selection_reviewed，后续加载不覆盖人工取消，新一轮AI建议才重新预选。超过每题12标签时明确提示人工筛选，不静默丢已选项。上级单选结果直接回填原搜索框、可清除/替换，不在下方显示标签列表。无迁移/真实模型调用/提交推送。

子题额外提供“查看整道题”只读弹窗，集中展示已冻结的原大题上下文、图表与当前子问，不显示参考答案/解析，不增加本次题数或改变计分。原生对话框支持Escape关闭并返回触发按钮。旧快照缺完整上下文时明确提示，禁止伪称已补齐或回写历史作答。

## M4-PRACTICE-ORDER-13（2026-10-21）

随机练习以试卷冻结的随机数组顺序编号1至N并依次显示，不再被原卷大题/子题号重新排序。仅相邻且同源同大题的子问可共用展示标题，非相邻题不移动；完整上下文和查看整道题保持。预览、作答、恢复与结果使用同一顺序，不改题目ID、答案关联或历史快照。

## M4-REVIEW-BATCH-TAGS-14（2026-10-21）

整份题库非SUPERSEDED题全部显式核验后同步CONFIRMED，跨分页/多题库逐份独立判断。未改变题干/题型/答案/解析/分值/标签/插图的重复保存保留核验状态；真实修改恢复该题草稿及题库待审核，不把保存当核验。空题库不自动确认，已删除/拆合父题不阻塞确认。批量确认和保存后统一以有效题状态同步题库，旧练习快照不修改。

批量知识标签提供“都添加这个标签”（保留原标签去重追加）及“都改成这个标签”（覆盖所选题原标签）两个显式动作，旧action=tag保持替换兼容，新增tag_add。先校验整批归属/revision/每题最多12标签再写入，任一超限全部拒绝，不截断。显式批量选择记录人工标签决定，避免AI刷新重新勾选。工具栏分离题库筛选、批量操作、标签搜索/动作，桌面控件对齐，手机纵排。无迁移/真实模型调用/提交推送。

用户追加覆盖上限：每题显式标签上限改为5个，单题保存、导入、拆合及批量设置保持一致，父级自动归属不重复占名额。历史已有标签/快照不自动删除；校正时可手工缩减。批量超限须一次列出所有超限题的question_id/paper_id/题库名/原题号/操作后标签数/上限，前端直接展示定位信息，整批仍无部分写入。AI推荐合并超过5个时只提示筛选，不静默截断原选项。

## M4-REVIEW-NAVIGATION-15（2026-10-21）

每次离开题库校正只进行一次未保存确认，共享本次导航事件的决定，不能为每道未保存题依次弹窗；取消仅取消当次导航并保留可继续编辑的本地草稿，确认仅放弃此次离开的草稿，不跨事件记忆授权。仅未核验/存在警告但无本地修改不算未保存。上传/请求处理中继续保护，不把确认放弃当成取消在途请求。题目折叠标题直接显示待核对具体原因（不只数量），填空答案一致性设置移至题目顶部可见专用区，需显式选择、经原保存和核验生效。选择框与折叠入口统一至少44px交互高度，箭头增大，兼容桌面/手机及键盘，不改判分规则/历史快照，无迁移/真实模型调用。

## M4-RETIRE-FILL-BLANK-16（2026-10-22，覆盖填空规则）

用户取消填空题，今后仅选择题/解答题。含横线、括号等空位的题干照录，作为solution保存，原答案和解析保留，不再要求答案唯一性或逐空一致判分；提交后按解答题检查提交、允许自评。题库现有PastQuestion.fill_blank幂等转换为solution并递增revision，保留ID/题干/答案/标签/插图和审核状态；仅当缺参考答案而有原逐空答案时将其合并为参考解答。转换前本机SQLite在线备份；不修改原ExamPaper/ExamAttempt/Mistake历史快照或历史成绩，新错题重做副本按解答题处理。无schema迁移，旧填空请求和旧AI输出接收后兼容归一到solution；旧备份恢复只转换来源题，历史快照照旧。页面取消填空题型、填空设置和新蓝图配额，旧试卷填空作答与判分兼容读取保留。先隔离验证，不调用真实模型，不提交推送。
