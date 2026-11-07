# M2-STUDY-REPORT-01 手动上传清单

2026-10-17 M2-TOPICS-REUSE：新生成练习题逐题选择/校验本次所选知识点子集并显示名称；三种真实AI预览可显式复用同用户/课程/请求/来源/模型/当前提示词下的完整成功结果，无新任务或模型调用。保留确认后重新生成；变更或失效则拒绝复用，无依赖/迁移。新增ai_result_reuse.py、ReusableResult.tsx、test_ai_topics_reuse.py、ai-topics-reuse.test.ts、ai-result-reuse.spec.ts必须一起上传；[完整本次清单](topics_reuse_2026_10_17.md)。旧83项副本不代表累计修改。

2026-10-17最新增量M2-REAL-MATERIALS：[新增与修改文件、验证、重启](real_materials_2026_10_17.md)。新增ai_material_scope.py、report_batches.py、test_real_materials.py、ai-workspace.css等必须一并提交，不可仅覆盖原83项旧副本。无新依赖/迁移；旧已上传/已下载目录未自动更新，之前模型切换/引用等未提交增量也需保留。以下清单为历史记录。

2026-10-16，Codex辅助gcx；本地无Git，以下按本轮实际编辑路径整理，不是git diff。不含自动生成的Office运行时、dist、缓存、用户数据或密钥。本轮没有删除业务文件，也没有新增迁移/依赖。上传前以团队最新版本对照，保留其他成员修改。

## 源码与检查入口

- `backend/app/ai/providers.py`
- `backend/app/ai/study_reports.py`
- `backend/app/schemas/remote_ai.py`
- `backend/app/schemas/study_reports.py`
- `backend/app/services/ai_context.py`
- `backend/app/services/remote_ai.py`
- `backend/app/routers/ai.py`
- `backend/app/routers/remote_ai.py`
- `backend/app/workers/ai_queries.py`
- `backend/tests/conftest.py`
- `backend/tests/m2/test_study_reports.py`
- `frontend/src/api/client.ts`
- `frontend/src/features/ai/index.tsx`
- `frontend/src/features/ai/RealQueries.tsx`
- `frontend/src/features/ai/StudyReportView.tsx`
- `frontend/src/features/ai/study-reports.css`
- `frontend/playwright.config.ts`
- `frontend/tests/e2e/m2/study-reports.spec.ts`
- `scripts/verify_markdown.mjs`

## 文档与自制截图

- `AGENTS.md`
- `README.md`
- `main_idea.md`
- `Hustudy_team_collaboration.md`
- `hustudy/main_idea.md`
- `hustudy/Hustudy_requirements.md`
- `collaboration/roles.md`
- `collaboration/README.md`
- `collaboration/workflow.md`
- `docs/zhy/history/collaboration/github_sync.md`
- `collaboration/task_board.md`
- `collaboration/handoff.md`
- `collaboration/gcx/README.md`
- `collaboration/gcx/progress.md`
- `collaboration/xtc/README.md`
- `collaboration/xtc/progress.md`
- `docs/README.md`
- `docs/api.md`
- `docs/contracts.md`
- `docs/decisions.md`
- `docs/progress.md`
- `docs/traceability.md`
- `docs/test_report.md`
- `docs/user_guide.md`
- `docs/setup_guide.md`
- `docs/gcx/README.md`
- `docs/gcx/features.md`
- `docs/gcx/optimizations.md`
- `docs/gcx/design/m2_plan.md`
- `docs/gcx/acceptance/study_report_acceptance.md`
- `docs/xtc/README.md`
- `docs/xtc/features.md`
- `docs/xtc/optimizations.md`
- `docs/gcx/evidence/study-report-390.png`
- `docs/gcx/evidence/study-report-1440.png`
- `docs/gcx/history/changed_files_2026_10_16.md`（本清单）

xtc目录仅同步用户授权的分工更正，不填写其个人成果或签收。测试结论见[验收](../acceptance/study_report_acceptance.md)，交接H-20261016-GCX-001仍待本人/成员接收。

## M2-CANDIDATES-01 本轮新增或再次修改（累计清单补充）

以下与上方文件列表取并集，重复路径只需上传最终版本。无业务文件删除、无新依赖/迁移，不上传.env/data/node_modules/dist或缓存。

### 源码、测试及公开结构

- `backend/app/schemas/question_drafts.py`（新增）
- `backend/app/schemas/study_reports.py`
- `backend/app/schemas/remote_ai.py`
- `backend/app/ai/question_drafts.py`（新增）
- `backend/app/ai/providers.py`
- `backend/app/ai/study_reports.py`
- `backend/app/services/question_drafts.py`（新增）
- `backend/app/services/study_report_demo.py`（新增）
- `backend/app/services/exam_ai_context.py`（新增M4只读桥）
- `backend/app/services/ai_context.py`
- `backend/app/services/remote_ai.py`
- `backend/app/routers/remote_ai.py`
- `backend/app/routers/ai.py`
- `backend/app/workers/ai_queries.py`
- `backend/tests/m2/test_question_drafts.py`（新增）
- `backend/tests/m2/test_ai_error_details.py`（新增）
- `backend/tests/m2/test_ai_scope_history.py`（新增）
- `backend/tests/m2/test_study_report_demo.py`（新增）
- `frontend/src/api/client.ts`
- `frontend/src/features/ai/ChunkPicker.tsx`（新增）
- `frontend/src/features/ai/QuestionDraftView.tsx`（新增）
- `frontend/src/features/ai/RealQueries.tsx`
- `frontend/src/features/ai/index.tsx`
- `frontend/src/features/ai/study-reports.css`
- `frontend/tests/e2e/m2/question-drafts.spec.ts`（新增）
- `docs/gcx/design/question_draft_schema.json`（新增公开结构）

### 本轮新文档和截图

- `docs/gcx/acceptance/candidate_acceptance.md`
- `docs/gcx/acceptance/evaluation_checklist.md`
- `docs/gcx/evidence/question-drafts-390.png`
- `docs/gcx/evidence/question-drafts-1440.png`

上方已列公共文档及gcx个人记录已同步当前能力/不按日期分段的要求；`docs/gcx/design/m2_plan.md`重写为状态与依赖，旧验收/贡献历史保留。`docs/gcx/evidence/study-report-390.png`和`study-report-1440.png`已更新。交接H-20261016-GCX-002待接收，测试范围详见本轮验收；不把本清单当已上传。

## 结构化错误反馈修正追加

上传清单另含：backend/app/ai/providers.py、backend/app/ai/question_drafts.py、backend/app/schemas/question_drafts.py、backend/tests/m2/test_ai_error_details.py、backend/tests/m2/test_remote_ai.py、backend/tests/m2/test_question_drafts.py、backend/tests/m2/test_study_reports.py，以及本次更新的AGENTS.md、README.md、docs/contracts.md、docs/gcx/features.md、docs/gcx/optimizations.md、collaboration/gcx/progress.md、collaboration/handoff.md、docs/test_report.md、本清单。无新增环境/依赖或数据库迁移。

## M2-LABEL-REVIEW-01手动上传增量（取与前文的并集）

新增/修改以下文件，以及本清单自身。截图由临时API验收生成；不上传.env、data、node_modules、dist、缓存或浏览器报告。

- `backend/app/schemas/study_reports.py`
- `backend/app/ai/study_reports.py`
- `backend/app/services/study_report_demo.py`
- `backend/tests/m2/test_study_reports.py`
- `frontend/src/api/client.ts`
- `frontend/src/features/ai/index.tsx`
- `frontend/src/features/ai/report-review.ts`
- `frontend/src/features/ai/ReportLabelEditor.tsx`
- `frontend/src/features/ai/StudyReportView.tsx`
- `frontend/src/features/ai/study-reports.css`
- `frontend/tests/unit/m2/report-review.test.ts`
- `frontend/tests/e2e/m2/study-reports.spec.ts`
- `frontend/tests/e2e/m2/question-drafts.spec.ts`
- `AGENTS.md`
- `README.md`
- `docs/contracts.md`
- `docs/api.md`
- `docs/test_report.md`
- `docs/traceability.md`
- `docs/user_guide.md`
- `docs/gcx/README.md`
- `docs/gcx/features.md`
- `docs/gcx/optimizations.md`
- `docs/gcx/design/m2_plan.md`
- `docs/gcx/acceptance/basic_acceptance.md`
- `collaboration/gcx/README.md`
- `collaboration/gcx/progress.md`
- `collaboration/handoff.md`
- `docs/gcx/evidence/label-review-390.png`
- `docs/gcx/evidence/label-review-1440.png`
- `docs/gcx/evidence/study-report-390.png`
- `docs/gcx/evidence/study-report-1440.png`
- `docs/gcx/evidence/question-drafts-390.png`
- `docs/gcx/evidence/question-drafts-1440.png`

## M2入口命名增量

- frontend/src/features/ai/index.tsx
- frontend/tests/e2e/m2/study-reports.spec.ts
- frontend/tests/e2e/m2/question-drafts.spec.ts
- frontend/tests/e2e/shared/responsive-layout.spec.ts（仅同步已有AI按钮定位）
- AGENTS.md、README.md、docs/user_guide.md、docs/gcx/README.md、features.md、optimizations.md、collaboration/gcx/README.md、progress.md、collaboration/handoff.md、本清单。
- docs/gcx/evidence下study-report、question-drafts、label-review各390/1440截图由本轮既有流程更新，展示新名称；不上传测试临时数据和运行报告。

入口命名复验另同步docs/test_report.md。

## 上传文件清单整理

另含docs/gcx/history/upload_guide.md、upload_files_full.txt、upload_files_m2.txt。按当前目录过滤出完整源码清单和累计M2去重清单，不含.env、运行数据或缓存；不代表已核对远端差异。

## 2026-10-17 完整范围审计（旧上传合并后的新文档变更）

新增docs/gcx/history/m2_remaining_audit_2026_10_17.md；更新AGENTS.md、README.md、docs/gcx/design/m2_plan.md、docs/gcx/README.md、collaboration/gcx/README.md、collaboration/gcx/progress.md和本清单。仅文档，尚未再次上传；旧83项上传副本保留原始已验证版本，不将新增审计伪称已包含于旧提交。

## 2026-10-17 GLM-5.3-Flash切换（旧合并后的新改动）

以下为此次代码与相关最新文档；不上传本机.env。旧83项清单/上传副本不改写，不伪称新内容已上传。

- `backend/app/core/config.py`
- `backend/app/ai/providers.py`
- `backend/app/services/remote_ai.py`
- `scripts/configure_zhipu.py`
- `.env.example`
- `backend/tests/conftest.py`
- `backend/tests/m2/test_remote_ai.py`
- `backend/tests/m2/test_model_switch.py`
- `frontend/tests/e2e/m2/study-reports.spec.ts`
- `AGENTS.md`
- `README.md`
- `docs/contracts.md`
- `docs/api.md`
- `docs/decisions.md`
- `docs/test_report.md`
- `docs/setup_guide.md`
- `docs/gcx/README.md`
- `docs/gcx/features.md`
- `docs/gcx/optimizations.md`
- `docs/gcx/design/m2_plan.md`
- `docs/gcx/history/model_switch_2026_10_17.md`
- `docs/gcx/history/m2_remaining_audit_2026_10_17.md`
- `collaboration/gcx/README.md`
- `collaboration/gcx/progress.md`
- `collaboration/handoff.md`
- `docs/gcx/history/changed_files_2026_10_16.md`

项目外diagnose_zhipu_minimal.py也增加模型参数，但不是运行必需，不包含于源码交接。

本轮既有浏览器测试重新生成docs/gcx/evidence下study-report、question-drafts、label-review的390/1440截图（临时账户/模拟模型），若同步验收图片请一并上传；不上传test-results或真实运行数据。
