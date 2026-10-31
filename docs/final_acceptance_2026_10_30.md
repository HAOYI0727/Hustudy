# Hustudy 最终验收准备报告（2026-10-31）

本报告按照最终汇报要求，从功能展示、非功能性展示、主要关键技术、工作量四个方面整理当前版本，并补充 2026-10-31 的五轮 WebKit 回归记录。自动化结果、人工体验和真实模型质量分开记录；自动化通过不代替正式成员签收、真实设备验收或真实学科答案评审。

## 当前 `test` 账户真实数据验收记录（2026-10-31）

### 追加：真实 Safari 本地文件操作（2026-10-31）

本次不是只观察路由：通过 Safari 的系统文件选择器，从仓库 `fixtures` 目录实际选择并上传 `learning_loop_material.md` 与 `native_preview.pptx`。两份资料页面均显示“已保存 1/1”，后端分别核对 5 个 Markdown 片段、2 个 PPTX slide 片段，解析/索引最终为 `SUCCEEDED`。PPTX 原件接口返回 Office MIME，原格式阅读器可以翻到隐藏第 2 页；未因上传自动排队兼容 PDF。随后完成原文检索、书签、摘录建笔记、网页编辑保存，笔记 API 读取到新标题、正文和 revision=2。

阅读 AI 的真实网页操作也已完成：短 PPT 预览显示 2/2 段、108 字符和 `glm-5.3-flash`，勾选确认后真实调用一次并得到“证据不足”结果（输入文本不足，符合契约）；已有 194 段课件仅完成 194/194 段、32110 字符的发送预览，未重复消费模型额度。随后在“真题与模拟卷”中通过同一系统文件选择器导入 `question_bank_demo.md`，网页识别 4 道题并确认题库，题目审核状态和题库状态均在页面与 API 中一致；再从该已确认题库随机抽题、保存选择题和解答题答案并交卷，页面显示选择题正确、解答题保留人工自评入口。

本轮扩展复验还覆盖了用户手册中的课程日程/学习记录筛选、知识点候选与预填练习、笔记阅读模式/专注阅读/关系图谱/笔记 AI 发送预览、API 密钥掩码、完整备份生成下载删除、指南 FAQ、反馈保存、课程查找回源、AI 本地检索、长课件问答发送范围预览和错题空态。后端只读矩阵对登录、课程、资料、笔记、题库、AI、复习、备份、API 配置和四个课程工作区均返回 200；没有新增业务阻断。

追加的真实成功案例：Safari 上传 `glm_qa_demo.md` 后，解析/索引成功，2 个片段、42 字符；在资料阅读进入 AI 问答，明确确认后真实调用 `glm-5.3-flash`，约 8 秒返回 `grounded`，答案“五个苹果”，1 条引用回到“苹果数量”原文。后端记录 `model_mode=real`、`total_calls=1`、`selected_chunks=2`、`sent_chars=42`，页面和 API 状态一致。

本节记录真实 API、真实数据库和真实 worker 结果，区别于只观察页面跳转：

| 领域 | 实际验证 | 结果 |
|---|---|---|
| 共享基础层 | 登录、课程列表、课程工作区、学习记录、跨账户课程访问 | 账户登录 200；课程/工作区/学习记录正常；访问其他账户课程 404 |
| MaterialHub | 6 份实际 PPTX + 2 份 Markdown + 1 份 PDF + 1 份 DOCX、版本、2/5/7/98/194 段正文、原件、PDF 兼容预览、资料健康、任务历史、检索、学习关联 | PPTX/PDF/DOCX 原格式阅读和正文/索引均成功；兼容预览仍为按需能力；资料健康需检查 0 |
| 笔记闭环 | 真实资料片段创建笔记、revision 更新、引用读取、关键词搜索、反链、Markdown 导出、删除撤权 | 创建 201、更新 revision 2、引用 1 条、搜索命中、导出 text/markdown、删除后读取 404 |
| AI Study | `glm-5.3-flash` 账户配置、连接测试、资料预览、确认、AI_ANALYSIS worker、引用结果 | 连接成功；正文片段真实问答 `SUCCEEDED / grounded`，返回引用；标题页按规则返回证据不足 |
| ExamPilot | 严格 Markdown 题库上传、解析、导入、确认、随机抽题、审阅、开始作答、保存答案、交卷、评分、结果、删除作答 | 题库实际导入 4 题；确认成功；随机练习、作答、交卷评分和删除作答均完成 |
| 备份与资料包 | 完整账户备份生成、worker 完成、下载 hash 核对、删除备份；单资料包导出、下载 hash 核对、删除导出任务 | 账户备份 128,906,630 bytes，hash 与服务端一致；资料包 7,555,632 bytes，hash 与服务端一致 |
| 权限与错误 | 其他账户课程访问、错误路由/参数、无数据空态、模型失败状态 | 越权 404；错误参数 422；空题库/空笔记/空知识点明确显示；失败不伪装成功 |

本次测试在测试账户中产生的验收笔记和作答记录已删除；AI问答、题库确认及课程学习记录作为真实验收证据保留。

## 一、功能展示：案例、步骤与分工

### 1. 演示分工

| 角色 | 成员 | 展示范围 | 建议演示重点 |
|---|---|---|---|
| A 队长 | zhy | 共享基础层 + M1 MaterialHub | 注册/课程、资料上传、版本阅读、PPT 助手、引用笔记、学习记录与资料导出 |
| B | gcx | M2 AI Study | 资料范围选择、发送预览、长资料分批、引用校验、取消/续跑、账户模型配置 |
| C | fzk | M3 NoteGraph | Markdown 编辑、阅读模式、目录/公式/图片、双链、关系图谱、409 三方合并、标准数据包 |
| D | xtc | M4 ExamPilot | 严格 Markdown 题库、题目校正、知识标签、真题身份、练习、作答、错题和复习计划 |

成员姓名和最终签收人以团队确认记录为准；本表只提供演示编排，不代替成员验收。

### 2. 预置案例

| 编号 | 准备材料 | 操作流程 | 预期结果 |
|---|---|---|---|
| F01 | 新注册账户、两门课程 | 注册→登录→创建课程→切换课程→退出再登录 | 课程归属正确，刷新后仍可见，另一账户不能读取 |
| F02 | `fixtures/learning_loop_material.md`、PPTX/PDF/DOCX | 上传→等待解析/索引→查看资料检查→打开原格式阅读→搜索/书签 | 原件、解析、索引、预览状态分离；失败可重试且不伪装成功 |
| F03 | `fixtures/preview_demo.pptx` | 资料阅读→当前 PPT 助手→核对发送范围→生成知识点总结→查看页码引用→采纳为笔记草稿 | 只分析当前版本，引用页码连续且可回源，不自动保存或调用模型 |
| F04 | 账户级模拟模型配置 | API 接入→保存个人配置→资料问答/学习报告→确认发送→取消或续跑 | 发送前展示范围、模型和目的地；配置修订使旧预览失效 |
| F05 | 自制 Markdown 笔记 | 新建笔记→编辑→阅读模式→目录/字号→公式/图片/双链→手动保存→刷新恢复 | 阅读不写入；草稿、撤销、来源和双链保持；自动保存默认关闭 |
| F06 | 标准课程包/笔记文件夹包 | 选择范围→查看依赖→预览→确认→导入新课程或合并课程 | 新 UUID、同名安全区分、原课程不覆盖，未选内容不隐式带入 |
| F07 | `fixtures/question_bank_demo.md` 或严格 Markdown 样例 | 上传严格 Markdown→校正题干/答案/标签/年份/分值→确认题库 | 不合格格式明确拒绝；确认后才可练习，AI 建议必须人工核对 |
| F08 | 已确认题库 | 父子知识标签→按标签练习/整卷练习→保存作答→提交/自评→删除作答 | 作答恢复、重复题、公共题干、成绩和历史记录边界正确 |
| F09 | 错题与复习计划 | 错题回源→查看资料/笔记→设置日期→重做→更新掌握状态 | 回到原 UUID/版本，计划只在明确操作后改变 |
| F10 | 完整账户备份 | 导出→隔离空账户恢复→核对资料、笔记、题库、作答和图片 | 业务对象往返完整；密钥、偏好、任务和回收站不迁移 |

### 3. 功能验收命令

在项目根目录执行：

```bash
bash scripts/check.sh
HUSTUDY_E2E_CHROME_CHANNEL=chrome npm run test:e2e --prefix frontend -- \
  account-api.spec.ts ai-execution.spec.ts ai-supplements.spec.ts \
  note-assistant.spec.ts note-conflict-merge.spec.ts note-graph.spec.ts \
  note-reading.spec.ts portable-packages.spec.ts qa-batches.spec.ts \
  topic-hierarchy.spec.ts workspace-polish.spec.ts \
  m4-analysis-bulk-edit.spec.ts m4-ans6-scroll-auto.spec.ts \
  m4-attempt-delete-major.spec.ts m4-bank-default-example.spec.ts \
  m4-deepseek.spec.ts m4-illustration-library.spec.ts \
  m4-self-score.spec.ts m4-strict-identity.spec.ts \
  m4-topic-batches-recovery.spec.ts m4-whole-paper-practice.spec.ts
```

本轮实际结果：共享检查后端 **721 passed、2 skipped**；前端 **248 passed**；AI专项后端 **69 passed、2 warnings**。当前增量 E2E **162 passed、4 skipped**，容量脚本使用临时库完成 10 门课程、200 份资料、1000 条笔记、5000 个资料片段和 4 并发查询。手册示例闭环另有 Chromium 390px/1440px **2 passed**。

## 本轮十轮 Safari Computer Use 复验（2026-10-31）

本轮继续使用 `test` 账户和本地 Safari：

1. 主导航模块入口可打开，课程、知识点、资料、AI、笔记、题库和错题入口齐全。
2. 知识笔记空态、文件夹/标签/关系图谱/导入/导出/新建入口显示正常。
3. 新建笔记编辑器显示手动保存开关、Markdown工具、公式、图片、引用和草稿状态，默认自动保存关闭。
4. 笔记返回课程总览后，课程数据和导航恢复正常。
5. 课程总览显示资料数、AI来源结果和近期学习记录。
6. 学习记录可回到 AI 问答详情，显示 `glm-5.3-flash`、发送范围、来源和引用。
7. AI引用“回到原文”准确打开对应课程、资料版本和片段。
8. 资料片段书签可保存，阅读书签数量更新并显示回到原文/改名/移除入口。
9. 资料阅读工作区保持 5 份资料、处理中 0、资料检查需检查 0。
10. 题库页面显示严格 Markdown 导入、校正、标签、AI辅助、练习和真题身份审核入口，空数据状态清晰。

本轮未发现新的功能阻断、错误伪成功或布局级问题；一次旧元素索引失效通过重新获取可访问性树恢复，记录为自动化操作边界。

## 五轮 WebKit 回归与真实 Safari 实测

本轮在 Playwright WebKit 历史回归基础上，使用 Computer Use 直接操控本地 Safari `http://localhost:5173`，全部页面使用 `test` 账户：

- 第1轮：PPT 原格式加载、下一页/上一页、页码同步、返回文本视图和 98 段目录。
- 第2轮：课程总览、学习数据、学习记录弹窗、AI 成功/证据不足/模型失败记录区分和原对象入口。
- 第3轮：知识点学习空态、名称检索、无结果反馈和建立知识标签入口。
- 第4轮：资料库 5 份资料、5 份可检索资料、处理中 0；资料检查显示需检查 0、正文可用 5。
- 第5轮：AI 学习页面显示 `glm-5.3-flash`，原文检索、引用展开、回到原文和笔记草稿入口正常；真实 AI 问答结果已回写到课程总览。

五轮未发现新的前端阻断问题；真实 Safari 与 WebKit 结果分开记录，不把自动化通过等同于正式成员签收。

## 二、非功能性展示

### 1. 效率与容量

`scripts/verify_capacity.py` 的本轮隔离实测：

| 场景 | p95 或处理时间 |
|---|---:|
| 课程列表，4 并发、100 次 | 13.108 ms |
| 笔记列表，4 并发、100 次 | 229.570 ms |
| 资料检索，4 并发、100 次 | 270.053 ms |
| 笔记检索，4 并发、100 次 | 18.366 ms |
| 资料分页，4 并发、100 次 | 59.181 ms |
| 20 页 PPTX 解析/索引 | 0.2109 s |
| 50 页 PDF 解析/索引 | 0.1795 s |

这些是本机、合成资料和回环 HTTP 的工程基线，不是生产 SLA；真实 Office 复杂版式、网络、磁盘和多进程压力仍需单独验收。

### 2. 安全与数据可靠性

- JWT 会话与课程/资料/笔记/题库归属校验。
- API Key 按账户隔离、服务端加密，不进入备份、日志、浏览器存储或页面回显。
- Markdown/AI 输出进行 HTML、脚本、外链和图片安全检查。
- 文件路径、重复 ZIP 成员、压缩比、哈希、大小和类型严格校验。
- 资料版本、Citation、Note、Question、Attempt 使用 UUID/revision 和乐观锁。
- 409 冲突、未知保存结果、401 过期、来源撤权、任务取消和迟到响应均保留原草稿或进入明确错误状态。
- 所有自动化案例使用临时数据库、临时存储、自制材料和模拟 Provider，不读取日常账户、不发送真实资料。

### 3. 健壮性与用户体验

重点测试 390px、820px、1440px 布局、键盘焦点、离开保护、断网、503、401、409、Worker 恢复、关闭弹窗和迟到响应。错误不能伪装为空列表或成功；操作失败后可以显式重试，不能自动重复发送或覆盖草稿。

本轮旧版全量 E2E 的历史结果为 38 个已执行用例中 31 个通过、6 个失败、1 个中断；随后已将题库批量校正、整卷展示、已有/扫描 PDF、删除撤销、严格 ZIP、标签上限、自评和 AI 归类等 24 个场景迁移到当前严格 Markdown/AI 契约，Chromium 24/24 通过，剩余旧套件继续迁移。

### 4. 尚需人工补齐的边界

- Safari、iPhone、Windows 实机和读屏器体验。
- 真实模型额度、延迟和学科答案质量。
- 真实团队成员接收、课程包跨设备恢复和生产部署。
- 托管 Worker、多进程长压、真实大文件/复杂 Office 版式。
- 阅读标记与 M2 报告事实标签的真实上游数据联通。

## 三、主要关键技术

| 层次 | 技术与实现 |
|---|---|
| 前端 | React 19、TypeScript、Vite、React Router、TanStack Query、Ant Design、Vitest、Playwright |
| 后端 | Python 3.11、FastAPI、Pydantic、SQLAlchemy、Alembic、Pytest、Ruff |
| 数据组织 | SQLite/WAL、Alembic 迁移、课程归属、UUID、revision、UTC 时间、软删除与回收站 |
| 文件与任务 | 本地文件存储、hash 去重、原子写入、解析/索引/预览独立任务、租约/取消/恢复/迟到保护 |
| 检索与阅读 | FTS5、zh-bigram-v1、资料版本与 Citation、PDF.js、PPTX/Word 原格式读取、Markdown 安全渲染 |
| AI 集成 | 账户级智谱、DeepSeek/兼容 Chat Completions、Provider 抽象、预览/确认、引用核验、预算和续跑 |
| 学习闭环 | NoteGraph 双链/引用、严格题库 Markdown、知识标签、练习快照、错题回源、复习日程、标准数据包 |
| 质量保障 | 后端隔离测试、前端单测、Chromium/WebKit E2E、迁移漂移检查、Markdown/PDF 安全检查、容量探针 |

## 四、工作量统计

统计口径：使用 `git ls-files`，只计算已跟踪的主体源码、脚本和测试；不含 `node_modules`、构建产物、缓存、截图、数据库和上传资料。

| 范围 | 文件数 | 行数 |
|---|---:|---:|
| `backend/app` 主体程序 | 185 | 30,998 |
| `frontend/src` 主体程序 | 201 | 11,889 |
| `scripts` 工具脚本 | 24 | 2,015 |
| 主体程序与工具合计 | 410 | **44,902** |
| `backend/tests` | 103 | 24,639 |
| `frontend/tests` | 122 | 8,998 |
| 测试代码合计 | 225 | **33,637** |
| 主体程序、工具与测试合计 | 635 | **78,539** |

工作量汇报时建议以 **44,902 行主体程序/工具代码** 为主，以 **33,637 行测试代码** 说明质量保障投入；不要把依赖库、构建文件和生成文件计入项目工作量。

统计可复现命令：

```bash
python3 - <<'PY'
import subprocess
paths = subprocess.check_output(["git", "ls-files"], text=True).splitlines()
groups = {
    "backend_app": [p for p in paths if p.startswith("backend/app/") and p.endswith(".py")],
    "frontend_src": [p for p in paths if p.startswith("frontend/src/") and p.endswith((".ts", ".tsx", ".css"))],
    "backend_tests": [p for p in paths if p.startswith("backend/tests/") and p.endswith(".py")],
    "frontend_tests": [p for p in paths if p.startswith("frontend/tests/") and p.endswith((".ts", ".tsx"))],
}
for name, files in groups.items():
    print(name, len(files), sum(len(open(path, "rb").read().splitlines()) for path in files))
PY
```

## 后续优化优先级

1. **P0：测试契约收口**。把旧题库 E2E 迁移到严格 Markdown/AI 模式，恢复可重复的全量浏览器回归。
2. **P0：正式验收资料**。补齐四位成员实际姓名、演示截图、人工签收、真实设备记录和 40 任务状态。
3. **P1：真实大文件与复杂版式**。补充多 Worker、LibreOffice、扫描 PDF、Office 表格和长 PPT 压测。
4. **P1：跨设备部署**。使用统一 HTTPS 后端和持久存储验证账号、资料、文件和恢复流程。
5. **P2：学习增强**。在真实需求确认后再评估语义检索、自动间隔复习、自动图谱推理和更多题型。
