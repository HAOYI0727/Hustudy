# Hustudy · 课程学习工作台

Hustudy 面向大学课程学习，将个人课件、带来源的 AI 理解、知识笔记、本人题库和错题复习连接在同一门课程中。课程总览是主入口，资料阅读是原文基础；用户可以不配置 AI，先完成阅读、记笔记、题库练习与复习。

- [完整使用手册](user.md)：按实际页面操作，包含闭环实例、限制、错误处理和测试命令。
- [主设计与实施路线](main_idea.md)：设计原则、架构、数据关系、40项任务和验收方案。
- [四人协作与当前进度](Hustudy_team_collaboration.md)：实际负责人、跨模块交接和待办。
- [接口](docs/api.md)、[共享契约](docs/contracts.md)、[技术记录目录](docs/README.md)、[历史测试记录](docs/test_report.md)。历史记录带有各自日期，不能当作当前全量测试结论。

## 1. 完整学习闭环

```text
创建课程 → 上传并核对原文 → 检索 / 提问 / 阅读报告
   → 整理带引用的笔记 → 导入本人题库并校正核验
   → 随机 / 整卷 / 自行选题练习 → 保存答案、交卷、自评
   → 错题回原题与课件 → 补充笔记 → 安排日程并重做
   → 回课程总览找回进度 → 导出成果或备份迁移
```

闭环通过真实 UUID、资料版本、原文片段、引用和作答快照串联。打开页面不会自动表示已学习、已掌握或已完成计划。题库原题出处与知识标签关联的讲义来源分开保留；报告知识点、笔记标签和题库知识标签也不是同一套实体。

## 2. 当前功能

| 页面 / 范围 | 实际能力 |
| --- | --- |
| 共享基础层 | 用户注册与 JWT 登录；账户、课程归属校验；课程分类/标签/改名/删除影响预览；共享路由、未保存离开保护、401原账户恢复、统一错误与分页；文件存储、Alembic迁移、任务与worker管理 |
| 课程总览 | 课程空间、真实学习摘要、继续原资料/笔记/AI结果/进行中作答；全部学习记录；当前课程日程的添加、查询、完成/恢复待办、删除及回原错题；标准课程包入口 |
| M1 · 资料阅读 | PPTX/PDF/DOCX/Markdown上传，批量队列与逐项结果；资料分类/标签/筛选/跨页批量整理；不可变版本、原格式/文本阅读、版本文字对照、全文查找、本机书签；解析/索引/兼容预览独立状态、资料检查与原任务恢复；扫描PDF人工补录确认；图片/截图来源、引用这份原文的笔记、跨模块学习关联、范围资料包 |
| 当前PPT阅读助手 | 固定当前版本的知识点总结、复习提纲、笔记写作；发送预览与覆盖说明；知识点关键词目录、按有效引用显示页码、跟随当前页、单点摘记与整部分笔记草稿。调用复用M2，保存复用M3 |
| M2 · AI学习 | 本地原文检索、资料问答、学习报告；多资料/历史版本/片段范围与补充笔记；逐次发送确认、JSON/schema/逐字引用核验；长资料分批、检查点、显式续跑、调用与修复预算；历史结果、精确复用与最多3条相近文字历史推荐（查看后人工确认使用） |
| M3 · 知识笔记 | Markdown管理/编辑/预览/阅读/专注模式、模板与快捷键；手动及可选自动保存、恢复副本、revision冲突与逐段三方合并；目录/标签/导入/批量整理、UUID双链/反链/只读图谱、资料引用、图库、公式面板；可选识别文字/音频后核对插入；多模型笔记助手先预览后采纳；导出、标准文件夹包与回收站 |
| M4 · 真题与模拟卷 | 严格Markdown/Markdown ZIP、已有资料导入；确认后AI文件转写、PDF原页/公式识别；题目校正/拆合/重复设置/删除、年份分值批量编辑、真题身份确认、知识标签层级/别名/合并/AI归类、插图与答案文件匹配；统计快照/资料缺口/蓝图；随机、整卷、自行选题三种练习；答案保存恢复、选择题判分、解答题自评、作答记录管理 |
| 错题复习 | 原题与来源回看、显式重做、掌握/保留/移出、复发记录、每日答对目标、按账户时区安排/完成/改期复习计划；保留原试卷成绩 |
| 课程查找 | 当前课程资料与笔记关键词检索、资料分类/标签/版本过滤、命中摘录和回原对象；资料筛选不限制笔记结果 |
| 备份与恢复 | 完整账户ZIP和空账户恢复；与离线阅读资料包、笔记ZIP、可选择导入的标准数据包分开 |
| API接入 | 当前账户智谱Key、DeepSeek/兼容Chat Completions模型配置、模型切换和明确连接测试；密钥加密且不回显，不从其他账户或旧共享Key回退 |
| 使用指南 / 反馈 / 外观 | 站内按章阅读/搜索/下载根user.md及自制示例；提交使用反馈；统一主色与卡片、中文黑体/宋体/楷体、英文Times New Roman优先、12–18px字号、导航/密度/宽度和响应式布局 |

原独立“知识点学习”工作区已移除；相关能力通过资料阅读、AI报告及题库考点入口使用。**AI自动出新题已停用**，当前练习来自已核验的本人题库；“笔记AI整理旧接口停用”不表示新的显式笔记助手不能用。

## 3. 环境与快速复现

### macOS / Linux

准备 Git、Python **3.11或3.12**、Node.js **24.x**及npm；当前PDF.js运行时要求较新的Node，避免旧Node环境。安装依赖需要网络，真实AI另需供应商账号、可用模型权限与额度。

```bash
git clone https://github.com/HAOYI0727/Hustudy.git
cd Hustudy
bash scripts/setup.sh
```

已有仓库直接在根目录操作，不必再次克隆。`setup.sh`创建或复用`.venv`、安装`backend/requirements.lock`、执行`npm ci`、仅在缺失时复制`.env.example`，并初始化空值/旧占位JWT密钥。新环境可用`PYTHON_BIN=python3.12 bash scripts/setup.sh`；不会替换已有虚拟环境。

分别开两个终端，工作目录均为仓库根：

```bash
# 终端一：API；开发环境默认自动管理一个资料worker
bash scripts/dev.sh
```

```bash
# 终端二：前端；predev自动生成本地Office/公式资源
npm run dev --prefix frontend
```

- 网站：`http://localhost:5173`
- API健康检查：`http://127.0.0.1:8000/health`
- OpenAPI：`http://127.0.0.1:8000/docs`，业务接口以`/api/v1`为前缀。
- 首次启动自动执行数据库迁移，当前迁移链至`0024_bank_answer_imports`。首次使用自行注册账号，**仓库不附带通用演示账号、密码、课程或Key**。

只单独启动uvicorn时，开发环境同样按配置托管worker。需要外部worker时设置`HUSTUDY_WORKER_AUTOSTART=false`并另开`bash scripts/worker.sh`；不要同时启动多份无意的worker。更新worker代码后先保存工作、重启后端与worker，再核对处理中任务。

### Windows PowerShell

Bash脚本不是原生PowerShell脚本。可在仓库根创建独立环境，使用不含平台固定依赖的requirements入口：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
# 仅第一次且.env不存在时复制；已有配置不要覆盖
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
.\.venv\Scripts\python.exe scripts/configure_auth.py
npm ci --prefix frontend
# 终端一
$env:HUSTUDY_WORKER_AUTOSTART = 'true'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload
# 终端二（同一仓库根目录）
npm run dev --prefix frontend
```

平台差异和可选OCR组件须在目标机器另验；上述命令不代表本轮已完成Windows实机验收。

### AI与可选能力

普通本地学习不需要Key。登录后在“API接入”保存**当前账户**配置，再明确测试连接；保存不会自动请求供应商。默认智谱模型ID为`glm-5.3-flash`，旧`glm-4.7-flash`仍兼容；以账户实际选择为准。不要把历史`.env`配置脚本当成网页个人Key的配置入口。

| 能力 | 额外条件 |
| --- | --- |
| 原格式PPTX/DOCX、PDF阅读与正文解析 | 项目Python/Node依赖即可；不需要系统Office转换器 |
| PPTX/DOCX兼容PDF与兼容页截图 | 安装LibreOffice、启用兼容转换、保持worker运行；必要时设置`HUSTUDY_LIBREOFFICE_PATH`。生产默认关闭，需显式`HUSTUDY_COMPATIBILITY_PREVIEW_ENABLED=true` |
| 笔记本地OCR/音频转写 | 可选`backend/requirements-capture.txt`/锁文件及预先准备的本地音频模型；不在用户任务中自动下载模型 |
| 题库本地PDF/OCR | 可选`backend/requirements-bank-ocr.lock`；AI原页转写另需所选模型支持视觉 |
| DeepSeek或其他兼容接口 | 在API接入保存账户模型配置；自定义主机还受服务端`HUSTUDY_ADDITIONAL_AI_HOSTS`允许名单约束 |

不能保证任意损坏文件、复杂字体/动画或供应商请求必定成功；失败应明确、有界、可核对，不能伪装成成功。

## 4. 数据、预算和部署

- 默认SQLite为`data/hustudy.db`，文件位于`data/storage`；修改对应环境变量可改变位置。`.env`、data、依赖、构建和浏览器缓存不应提交到仓库。
- 普通资料单文件≤**30MiB**（31,457,280字节），一批≤20份/100MiB；图片单张≤10MiB。答案导入≤30MiB、PDF≤20页、目标题库≤100题。不同导入/备份工具有独立预算，以页面和手册为准。
- 原件保存、解析、索引、兼容PDF是独立状态。上传不会自动排队Office转PDF；阅读中按需点“生成兼容 PDF”。长转换预算600秒、预览租约660秒；成功仍需逐份核对页数和视觉内容。
- `localhost`数据只属于本机。GitHub同步源码不会同步账号。跨电脑使用须连接同一个持久后端，或使用完整备份迁往新数据库空账户。
- 生产前端：`npm run build --prefix frontend`生成`frontend/dist`；默认同源`/api/v1`。不同地址可在构建前设`VITE_API_BASE_URL`，其中只能放公开地址，不能放Key。
- `deploy/nginx/`和`deploy/systemd/`是部署模板，需替换目录/域名/证书/用户；配置HTTPS、路由回退、CORS、持久数据库与文件、凭据目录和外部worker。示例Nginx上传上限35m仅覆盖普通资料，若开放100MiB标准包或256MiB账户恢复，须按对应接口调整代理限制和磁盘预算。
- 备份：账户ZIP不含密码/Key；恢复保留业务UUID并映射为目标用户，只能到无业务数据且无UUID冲突的空账户。标准包导入则为选中对象创建新UUID，可合并到已有课程。

## 5. 测试与验收

自动测试使用隔离数据库、文件和模拟Provider，不应替换为日常8000/5173服务或真实Key。以下是**可执行入口**，不是本轮已经全部通过的声明。

```bash
# Ruff、后端pytest、迁移、Markdown/PDF安全渲染、前端单测、类型和构建
bash scripts/check.sh

# 前端单独验证
npm run test --prefix frontend
npm run check --prefix frontend
npm run build --prefix frontend

# 首次准备浏览器；Linux可能还需系统浏览器依赖
cd frontend
PLAYWRIGHT_BROWSERS_PATH=../.tools/playwright npx playwright install chromium webkit
cd ..
npm run test:e2e --prefix frontend
# 已安装Chrome时可替代Chromium：
# HUSTUDY_E2E_CHROME_CHANNEL=chrome npm run test:e2e --prefix frontend

# 共享检查、双引擎与隔离容量；日志位置由脚本输出
bash scripts/accept_captain.sh
```

Playwright默认开启临时API **8056**、前端 **5178**，单worker、零自动重试；不能与另一测试进程争用这些端口。手动闭环使用[手册第3章](user.md#3-用示例走完一次学习闭环)的自制资料和严格题库；真实模型测试需要本人另行核对发送并同意，自动测试不会证明真实教学质量。

本次文档更新验证（2026-11-07）：手册单元4项通过；手册/示例闭环双引擎首轮10通过、2个旧指南数量断言失败（页面已由9条变8条），按当前页面修正后2项定向复验均通过，共12个不同场景经复验通过；TypeScript/生产构建通过。站内指南同步默认手动保存与已实现关系图谱的说明。未重跑全站全量、未调用真实模型、未操作日常账户或代签成员验收。

最近可追溯实测：

- [2026-11-06 AI真实验证](docs/zhy/shared_platform/ai_live_validation_2026_11_06.md)：test账户资料问答4条引用；91片段长报告分3批/3个确认窗口完成，29知识点、4例题、15自测、78条去重引用。相关199后端/22前端用例通过；不是当前全站全量结论。
- [2026-11-06 PDF验证](docs/zhy/materialhub/pdf_preview_validation_2026_11_06.md)：本机28份PPTX共2711页的页数核对与双引擎抽页，非所有Office版式保证。
- [M4答案导入](docs/xtc/implementation/answer_import.md)、[自选组卷](docs/xtc/implementation/manual_practice.md)、[手动日程](docs/xtc/implementation/course_manual_agenda.md)：独立新增能力及验收边界。
- [四方面验收汇报](reference/Hustudy四方面验收汇报.docx)：2026-11-07独立文档，含四人分工、数据库恢复案例、功能/非功能/关键技术及当前主体代码量37,618行。样式、测试和工程辅助单列，附统计复核命令；既有失败、待演练及人工验收分别说明。

## 6. 当前边界与后续工作

1. 教师强调：M2有只读适配/核验逻辑，M1尚无阅读标记持久化入口及reader注册；当前不能演示端到端教师强调。M4真题身份录入已实现，旧“仍缺真题身份入口”的说明已过时；报告事实标签仍须有效身份、映射和引用共同成立。
2. 长问答先逐批摘录依据再统一回答；长报告各批独立生成，**没有跨批全文AI融合**。引用结构有效不等于教学内容正确。
3. AI自动生成新题、旧识别后直接新建笔记/旧自动整理接口不作为现行功能；不承诺语义搜索、自动间隔复习、多人实时协作或自动云同步。
4. 正式40任务签收、真人试用、完整跨设备矩阵、长期负载与公共部署需保留独立证据；不宣称“全站无bug”。

## 7. 工程结构与维护

2026-11-07目录已按模块整理：后端tests与前端unit/e2e按shared、m1–m4、integration分类；docs只保留四个成员业务目录及公共文件/必要licenses。生成物统一到根`.artifacts`，fixtures保留为版本化输入。[清理范围、数据保留和真实测试问题](docs/zhy/shared_platform/repository_organization_2026_11_07.md)。

```text
backend/app/       FastAPI路由、模型、领域服务、适配与worker
backend/migrations/  Alembic迁移（当前至0024）
backend/tests/     隔离测试，按shared/m1/m2/m3/m4/integration分类
frontend/src/     React工作区、共享路由/主题、四模块
frontend/tests/   Vitest与Playwright，按共享层/四模块/集成分类
fixtures/         自制闭环资料、题库与固定演示输入
scripts/          安装、启动、测试、迁移/容量/包校验
deploy/           Nginx/systemd配置示例
docs/             契约、API、技术与验收证据
collaboration/    必要分工/流程/任务与四成员进度、统一交接
.artifacts/       忽略的截图、trace、私有样本选择器及实验输出
```

技术栈：React/TypeScript/Vite、Ant Design、React Router、TanStack Query；FastAPI/Pydantic、SQLAlchemy/SQLite FTS5/Alembic；python-pptx/python-docx/pypdf、PDF.js/本地Office阅读器、KaTeX、安全Markdown；pytest/Ruff/Vitest/Playwright。

更新代码前先保留本地未提交修改，再`git fetch origin --prune`、核对差异和`git pull --ff-only origin main`。本地修复是否提交、推送或合并由用户明确安排；不要用强制重置覆盖工作，也不要上传运行数据、个人课件或密钥。第三方依赖许可见锁文件及前端构建生成的Office/公式声明；这些声明不能省略。
