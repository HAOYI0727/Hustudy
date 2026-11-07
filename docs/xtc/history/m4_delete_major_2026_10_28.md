# M4-ATTEMPT-DELETE-MAJOR-20 验证记录（2026-10-28）

xtc，Codex辅助，工作区未提交；人工接收待本人。用户明确删除作答时一并删除关联错题和复习计划，删除前提示。

## 最终行为

- 当前作答和每条历史作答均有删除入口；当前未选择时按钮置灰。确认永久删除该次答案、成绩、关联错题（含重做快照）和复习计划，同时移除其他错题上的该次复发事件；其他作答、题库和来源卷保留。可删除进行中作答，不代交卷。取消不丢草稿，成功清除恢复指针。API归属与有效课程复核、事务清理；无schema迁移。
- 整卷以明确大题题号为展示单位，完整题干只展示一次，下方按小问独立填写/保存/判分，原UUID与成绩逻辑保留。列表区分大题数和作答项数。
- 随机抽中小问直接展示冻结完整大题，含当前小问并按原号排列，不再只显示兄弟上下文或要求弹窗查看；只判分抽中项。公式/表格/插图保留，无其他小问答案泄露。
- 旧快照不回写：有原上下文则与本题兼容显示；完全缺失完整题干时明确说明，不自动编造。完整字段及图片在备份恢复中校验，课程包按现有结构化UUID映射，题干字段保持文本语义。

## 实际验证

- `PYTHONPATH=backend .venv/Scripts/python.exe -m pytest backend/tests/m4/test_attempt_deletion.py backend/tests/m4/test_question_context.py backend/tests/m4/test_m4_whole_paper_practice.py backend/tests/m4/test_question_bank.py backend/tests/m4/test_m4_strict_identity.py -q`：39 passed，18.18s。新增删除权限/确认/活跃作答/依赖/复发清理与其他作答保留；完整题干冻结、无答案、备份往返等。
- 补充大题计数后单独重跑整卷测试：4 passed，3.43s。
- 最终Chrome：`HUSTUDY_E2E_CHROME_CHANNEL=chrome node node_modules/@playwright/test/cli.js test tests/e2e/m4-attempt-delete-major.spec.ts tests/e2e/m4-whole-paper-practice.spec.ts tests/e2e/m4-strict-identity.spec.ts tests/e2e/bank-display-reference.spec.ts --project=chromium --grep '大题整卷|只抽一个子问|整卷完整作答|本地限制|AI入口保留|严格Markdown|ans6私人'`：10 passed，59.3s。覆盖390/1440大题一次展示、小问输入、公式表格、取消保留草稿、删除及计划清理、刷新、原完整作答与严格录入。
- 初轮新增浏览器用例误将review-tasks分页对象当数组断言；修正为items后最终10项全部通过。无业务失败未处理。
- TypeScript、Vite生产构建、相关Python Ruff通过。完整大题截图local/m4-major-unit-1440.png和390.png已目视检查；无横向溢出。
- 没有操作日常账号作答或进行任何真实AI调用；本地API和worker仅为加载代码重启，健康及新DELETE路由已检查。
- 未重复全站测试、WebKit、真实设备或团队验收，不推定通过。

代码范围：M4 question_context/attempt_deletion/bank_paper_practice/question_bank路由与快照公开、QuestionContext/BankPractice/MistakePractice/CSS；共享client可选字段、备份字段验证和课程包文本字段白名单。跨模块业务规则保持。公共契约/API及xtc功能/优化/进度、user.md同步。
