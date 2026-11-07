# 样例报告自测缺少依据补救（2026-10-17）

M2-REPORT-SELFCHECK，Codex辅助gcx。用户选materialhub_demo资料进行真实AI生成，响应漏掉前三道self_checks.evidence。页面“真实AI”和批次错误说明其为真实生成路径，不能把使用样例资料等同于固定演示。此错误发生在JSON业务结构检查，与资料读取无关；此前模拟回归未覆盖这个具体遗漏。

报告提示词v5逐项强调自测question/answer/evidence。官方JSON模式通过response_format=json_object启用，并在messages描述结构，仍须程序校验：[官方结构化输出](https://docs.bigmodel.cn/cn/guide/capabilities/struct-output)。本次未假设支持未核实的服务端strict schema，也未自动发送修复请求。

最终ReportOutput/TeachingReport/ReportExercise仍要求每项证据。仅模型接收层使用单独DraftSelfCheck识别缺省或空引用的自测；生成阶段舍弃这类原题，保留有引用原题。依据已逐字引用校验的知识点解释、原文摘录、报告例题建立基础自测模板，补至至少3题，再按严格TeachingReport验证。不会给原题猜测引用，不复制无引用原答案。

基础自测标注generation_origin=rule_generated，整体validation_notices说明丢弃/补充数量；页面显示“基础自测 · 根据已校验知识点或例题生成”，Markdown和笔记保留提示。此为保守基础练习，不承诺达到模型原创题的多样性或学科难度。其他必填字段、非法/伪造引用仍拒绝，不凭兜底把坏报告判为成功。

报告v4历史补入允许列表，旧记录不改写。代码无新依赖/迁移，仅原Hustudy-main，GitHub/旧上传副本未更新；实际密钥/用户资料不改。需要重启worker，后端reload自动加载，否则重启；前端Ctrl+F5刷新。原终端命令python -m app.workers.materials，或& 'E:\Anaconda\python.exe' -m app.workers.materials（PYTHONPATH=backend保留）。如上一轮完整重启，见[真实资料修复](real_materials_2026_10_17.md)。

修改：AGENTS.md、docs/contracts.md、backend/app/schemas/study_reports.py、backend/app/ai/study_reports.py、backend/app/routers/remote_ai.py、backend/tests/m2/test_report_selfcheck_completion.py；frontend/src/api/client.ts中报告练习类型、frontend/src/features/ai/StudyReportView.tsx、frontend/tests/unit/m2/report-review.test.ts；README/docs/gcx与collaboration/gcx进度、docs/test_report及本记录。

离线后端133 passed/18.67秒（前轮126项关联测试加7项新用例）：覆盖缺1/3道引用的原题被弃且不泄露原题内容、只调用一次HTTP、严格持久契约不接受缺引用、知识点/例题/原自测假引用与其他字段缺失仍失败。相关Ruff通过。真实模型尚未复测，不将模拟测试通过称为真实生成成功率。

前端23项Vitest通过（490ms），包括新增真实渲染基础自测标识/整体提示及笔记提示保留；TypeScript通过。本次不重跑浏览器/全量后端，前次Chrome四项不能冒记为本次重跑。
