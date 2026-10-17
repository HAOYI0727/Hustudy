# Hustudy 当前测试报告

2026-10-17 M2-TOPICS-REUSE：165项关联后端通过（146项20.57秒、问答引用/配置11项1.86秒、备份/撤回8项5.70秒），25项Vitest、6项Chrome（31.7秒，390/1440px）及TypeScript/Ruff/生产构建通过。22项新增后端用例、2项前端单元和2项浏览器用例；三模式复用无额外网络/Job、来源/配置/考点变化拒绝、逐题关联/越界/旧信封兼容。临时库与模拟响应，不使用真实API或用户资料；未重跑全量后端，旧Windows三项不处理。[详情](gcx/topics_reuse_2026_10_17.md)。

## 2026-10-17 M2-REPORT-CAPACITY

140项关联后端通过（18.76秒），23项Vitest、TypeScript及相关Ruff通过。新增7项容量回归覆盖12步骤/12知识点/6引用/4例题与更长正文完整保留、第6条假引用仍拒绝、61条有效引用、超出新容量时的安全中文数量说明，以及必填/标签来源/3–5自测约束。问答/候选行为未改，已回归其相关测试。无真实模型调用，未重跑浏览器/全量后端；原Windows问题未处理。[记录](gcx/report_capacity_2026_10_17.md)。

## 2026-10-17 M2-REPORT-SELFCHECK

133项关联后端通过（18.67秒），23项Vitest、相关Ruff/TypeScript通过。新增7项覆盖自测缺引用舍弃与基础模板替换、原题不泄露/不猜引用、一次HTTP、严格最终契约及其他字段/假引用仍拒绝。前端补页面标识/笔记保留提示的渲染用例，实际结果见[记录](gcx/selfcheck_completion_2026_10_17.md)。本次未重跑浏览器/全量后端，未真实模型调用；前轮4项Chrome仍为历史证据。

## 2026-10-17 M2-REAL-MATERIALS（当前增量）

最终关联后端126 passed/20.70秒，Vitest22通过，Chrome报告/候选390与1440px四项通过（26.6秒），TypeScript、相关Ruff与生产构建通过。新回归含真正生成并解析的9页PDF/9页PPTX代码课件、完整范围与切片偏移、成功步骤/可见中间草稿、失败显式续跑不重发成功批、取消/删除/租约失效拒绝迟到结果、恢复归属/配置/来源校验、历史旧提示词可读、代码符号与唯一精确答案转换。浏览器补验部分报告、确认续跑、等高独立滚动和窄屏导航可视性，截图已查看。

只读检查用户已有7份Lecture的解析/索引及抽样正文，没有将其发送给模型。自动测试使用临时库、合成课件与模拟HTTP；无真实学科质量结论。未重跑全量后端，原Windows三项问题未处理。详见[实现、限制与复测步骤](gcx/real_materials_2026_10_17.md)。

## 2026-10-17 M2-REPORT-STRUCTURE

116项关联后端回归通过（16.68秒）、22项Vitest、TypeScript与相关Ruff通过。覆盖无效附加概念关系过滤与提示、有效关系保留、重名安全诊断、伪造引用仍拒绝、提示不可由模型伪造、结构错误徽标及笔记提示兼容。未自动调用真实模型，未重跑浏览器/全量后端；既有Windows3项问题未改。[详情](gcx/report_structure_2026_10_17.md)。

## 2026-10-17 M2-QA-EXCERPTS

112项关联后端回归通过（25.43秒），相关Ruff通过。问答采用请求内摘录编号，验证原文字符、引用偏移/哈希、未知编号拒绝且不重试、混填拒绝、旧引用格式严格校验，以及预览确认/来源撤权/历史/笔记和报告候选备份回归。前端无改动，未重跑浏览器或全量后端，无真实模型调用。[详细记录](gcx/qa_excerpts_2026_10_17.md)。

## 2026-10-17 M2-CITATION-FEEDBACK

106项关联后端测试通过（23.79秒），19项Vitest通过，TypeScript与相关Ruff通过。覆盖无效片段ID/不一致摘录安全消息、拒绝空白模糊匹配、历史引用错误徽标与服务/成功状态兼容。本轮无真实模型调用、无全量后端或浏览器复测；原Windows3项问题仍未处理。[诊断与增量文件](gcx/citation_feedback_2026_10_17.md)。

## 2026-10-16 M2-CANDIDATES-01（当前增量）

最终M2/备份/课程撤权/M1关联89 passed/27.77秒；全量中间版167 passed/3 failed/44.19秒，仍为既有Windows 0600/执行位/符号链接权限前提。此全量早于固定报告2项新增，不推算最终全量成绩。14项Vitest、Ruff/类型/构建、临时库迁移无漂移、Markdown/AI显示安全、PDF实渲染通过。

候选Chrome操作使用真实临时API和固定模型，报告真实AI操作使用HTTP替身。最终浏览器补验和截图见[gcx验收](gcx/candidate_acceptance.md)。不读取用户资料或使用真实密钥；真实质量、WebKit/实机/成员签收待验，不能标全部通过。


## 2026-10-16 M2报告 / gcx

本轮Codex辅助gcx，未上传GitHub或发布。最终模块与关联回归45 passed/14.69秒，Vitest14、Chrome2（390/1440px）通过；Ruff/类型/构建/迁移漂移/Markdown安全显示/PDF实际渲染通过。证据与命令见[gcx验收](gcx/study_report_acceptance.md)。

全量后端初次129 passed/3 failed，29.37秒，发生在报告备份往返用例新增之前；不与45项相加。失败均在未改动的既有测试：test_jwt_contract.py的0600断言、test_preview_recovery.py的POSIX执行位、test_storage_contract.py的符号链接特权（WinError1314）。未标记skip或删断言；需要队长后续统一平台验收。测试夹具已释放SQLite池以免Windows临时库清理错误。沙箱环境本地socket/缓存rename受限，相关验证在沙箱外以临时库/假密钥执行。

Chrome真实临时账户/资料/笔记API、AI HTTP替身；未发起真实模型请求，不等于学科质量或真实模型端到端通过。人工审阅、跨浏览器/实机与团队签收待补。


更新日期：2026-10-16；记录者：Codex（zhy队长会话辅助），本人审阅待填。报告只记录运行证据，工作区未提交/合并。

最近后端共享检查（2026-10-15）`bash scripts/check.sh`：**116 pytest passed（原格式切片19.60秒）、14 Vitest**，Ruff、临时迁移/ORM漂移、安全Markdown/AI显示、PDF.js双页、TypeScript/Vite均通过。独立Python3.12.13工作区116项16.96秒；2026-10-16前端最新完整回归42项3.6分钟、14Vitest、类型/构建通过，无重试。保留1条Starlette/anyio弃用警告，主包约489.66KB/按需PDF492.56KB，原格式阅读器按需加载。运行库head0012，本轮无迁移。

10课程/200实际导入资料/1000笔记/5000片段的隔离容量，5类接口各100次、4并发，p95最大275.814ms；20张PPTX/50页文本PDF解析索引≤60秒。同机Python3.12.13干净源码、新venv、npm ci重建115项及全部共享检查通过（该快照早于新增权限矩阵，当前116项另全量复验）。详见[检索/容量/环境验收及JSON](zhy/materialhub/search_capacity_acceptance.md)。不是跨机器或真实课程复杂样本/所有版式的成绩。

关键补录/撤回、搜索翻页/摘要/回源、索引UUID不变、课程确认删除撤权已双引擎验证；三格式预览/截图、导航、401草稿与备份下载一并回归。归属矩阵覆盖19类M1读取和10种越权变更。真实模型未调用，真实用户试用、Gitee/签收/发布及M2–M4剩余P0不冒记通过。

以下日期增量保留当时的真实数量/限制；当前任务状态见[完成核查](zhy/completion_audit.md)、[任务表](../collaboration/zhy/task_status.md)，历史待办由后续证据覆盖，不能把不同轮次累计成当前测试数。

## 最新增量：GLM课程问答

2026-10-14 M2-ZHIPU-QA-01：最终bash scripts/check.sh为67pytest passed（11.68秒），共享Ruff/迁移漂移/Markdown安全/PDF双页/类型/构建通过。新增20个远程AI风险场景使用假密钥/MockTransport；真实网络只进行自制苹果请求，grounded/1原文引用/417tokens。用户课件不进入自动网络测试。

[详细验收](zhy/integration/zhipu_qa_acceptance.md)说明配置、确认、Source/schema/限流/取消/租约、当前政策未核实与Safari正向闭环限制。覆盖前文“真实模型未接入”中的课程问答部分；完整教学报告、题目生成、语义正确率/压力/备份恢复等继续待验收。

2026-10-15最终补验：AI回答使用真实组件SSR验证生成链接/图片不可导航或加载、HTML移除、GFM表格保留；最终全量命令退出0，日志/tmp/hustudy-zhipu-check-final.log。Safari入口/演示状态可见，但切换真实模式后返回登录，原因未定，未完成正向确认/结果/草稿验收。没有额外远程调用用户资料。保留主包521.87KB构建提示，未测量性能目标。

同日DOC-ZHY-AUDIT-01仅重分类队长文档并核查当前状态，没有重跑业务测试。正式十任务与“已实现/待实现/待验收”的边界见[完成度核查](zhy/completion_audit.md)，67项历史回归不等于队长职责或全部P0完成。

## 2026-10-15 共享认证/存储/分页最新回归

实际bash scripts/check.sh最终96passed(15.84秒)，Ruff/迁移漂移/笔记及AI显示安全/PDF.js双页/TypeScript/Vite通过，日志/tmp/hustudy-browse-01.log；此前JWT89和存储94为历史切片结果。29新增场景验证JWT、原子存储/低磁盘/回滚、105份同时间记录稳定分页。1条依赖警告及主包提示保留；未据此测量p95或认定全部P0通过。

## PLATFORM-BACKUP-01实际结果

完整账户ZIP/空账户恢复已实现，四格式、3张图、3笔记双链、2套试卷作答、人工来源/AI/错题/时区在隔离库往返；同库UUID/非空/越权、损坏/真实字节/假引用/缺失关系、提交故障/文件清理、过期不重放及终态移除验证通过。最终bash scripts/check.sh：101passed(16.43秒)，所有共享检查/构建通过；日志/tmp/hustudy-platform-final.log。Safari/跨机器/Python3.12/压力仍未测，不标全部P0。详情见zhy/shared_platform/account_backup_acceptance.md。


## PLATFORM-WEB-BASE-01实际结果

本次check101pytest15.52秒、10项Vitest及全部共享检查通过；独立Python3.12.13锁依赖101项24.19秒。Chrome（本机channel）/官方WebKit各4项，最终8passed52.2秒：真实隔离API上传解析阅读检索、版本定位刷新/前后退/草稿离开确认、模拟401+真实原账户重登保留笔记及资料整理草稿、完整备份实际下载hash。首次WebKit相对路径失败已修为绝对路径并复验通过，不能将失败启动计为通过。

主包485.85KB（按需工作区/Modal），无500KB警告；仅构建体积证据，未测加载时间。Safari查看资料/备份入口；用户现有数据未更改。完整范围、命令、日志和限制见[共享前端验收](zhy/shared_platform/web_base_acceptance.md)。其他课程/性能/交付关口仍待验证。


## M1-PREVIEW-RECOVERY-01实际结果

实际缺LibreOffice和Safari缺少Map.getOrInsertComputed两层原因均已定位处理；安装LibreOffice26.8.1（程序26.8.1.1），PDF.js显示层/worker同版本legacy，环境检测/原任务重试/错误详情可用。PPTX包含隐藏页并校验页数，旧错位读取/截图拒绝，有旧截图不静默改指。现有课件缓存重建为146/146页，原件和正文引用身份不变。

最终check110pytest15.47秒、10Vitest及全部共享检查通过；最终14项Chrome/WebKit约1.5分钟通过（含移除Map/WeakMap新API的兼容测试、隐藏第二张PPT、三格式真实预览截图回源）。3.12选定17项3.40秒通过。保留1条依赖警告；主包485.98KB/PDF阅读器492.59KB，均按需或原入口，无500KB提示。Safari曾实际显示原课件第一页；最新146页缓存的新标签页因会话过期需原账户重登，未冒记最终实机再打开。

[验收明细](zhy/materialhub/preview_recovery_acceptance.md)记录命令、日志及剩余范围；测试失败的早期选择器、modern构建记录不替代最终结果。无真实模型调用/用户课件外发。

M1-SEARCH-02最终边界复验：跨窗口删除15篇笔记后旧结果页为空，提示“当前页已无结果”，上一页钳制到有效页；Chrome/WebKit2项12.6秒通过（原20项中的场景增量，不累加计数），类型检查通过。63份文档622本地链接无缺失，18交接锚点唯一，git diff --check/Ruff/bash语法通过。


## 2026-10-15 M1-NATIVE-PREVIEW-01

按用户新要求补PPTX/Word直接OOXML预览，PDF继续原文件；转换PDF另标兼容预览，原格式不依赖转换状态。原件仅从授权接口读取，隔离iframe无登录信息/无外部连接，nonce与消息source/channel/页码校验，卸载取消请求。后台解析完成不切走原格式视图；隐藏PPT页/Word显式换页/样式表格图片、缩放/演示、坏ZIP显式重试均已验证。

最终26项双引擎2.1分钟（各13项）、14Vitest、类型与构建通过；后端116项19.60秒及迁移/安全显示/PDF实渲染等共享check通过。API/数据库无迁移，本轮未新跑后端3.12/容量/干净全依赖安装，历史证据不得当作新增依赖后的新测量。Office本地runtime约1.31MB不在主入口，第三方许可随构建发布。初轮故障注入受开发StrictMode重复GET干扰、之后WebKit暴露后台切模式问题，已分别修正测试/实现并最终全量通过。见[原格式验收](zhy/materialhub/native_preview_acceptance.md)。


## 2026-10-15 PLATFORM-RESPONSIVE-01

全量Chrome/WebKit各20项共40passed3.2分钟，无重试，含新增7场景/每引擎；覆盖5尺寸/触屏、9工作台页面/登录注册、无整页横向溢出、44px热区、目录折叠、搜索/长笔记、抽屉焦点/草稿/旋转及既有端到端闭环。吸顶收尾后20项1.5分钟，PPT比例及实际可视区收尾6项31.8秒通过，是40项子集，不相加。14Vitest、TypeScript/Vite通过，主包488.37KB；无后端/迁移变化，未在本轮重跑pytest/容量/3.12。

初轮13/14响应式通过后修复Chrome抽屉Shift+Tab焦点；构建Array.at目标lib不支持已改兼容下标。最终结果、日志/截图和未完成实机/真实用户边界见[验收](zhy/shared_platform/responsive_layout_acceptance.md)，不把浏览器模拟当Safari/iPad实机或真人试用。


## 2026-10-16 PLATFORM-VISUAL-02

最终完整Chrome/WebKit各21项共42passed3.6分钟，无重试；包含新关键配色/区域账户标识/减少动效场景及此前全部闭环和5尺寸触控布局。7处实际DOM文字/控件配色抽样≥4.5，不声称完整无障碍审计。14Vitest（397ms）、类型检查与Vite构建通过；主包489.66KB、按需PDF492.56KB。无后端/迁移改动，未在本轮重跑pytest/容量/独立3.12。

首轮跨夜33passed/9超时、6.2小时，部分超时记录长达数十分钟/小时；未核实系统休眠日志，不武断归因或当性能数据。连续全量重跑42项均通过，未扩大超时/开启重试；临时caffeinate随测试结束退出。原日志/tmp/hustudy-visual-02-e2e.log，最终/tmp/hustudy-visual-02-final-e2e.log。[验收及截图](zhy/shared_platform/visual_polish_acceptance.md)。

## 2026-10-16 M2结构化响应错误反馈回归

命令：`E:\Anaconda\python.exe -m pytest backend/tests/test_ai_error_details.py backend/tests/test_question_drafts.py backend/tests/test_remote_ai.py backend/tests/test_study_reports.py -q`。实际：76 passed in 12.34s。新增语法/字段错误区分、未知字段和值不泄露、候选缺失必填路径及不重试验证；Ruff针对providers.py、question_drafts.py和test_ai_error_details.py通过。临时数据库/假密钥/模拟HTTP，未调用真实模型；未证明历史400字请求具体错在哪个字段，也不声明真实候选输出质量已通过。

## M2-LABEL-REVIEW-01最终验证（2026-10-16）

87项后端23.29秒、17项Vitest291ms、4项Chrome28.1秒，生产构建/TypeScript/Markdown安全/Ruff通过；含教学结构/非法概念关系/旧报告兼容，标签快照、保存失败恢复和真实临时笔记API引用验证。全部为临时数据/模拟HTTP或固定演示，未调用真实模型；不标全站/实机/WebKit或真实学科质量通过。[命令、结果、截图及限制](gcx/basic_acceptance.md)。

## M2入口命名复验（2026-10-16）

仅改前端名称及用途说明。npm run check --prefix frontend通过；既有study-reports/question-drafts的Chrome390/1440流程4 passed（25.3s）；responsive-layout的“关键文字配色、工作区标识与减少动效”单项1 passed（12.4s）。临时数据/模拟AI，未调用真实服务。本轮未重跑后端或全量测试。

## M2-MODEL-53-FLASH（2026-10-17）

104 passed in 22.81s（模型配置/切换/新旧参数、问答/报告/候选/安全错误/备份关联），Chrome报告/候选桌面和窄屏4 passed/24.6s；相关Ruff通过。全程假密钥/模拟HTTP/临时数据，未调用真实模型；不把模型可配置说成新模型实际可用或内容质量已验。命令及限制见[记录](gcx/model_switch_2026_10_17.md)。
