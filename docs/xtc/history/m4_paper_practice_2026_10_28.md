# M4-PAPER-PRACTICE-19 交付与验证（2026-10-28）

成员xtc，Codex辅助实现，工作区未提交；成员人工接收待本人检查。

用户明确口径：同次覆盖，不同次保留。同一attempt/question保存只覆盖最后值，不增加过程记录；不同attempt不删除。练习标题和历史每次作答仅显示当前中文状态，不与READY阶段并列；自评更新后刷新历史。增加“重新练习本套”，开始新的独立作答。

新增整卷元数据列表及创建接口见docs/api.md M4-PAPER-PRACTICE-19。整卷保留原题号、顺序、选项和重复题，不受随机抽题100题截断；最多500题，全部有效题目须确认且来源有效，否则明确拒绝整卷。原冻结快照、审阅、开始、保存、交卷和权限流程复用。题库已移除题目不纳入。列表范围最近200份；未知响应保留request_id可重试，同键变参409。无schema、依赖或模型调用。

## 实际验证

- 后端命令：`PYTHONPATH=backend .venv/Scripts/python.exe -m pytest backend/tests/m4/test_m4_whole_paper_practice.py backend/tests/m4/test_question_bank.py backend/tests/m4/test_m4_strict_identity.py -q`，34 passed，9.68s。
- 新增后端测试4项：题号/重复题/选项/答案不泄露；同次A→C→B仅B持久化、交卷幂等与不同次保留；归属/未确认/活动作答；101题完整与上限/失效来源/删除拒绝。
- 浏览器：`HUSTUDY_E2E_CHROME_CHANNEL=chrome node node_modules/@playwright/test/cli.js test tests/e2e/m4-whole-paper-practice.spec.ts tests/e2e/m4-strict-identity.spec.ts --project=chromium`，7 passed，38.7s。新增390/1440整卷完整流程：禁用未审核卷、重复题、文本/选项覆盖、刷新、最终状态、不同次独立；兼容严格Markdown、公式表格、ZIP/私人ans6样例、AI仅预览不调用。
- 初次默认Chromium因本地未安装该二进制未运行，改本机Chrome。早期检查发现下拉框精确名称匹配及旧公式用例误匹配隐藏上下文，增加显式aria-label并收窄测试到直接题干，最终上述7项均通过。未安装浏览器或新增依赖。
- TypeScript检查、Vite生产构建、涉及Python文件Ruff均通过。未为本轮重复全站后端/全部浏览器矩阵；无WebKit、真人/实机或团队签收结论。
- 截图位于私有local/m4-whole-paper-390.png和1440.png，已目视检查；无横向溢出。测试只用独立临时账户与数据库，不替日常账号交卷/新建作答/删除历史。

## 检查入口

本地后端已重启加载新接口。进入“真题与模拟卷 → 题库练习与作答 → 选择试卷完整练习”，选择可用卷、设置时长并载入；核对后开始。若有原作答尚未交卷，先完成原作答才能切换。历史展开后每次作答一条当前状态，完成后可重新练习本套。正式人工接收仍待本人。
