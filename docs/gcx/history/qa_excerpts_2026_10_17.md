# 资料问答引用稳定性修复（2026-10-17）

M2-QA-EXCERPTS，Codex辅助gcx。用户反馈练习生成成功，但资料问答仍因摘录不一致失败。本次不再仅加强提示词：将问答的原文摘录交给程序管理，模型只选择引用编号。

## 最终行为

- 问答提示词版本为zhipu-grounded-qa-v2。将已确认片段按最多400字符划分，每条附当前请求内唯一E1、E2等编号。纯空白切片不作证据，其余字符不改写、不另取资料；原有最多6片段、8000字符范围保持。
- 发送结构为sources[{source_id,excerpts:[{excerpt_id,text}]}]；不重复附带整段text，不增加资料正文。编号只是输入编码，API预览仍显示原片段，未增加外部数据。
- 模型输出evidence:[{excerpt_id}]，程序从本次表恢复source_id与连续原文，再执行既有引用校验，计算哈希和原文偏移；沿用归属、撤权、来源可用性检查与旧持久化格式。
- 未知编号拒绝；不从其他片段猜测替换，不做模糊文字匹配。兼容旧source_id/quote格式并逐字校验，混填字段拒绝。报告/候选协议不改。
- 不自动重试、不新增请求或迁移、不读取密钥或保存失败模型原文。编号存在只能证明引用来自资料，不能证明回答的语义正确。

## 加载与复测

离线验证：112项后端测试通过（25.43秒），运行qa_excerpts、citation_feedback、model_switch、remote_ai、study_reports、question_drafts、study_report_demo、ai_error_details、account_backups、ai_scope_history。新测试覆盖含英文/空格/换行的精确摘录与偏移/哈希、最多6片段的唯一编号及正文不扩增、未知编号拒绝且仅1次HTTP、混填字段拒绝；既有全流程测试改用编号响应，继续验证预览/确认/历史/保存笔记。相关Python文件Ruff通过。前端未改，未重跑浏览器或全量后端，不宣称既有Windows3项问题已修复或真实质量已验收。

后端--reload自动加载；未使用reload则重启后端。worker必须Ctrl+C后重启。原终端已保留项目目录/PYTHONPATH时用`python -m app.workers.materials`，或`& 'E:\Anaconda\python.exe' -m app.workers.materials`。前端无需重启，可刷新。

用户重新预览并确认“高阶函数的概念”，观察回答、点击引用回源、刷新历史；旧失败记录保留原状。未自动真实调用，实际模型复测待用户进行。

## 交付范围

仅修改原Hustudy-main；未同步GitHub、下载副本或旧83文件上传副本。代码：backend/app/ai/providers.py、backend/app/schemas/remote_ai.py、backend/tests/m2/test_remote_ai.py及新增backend/tests/m2/test_qa_excerpts.py。文档：AGENTS.md、docs/contracts.md、README.md、docs/gcx/README.md、collaboration/gcx/progress.md、docs/test_report.md及本记录。此前模型切换等增量仍须一起上传。
