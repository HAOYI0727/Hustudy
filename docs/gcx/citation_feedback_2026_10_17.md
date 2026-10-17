# M2引用校验失败排查与反馈（2026-10-17）

用户切换GLM-5.3-Flash后练习生成报“模型引用未通过原文校验”。只读检查失败任务元数据：模型glm-5.3-flash、错误INVALID_CITATION、尝试次数1、无服务错误码。模型已返回并通过结构校验，失败发生于本地原文证据校验；与之前429/1305不同。

失败记录不保存模型原始回复，因此不能断言具体哪条引用错误。可能为source_id未来自发送片段，或quote不是对应片段逐字连续原文。此次不放宽引用、不伪造成功、不自动发送真实请求。

修改：细分上述两类安全错误消息，不输出模型原文或ID；候选提示版本v3明确区分片段/资料版本/Topic/原题ID，要求复制简短连续原文并保留标点空格换行。M2页面将INVALID_CITATION显示为“引用校验失败”，解释模型已返回但未生成可用结果，兼容已有历史记录。未更改共享状态枚举、数据库或M1功能。

提示词改进不能保证每次真实模型输出通过，尚未进行真实模型复测；旧失败记录不会自动变为成功。无新依赖或迁移。修改仅在原Hustudy-main，未同步下载副本、旧上传副本或GitHub。

验证：106项后端回归通过（23.79秒；citation_feedback、model_switch、remote_ai、study_reports、question_drafts、study_report_demo、ai_error_details、account_backups）；19项Vitest通过，TypeScript及本次Python文件Ruff通过。新增测试验证两类引用错误不泄露返回值、不做可能改变含义的空白模糊匹配，引用失败徽标兼容历史状态且服务异常/成功不受影响。初次沙箱运行因本地连接/缓存权限受阻，改为已授权的本地执行后通过；未改代码绕过权限、未重跑全量后端或浏览器测试，既有Windows3项问题仍待处理。

本次增量文件：AGENTS.md、docs/contracts.md、backend/app/ai/providers.py、backend/app/ai/question_drafts.py、backend/app/schemas/question_drafts.py、backend/tests/test_citation_feedback.py、frontend/src/features/ai/AIResultStatus.tsx、frontend/src/features/ai/index.tsx、frontend/tests/unit/ai-result-status.test.ts、README.md、docs/gcx/README.md、本记录、collaboration/gcx/progress.md、docs/test_report.md。上传时还需包含上次模型切换与剩余工作审计的增量；原83文件副本没有自动更新。

加载：后端使用--reload时自动加载；否则重启后端。worker必须Ctrl+C后重新启动；前端Ctrl+F5刷新，无需重启Vite。沿用现有终端目录/环境时worker命令为`python -m app.workers.materials`，或`& 'E:\Anaconda\python.exe' -m app.workers.materials`。新终端完整启动步骤见[模型切换记录](model_switch_2026_10_17.md)。
