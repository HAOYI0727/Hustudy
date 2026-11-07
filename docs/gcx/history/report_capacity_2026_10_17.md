# 学习报告容量与限制修复（2026-10-17）

M2-REPORT-CAPACITY，Codex辅助gcx。用户确认其他AI功能测试正常，学习报告仍因learning_sequence、topics.evidence超过长度失败。根因是学习步骤≤8、每知识点证据≤3等小上限被作为整份生成的硬拒绝条件；截图中的列表级too_long并不表示资料解析失败。本轮只调整报告，问答/候选结构、配置与运行规则不变；不自动调用真实API。

报告提示词v6统一审查容量：学习目标/前置知识/复习建议各32项，学习步骤64项，知识点32项，例题12项，易错点/突破步骤/概念关系32项，每处依据64条、去重总引用256条。概述8000字符、讲解/答案12000字符、问题6000字符；名称/标签理由仍200/1000字符，关系描述3000字符。Prompt建议精炼3–12步骤、3–12知识点、通常1–6依据，安全上限不再等同于展示建议。

完整保留合法超出旧上限的内容，不切前8步或前3条引用；每一条引用仍核验。自测3–5、必填字段、标签来源、未知字段、合法UUID/摘录编号、真实原文与来源归属检查均保留。整体来源范围、输出token及1MiB响应预算未扩大。报告专属中文诊断提供字段、实际数量/上限，不显示模型原文；其他Provider消费者未启用该格式。

旧v5报告补入历史允许列表，旧数据不改写。M3单篇笔记50处引用仍是独立上限，报告超过该数量可阅读但须按更小范围整理笔记，不能把“报告可生成”当作“任意大报告可整体保存到一篇笔记”。无新依赖、表或迁移，其他M1/M3/M4业务不改。

新增test_report_capacity模拟截图形状：12步骤/12知识点/6引用/4例题/更长讲解与概述全部保留；第6条假引用仍拒绝，61条有效引用不再被旧50条上限拒绝；真正65步骤明确显示实际65/上限64而不输出原步骤，必填/标签来源/自测业务上限仍拒绝。

最终140项关联后端通过（18.76秒），23项Vitest、TypeScript及相关Ruff通过。共7项新增容量用例，并回归上轮自测补救、分批/续跑、历史与备份、问答/候选。无真实模型请求，未重跑浏览器/全量后端，旧Windows三项问题未处理。测试验证本地规则与流程，不代表真实模型成功率或答案正确性。

修改：AGENTS.md、docs/contracts.md、backend/app/schemas/study_reports.py、backend/app/ai/study_reports.py、backend/app/ai/providers.py中报告专属诊断、backend/app/routers/remote_ai.py历史列表、新增backend/tests/m2/test_report_capacity.py；README、docs/gcx/README/features、collaboration/gcx/progress、docs/test_report与本记录。仅原Hustudy-main，未同步GitHub、下载版或旧上传副本。

加载：worker需Ctrl+C后重新执行python -m app.workers.materials，或& 'E:\Anaconda\python.exe' -m app.workers.materials；原终端PYTHONPATH=backend保持。后端--reload会加载，否则重启后端；网页刷新。失败记录不自动重发，重新预览确认或主动确认继续未完成批次，成功批次不重发。真实模型合规率/学科质量仍待用户实际验收。
