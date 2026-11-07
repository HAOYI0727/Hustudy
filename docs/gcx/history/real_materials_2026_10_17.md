# 真实课件、分批报告与AI工作区修复（2026-10-17）

任务M2-REAL-MATERIALS，Codex辅助gcx。用户要求先用本人API验证真实课程，再考虑BYOK。本轮不改密钥/模型配置、不自动调用真实AI、不修改M1解析器；仅在原Hustudy-main实施，GitHub、下载副本和原83文件上传副本未同步。

## 实际课件检查

以只读SQLite连接检查本人已有资料，未把课件发送到模型，未修改运行库或重新解析原件。7份Lecture资料均为parse/index SUCCEEDED：

| 资料 | 格式 | 正文段数 | 提取字符 |
|---|---|---:|---:|
| Lecture 1 | PDF | 37 | 8371 |
| Lecture 2 | PPTX | 26 | 6566 |
| Lecture 3 | PDF | 26 | 6051 |
| Lecture 4 | PDF | 24 | 6558 |
| Lecture 5 | PDF | 29 | 8448 |
| Lecture 6 | PDF | 28 | 8520 |
| Lecture 7 | PDF | 33 | 10377 |

Lecture 2/6抽查有函数、箭头类型、ML代码与运算符，替换字符U+FFFD计数为0。旧流程Lecture 6前6段仅1311字符，Lecture 2前6段1270字符，不能覆盖正文。此证据说明非整体读取失败，不证明图片、数学公式、PDF阅读顺序或字体映射完整；有缺失应回到M1/人工补录定位，不把解析成功等同于全部学科语义提取正确。文档不复制私人课程原文或密钥。

## 当前实现

- **报告范围**：最多20版本、400原文段、240000字符；纳入完整可提取正文，超限明确拒绝并请按章选择，不再静默取前6段。长原文拆连续子段而非截去2000字符之后的正文，引用带原chunk偏移。预览列出覆盖情况、读取问题、批次数和最多调用数。
- **报告分批**：每批≤8000字符/32子段，每次worker处理一批。各批独立完整教学报告，最终按顺序分节展示，每节3–5自测；不宣称跨节综合推理，未再发AI汇总请求。允许按部分审阅标签和保存笔记，整体引用超过M3单篇50处时提示按部分整理，不修改M3上限。
- **持久化与续跑**：成功批保存为内部AIResult checkpoint（固定请求/批序UUID），不进入普通报告/问答/候选历史；仍通过现有账户备份保存。失败保存已完成部分与具体批序，不标完整成功、不自动重复失败调用。POST resume需再次严格布尔确认；跳过成功批、重验来源/模型和归属。取消/删除/过期租约拒绝迟到写回；worker在排队批之间重启可继续原已授权计划，未结束的在途步骤失去租约则明确失败并等待用户确认。
- **候选范围**：最多128段/32000字符，完整纳入；超限请缩小章节。普通问答继续按问题关键词检索相关片段，仍不声称对整份课程作全面分析。
- **引用**：报告/候选接入问答已用的400字符摘录编号，模型选择、程序回填；兼容旧逐字quote，错误编号仍拒绝。报告/候选提示词均v4，旧版本历史仍可查。
- **编程题校验**：选项NFC规范化且保留运算符、大小写、内部空白，避免x+1与x-1、f(x)与f[x]误判。题干只忽略末尾中文句末符号，不删除代码符号；旧hash不重算，跨批历史去重仍是原待办。答案仅在精确匹配唯一选项正文时转为该选项ID并提示，其他情况不猜测。错误细分到题序、选项重复/编号/答案/评分细则。
- **超时与错误**：连接10秒、读取无响应110秒，响应字节处理120秒检查，替代旧45秒读取/60秒响应检查；区分连接等待与响应等待、输出截断、题目校验与平台繁忙。1302按账户速率、1305模型繁忙、1308使用上限分类。这里不是父报告全部批次120秒内完成的承诺；严格跨请求deadline、缓存与有限修复等完整R05–R07仍待审计，不把超时配置冒称完整NFR-07达成。
- **布局**：仅AI模块新增CSS。宽屏>1100px左右两栏等高、独立滚动，窄屏单栏、设置/结果快捷导航与结果自动定位；长资料/历史有滚动区域，长报告按部分折叠。布局不改其他模块共享样式。

## 验证与限制

最终关联后端126 passed/20.70秒（test_real_materials、report_structure_feedback、qa_excerpts、citation_feedback、model_switch、remote_ai、study_reports、question_drafts、study_report_demo、ai_error_details、account_backups、ai_scope_history）；22项Vitest、TypeScript与相关Ruff通过，生产构建通过。Chrome报告/候选390/1440px四项26.6秒通过；报告扩展模拟部分失败/确认续跑及布局，两个新布局截图已目视检查。未重跑全量后端，历史Windows三项问题未改。没有真实模型质量验收。

已完成批次可在运行中直接预览：内部可变草稿m2-report-progress-v1保存分节结果，不进入普通历史；最终/失败仍产生独立结果，既有成功结果不覆盖。前端计数变化时同步草稿内容，避免相同草稿ID造成不刷新。

本轮验证结果见docs/test_report.md本任务条目；模拟HTTP不代表真实学科正确性。报告结构、引用、来源撤回和状态通过也不能保证模型答案正确。实际API拥堵/限额、复杂公式遗漏和真实模型坏输出仍可能发生，错误不再统一显示为模型不可用。

本次无新依赖、数据库表或迁移；使用现有AIResult/RemoteQuery/ProcessingJob。共享M1有界读取接口仅扩展切片偏移校验，不改解析器或现有Windows权限规则。BYOK、M4正式试卷/逐题配额和自动教师标注不在此修复范围。

## 重启与人工验收

在原项目目录，分别在后端/worker终端Ctrl+C后启动；前端仍运行时Ctrl+F5即可。

```powershell
# 后端终端
python -m uvicorn app.main:app --app-dir backend --reload
# worker终端（原PYTHONUTF8及模型环境保留）
$env:PYTHONPATH = 'backend'
python -m app.workers.materials
```

完整路径替代：
```powershell
& 'E:\Anaconda\python.exe' -m uvicorn app.main:app --app-dir backend --reload
& 'E:\Anaconda\python.exe' -m app.workers.materials
```

完整新终端准备见docs/setup_guide.md。本轮无需重新安装依赖/输入密钥；不要同时启动两份worker。

1. 新建报告预览选择Lecture 6，清除旧的“精确片段”选择以使用全文，核对原28段/8520字符（若未新增版本）完整纳入、预计2批。逐条展开核对正文，确认最多调用数后再发送，勿直接重用旧6段预览。
2. 观察批次计数，完成后展开各部分核对解释、例子、自测与来源；分别整理为笔记，刷新后检查历史。
3. 如真实模型超时/繁忙，检查已完成部分，主动勾选后继续未完成批次。续跑可能再次消耗失败步骤的账户额度；成功批不重复发。
4. 候选选择一份编程课件，核对覆盖范围，检查包含运算符/括号的不同选项不再误判；答案内容仍人工核对。
5. 桌面分别滚动两栏；窄屏通过快捷导航切换设置/结果，确认正文不横向溢出。

## 增量文件（不替代之前未上传改动）

新增：backend/app/services/ai_material_scope.py、backend/app/services/report_batches.py、backend/tests/m2/test_real_materials.py、frontend/src/features/ai/ai-workspace.css、本记录、evidence/ai-layout-390.png与ai-layout-1440.png。

修改：backend/app/services/{remote_ai,question_drafts,ai_context}.py、backend/app/ai/{providers,question_drafts,study_reports}.py、backend/app/workers/ai_queries.py、backend/app/schemas/{remote_ai,study_reports,question_drafts}.py、backend/app/routers/remote_ai.py、backend/tests/{test_study_reports,test_question_drafts,test_ai_error_details}.py；frontend/src/api/client.ts中的M2类型/API、frontend/src/features/ai/{index,RealQueries,ChunkPicker,QuestionDraftView,AIResultStatus}.tsx、frontend/tests/unit/m2/ai-result-status.test.ts、frontend/tests/e2e/m2/study-reports.spec.ts及重新生成的原M2六张验收截图；AGENTS/contracts/API/user/setup/test_report/README及gcx个人文档、剩余审计和协作记录。
