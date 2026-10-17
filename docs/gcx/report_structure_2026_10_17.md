# 学习报告结构与概念关系反馈（2026-10-17）

M2-REPORT-STRUCTURE，Codex辅助gcx。用户确认问答引用修复有效，随后学习报告出现“report：不符合结构约定”。代码中报告层关系验证会在知识点重名，或概念链接不存在/自指/重复时产生此类笼统错误；失败模型原文未保留，不能断言本次具体是哪一种。未自动调用真实模型。

## 修改

- 报告提示词版本v3：明确完整顶层成功/证据不足格式、自测3–5项、名称唯一、先确定知识点再引用完整名称；只有一个知识点时不生成概念关系。
- 仅对可选概念关系移除不存在、自指和重复链接。保留首条有效链接，不猜测目标，不改写关系或补造知识点。服务端生成validation_notices，页面、报告Markdown和编辑笔记草稿都保留移除数量与人工复核提示。
- 知识点重名仍拒绝，改为明确且不含模型原文的固定提示。必填内容、题目、标签、引用、权限与来源可用性仍严格检查。模型不能自行设置validation_notices冒充校验提示。
- M2结果区将INVALID_OUTPUT/INVALID_JSON显示为“输出格式不符”，不再把结构问题误报为“模型不可用”。兼容provider_error状态和历史报告缺少新字段的情况；旧失败记录不改写或自动重试。

## 加载与交付

离线验证：116项后端回归通过（16.68秒；report_structure_feedback、qa_excerpts、citation_feedback、model_switch、remote_ai、study_reports、question_drafts、study_report_demo、ai_error_details、account_backups、ai_scope_history），22项Vitest通过，TypeScript与相关Ruff通过。新增用例验证重名安全提示、无效链接剔除且保留有效链接及原文引用、剔除链接不绕过伪造引用拒绝、模型无法伪造服务器提示、历史错误徽标与笔记提示保留。未重跑浏览器/全量后端，既有Windows3项权限前提问题未处理；没有真实模型调用。

原项目Hustudy-main有改动，下载副本、旧83文件上传副本和GitHub未自动同步；无新依赖/迁移。worker必须Ctrl+C后重启，原终端环境保留时为`python -m app.workers.materials`或`& 'E:\Anaconda\python.exe' -m app.workers.materials`。后端--reload自动加载，未使用reload则重启；前端Ctrl+F5刷新，无需重启Vite。

真实报告需用户重新预览、确认生成并核对答案与引用。通过结构或原文检查不代表教学内容语义正确；未声称全部M2完成。

涉及：AGENTS.md、docs/contracts.md、backend/app/schemas/study_reports.py、backend/app/ai/providers.py、backend/app/ai/study_reports.py、backend/tests/test_study_reports.py、新增backend/tests/test_report_structure_feedback.py、frontend/src/api/client.ts中M2报告类型、frontend/src/features/ai/{AIResultStatus.tsx,StudyReportView.tsx,index.tsx,report-review.ts}、frontend/tests/unit/{ai-result-status.test.ts,report-review.test.ts}、README.md、docs/gcx/README.md、本记录、collaboration/gcx/progress.md、docs/test_report.md。
