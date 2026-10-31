# Hustudy

2026-10-31 生产部署边界：PPTX、DOCX、PDF的原格式读取与正文解析只使用项目锁定的Python/Node依赖，不需要服务器安装LibreOffice或其他系统转换器。`HUSTUDY_ENV=production`时兼容PDF转换默认关闭；只有明确启用并安装LibreOffice，才提供静态版式/截图兼容路径。

2026-10-31 M1预览路径调整：PPTX/DOCX默认使用原格式阅读器，PDF直接使用原PDF按页阅读，不再在上传解析完成后自动排队Office转PDF。兼容PDF改为阅读页中明确点击“生成兼容 PDF”后才提交，LibreOffice只服务静态版式核对和截图；原格式与正文阅读不受兼容转换失败影响。[验收与使用](docs/test_report.md)

2026-10-28 M4：本地文件录入改为严格Markdown及仅录入Markdown的ZIP；AI保留多格式与发送确认。增加批量真题身份/来源审核、批量知识标签关联确认及M2依据修订校验，缺口矩阵区分历史错误与当前重做状态。无新迁移；使用现有Node/KaTeX校验公式。[本地格式与操作](docs/xtc/strict_markdown_format.md)。

2026-10-27 M3收尾：逐段合并、关系图谱、标准包与课程合并、阅读/可选保存、专注导航与多模型笔记助手已获用户本轮验收确认。剩余边界的隔离自动验证与保留待办见[提交验证](docs/fzk/m3_completion_audit.md)；第9项跨课程/独立账户恢复仍暂缓，不将本轮通过等同全站验收完成。

2026-10-27专注阅读新增“全部笔记”导航，可按课程、目录、标题翻页切换。原智谱页面保留，新增DeepSeek/兼容接口多配置与共享模型选择；笔记AI提供摘要、解释、结构整理、复习问题和自定义处理，确认发送后预览、明确采纳为草稿。无新增依赖/迁移，重启后端及托管worker后刷新前端。[使用与验收课程包](docs/fzk/note_assistant_acceptance.md)。

2026-10-27笔记新增独立阅读模式：列表点“阅读”或编辑区切换“阅读模式”，支持标题目录、字号、专注阅读、公式图片与双链连续阅读。自动保存现在默认关闭，可在编辑区明确开启并按本机账户记住；“立即保存”和Ctrl/Cmd+S保持。阅读不会发起自动保存，草稿和撤销历史保留。无新增依赖或迁移，保存工作后刷新前端即可使用。[操作与验收](docs/fzk/note_reading_acceptance.md)。

2026-10-27新增标准数据包：课程／笔记文件夹ZIP可自选导出、预览后导入；课程包支持新建或合并到已有课程，保留原内容并重映射图片和内部关系。入口在课程总览及知识笔记“标准数据包”。后端启动自动执行0022迁移，无新增依赖；工程外验收样例可用 `scripts/generate_portable_samples.py` 自动生成。[使用、边界与验收](docs/fzk/portable_packages_acceptance.md)。

2026-10-26 M3新增课程笔记关系图谱：在“知识笔记 → 关系图谱”浏览已有双链，按标题/关联状态筛选，聚焦单篇直接关联，再打开笔记继续编辑。图谱只读已保存关系，显示真实数量与截断范围，无新依赖或迁移；后端重载后刷新前端。[操作与验证](docs/fzk/note_graph_acceptance.md)。上一轮逐段合并已获用户复验通过。

2026-10-26 M3笔记冲突处理：新增逐段三方合并，正文、标题、标签和文件夹分别核对；应用前保留原草稿，应用后等待明确保存。支持本地/服务端正文与恢复副本下载，旧副本无共同版本或大篇幅差异超限时保留全文并提示手动处理。无新依赖或迁移，保存当前输入后刷新页面即可使用。[操作、技术说明与验证](docs/fzk/note_merge_acceptance.md)。

> **2026-10-24 M2交接提醒：两个事实标签的上游入口尚未完成。** “教师强调”缺M1阅读标记保存/查询及reader注册；“已确认真题”缺M4真题身份录入。M2已有自动检测、引用相交校验和失效保护，但不能把两标签的网页闭环标为完成。请接手的M1/zhy、M4/xtc补齐，M2配合联合验收。详见[本轮交接与接口清单](docs/gcx/handoff_2026_10_24.md)。用户已确认本轮新增功能及长课件问答测试正常；旧手动标签录入说明已被自动读取方案覆盖，不再适用。

2026-10-24长课件问答：明确选择资料后纳入完整可提取正文（≤400原片段/24万字符），长资料分批检查依据再统一回答，显示覆盖/步骤并可显式续跑；不再只取6段。未选资料仍使用相关片段检索。[实现与验证](docs/gcx/qa_batches_2026_10_24.md)。

2026-10-24 API配置已改为账户独立：问答/报告、题库文字识别、AI归类和视觉转写均使用任务所属账户的密钥；无个人Key不回退旧共享配置。升级后重启后端/托管worker并刷新页面，再到API接入保存个人Key，之后保存或清除无需重启。[迁移、测试与边界](docs/gcx/account_api_2026_10_24.md)。

2026-10-24更正：报告设置中的可选区只保留补充笔记。教师强调改为自动读取阅读片段标记，真题改为自动读取已确认身份与关联；目前无上游记录时保持AI建议，不要求在报告页手动填写。阅读标记入口本轮未开发。[当前实现与测试](docs/gcx/supplements_labels_2026_10_24.md)。

2026-10-24 M2补充来源：问答/报告支持主动选择并确认个人笔记；报告支持本人记录的“教师强调”以及显式选择真题后、经已确认知识点映射核对的“已确认真题”。模型仍只生成AI建议，事实来源由服务端判断，缺依据不升级标签。笔记和依据变化会使旧预览失效。无需迁移或安装依赖，重启后端/托管worker并刷新前端。[使用与测试](docs/gcx/supplements_labels_2026_10_24.md)。

2026-10-24 M2第二轮：问答/报告可在发送前选择最多2次格式修复（默认关闭）；生成、修复及跨批调度共用120秒确认窗口，预算耗尽保留已完成部分，仅明确确认才续跑新窗口。调用与修复计数可见，不修复无效引用/限流/超时，不恢复AI出题。重启后端以加载托管worker，前端刷新。[功能与测试](docs/gcx/execution_budget_2026_10_24.md)。

Hustudy 是面向大学生的本地优先学习网站，以课程为中心连接资料、AI理解、知识笔记、题库练习和错题复习。前端采用 React / TypeScript / Vite，后端采用 FastAPI、SQLite / Alembic 与本地文件存储。

更新日期：**2026-10-31**。当前已实现并自动验证多条学习闭环；正式40项课程任务、成员接收、真人试用与实机验收按各自记录核对。四方面最终验收准备见[报告](docs/final_acceptance_2026_10_30.md)。

**使用入口：**[完整使用手册 user.md](user.md) · [四方面验收报告](docs/final_acceptance_2026_10_30.md) · [121项人工验收清单](docs/zhy/materialhub/captain_acceptance_2026_10_23.md#manual-checklist) · [安装指南](docs/setup_guide.md) · [GitHub提交指令](#github提交与推送)

## 学习闭环

```text
注册/登录 → 创建课程 → 上传资料 → 阅读与核对原文
→ 当前PPT知识点总结 / 课程问答 → 整理带引用的笔记
→ 上传题库 → 校正并核验 → 随机练习 → 保存/提交/自评
→ 错题回源 → 补充笔记 → 安排复习 → 重做与再次核对
→ 导出学习成果 / 完整账户备份
```

阅读、笔记与本地题库练习可以独立使用。真实AI须先配置后端模型连接，每次发送前预览并确认；未配置模型也可以完成手册中的本地学习示例。

## 当前功能

| 范围 | 已实现的主要能力 |
| --- | --- |
| 共享基础层 | 注册/JWT登录、课程分类与标签、课程归属隔离、带来源的路由与离开保护、401原账户恢复、共享学习记录、完整账户备份与空账户恢复 |
| M1 MaterialHub资料库 | PPTX/PDF/DOCX/Markdown上传、批量分类/标签整理、固定版本、解析/索引独立任务、兼容PDF按需任务、资料检查、中文关键词检索、原格式阅读、文本分页、书签、版本文本对照、人工补录、图片管理和资料包 |
| 当前PPT阅读助手 | 固定当前版本、全面总结/复习提纲/笔记写作、可编辑学习目标、发送覆盖与分批确认、按知识点组织总结、真实引用页码导航、单知识点摘记与可编辑笔记草稿 |
| M2 AI Study | 课程原文检索、资料问答、多资料学习报告、逐次确认、引用核验、历史与符合条件的成功结果复用；API接入页配置当前登录账户专用连接 |
| M3 NoteGraph | Markdown编辑/安全预览/阅读模式、手动及可选自动保存与冲突保护、目录/标签/批量整理、UUID双链与原文引用、图片和公式工具、文字/音频识别后核对插入、本机草稿恢复、选择导出和回收站 |
| M4 ExamPilot | 严格Markdown/Markdown ZIP导入、PDF/OCR/图片确认后AI转写、人工校正与核验、分级知识标签、统计快照与蓝图、选择题/解答题随机练习、选项打乱与答案映射、作答恢复、自评、错题重做与日期计划 |
| 学习工作台 | 课程真实摘要、继续原对象、知识点学习中心、课程复习日程、资料/笔记查找，以及手册、反馈和备份入口 |
| 全站外观 | 统一主色、六预设/自定色、云白/暖纸/柔雾基调、浅深导航、密度/宽度选择；中文支持黑体/宋体/楷体，英文优先Times New Roman，字号可在12–18px范围连续调节；卡片阴影/轻浮动、电脑/平板/手机布局 |

资料单文件上限为 **30MiB（31,457,280字节）**，资料批量最多20份、总计100MiB。其他图片、识别、导入与备份预算分别见[user.md](user.md)，不要把资料上限套用到所有工具。

当前新增题型仅选择题和解答题；练习使用已经核验的本地题库。AI自动出新题、笔记AI整理及识别后直接新建笔记已停用，历史记录与兼容读取按原契约保留。

## 最近完善与体验入口

| 更新 | 如何体验 | 实现与验证 |
| --- | --- | --- |
| 原文关联笔记检索 | 资料阅读下方“引用这份原文的笔记”，或“阅读笔记 → 关联笔记”：按标题/原文片段检索，每页6篇，同笔记聚合引用条数，选中后读取正文 | [关联笔记验收](docs/zhy/materialhub/reference_notes_acceptance.md) |
| 当前课程复习日程 | 课程总览展开日程，查看到期/逾期/今天/未来/完成/全部待办；搜索、分页后回原错题回顾 | [复习日程验收](docs/zhy/integration/course_agenda_acceptance.md) |
| 站内完整手册与示例 | 使用指南按章阅读、搜索或下载手册，下载配套自制资料/题库，按第3章完成实际闭环 | [手册验收](docs/zhy/integration/user_manual_acceptance.md) |
| 当前PPT专用总结 | 阅读页打开AI阅读助手，核对固定版本与发送范围；生成后按知识点/真实页码导航并整理笔记 | [专用助手](docs/zhy/materialhub/ppt_companion_acceptance.md)、[知识点导航](docs/zhy/materialhub/reading_navigator_acceptance.md) |
| 长课件与草稿连续性 | 原格式单页、文本按组阅读；原文/笔记/复习分区，切换预览保留编辑区，跨页仍受离开保护 | [长资料排版](docs/zhy/materialhub/learning_layout_acceptance.md)、[关联笔记排版修正](docs/zhy/materialhub/reference_notes_acceptance.md) |

本轮关联笔记卡片采用统一主题、引用徽标、更新时间、轻阴影与宽窄布局。无引用时收拢空态；80页自制PPT复验的阅读区由1582px降至1309px，保留原高度门槛。后端引用列表改为必要元数据投影，严格核对有效引用，避免读取列表用不到的笔记正文。数据示例指标不代表全部课件或真实设备。

## 快速开始

macOS/Linux可用项目脚本初始化；Windows步骤见[环境指南](docs/setup_guide.md)。脚本支持Python 3.11/3.12，推荐3.12；前端PDF.js要求Node满足 `>=22.13.0 || >=24`，依赖使用锁文件安装。

```bash
# 在仓库根目录初始化；已有有效配置会保留
bash scripts/setup.sh

# 仅新建环境时需要指定Python
# PYTHON_BIN=python3.12 bash scripts/setup.sh
```

分别在两个终端启动：

```bash
# 终端一：API，开发模式默认自动管理资料worker
bash scripts/dev.sh
```

```bash
# 终端二：前端
npm run dev --prefix frontend
```

- 网站：`http://localhost:5173/`
- 后端健康检查：`http://127.0.0.1:8000/health`
- OpenAPI文档：`http://127.0.0.1:8000/docs`

API启动会执行已有迁移，当前迁移头为 `0021_bank_library`；本轮关联笔记与复习日程没有新增迁移或依赖。更新前先保存草稿；开发API可自动重载，未启用重载的服务需重启后端，单独运行的worker也需加载新代码。

开发API默认托管worker并在异常退出后退避重启。只有明确关闭托管（`HUSTUDY_WORKER_AUTOSTART=false`）或采用外部进程管理时，才另行启动：

```bash
bash scripts/worker.sh
```

PPTX/DOCX/PDF可直接按原格式阅读或按原页查看；解析、索引与兼容PDF独立反馈。生产环境默认不启用兼容PDF转换，因此不需要LibreOffice。正常连接安静显示，异常可检查重试。[处理服务与部署示例](docs/zhy/shared_platform/worker_deployment.md)说明生产守护方式；模板准备不等于已经上线。

首次体验可下载[传输层资料](fixtures/learning_loop_material.md)和[配套题库](fixtures/learning_loop_questions.md)，按手册第3章操作；[操作系统演示资料](fixtures/materialhub_demo.md)另用于固定报告演示，不冒充对任意课件的真实理解。

### 外观与字体设置

登录后点击右上角「外观」，设置仅保存在当前浏览器并立即应用，不写入课程、笔记、资料或账户备份：

1. **主题色调**：选择远山蓝等六种预设，或输入六位十六进制自定色；按钮、导航、卡片和焦点会同步换色。
2. **字体风格**：选择黑体、宋体或楷体。普通中文界面和笔记文本随选择变化；英文文本始终以 Times New Roman 为首选，系统缺字时使用同类本地后备字体。
3. **字体大小**：拖动 12–18px 滑杆，网站普通界面、标题、按钮和说明文字同步调整；PPT/PDF/Office 原件、代码、公式和资料阅读器字号保持独立。
4. **页面基调与导航**：默认方案为“远山蓝 + 云白 + 深色导航 + 舒适留白 + 舒展布局”，也可切换暖纸/柔雾、浅色导航、紧凑排列或聚焦布局。

首次使用建议按「课程总览 → 选择课程 → 资料阅读 → 知识点学习 → 知识笔记 → 题库练习 → 错题复习」体验完整闭环；右上角的「学习记录」可回到同一课程下的资料、笔记、AI结果、练习和错题对象。

## 验证与当前范围

最近一次业务验证来自2026-10-24的[关联笔记验收记录](docs/zhy/materialhub/reference_notes_acceptance.md)：

| 检查 | 已执行结果 |
| --- | --- |
| 后端全量 | 478项通过、2项私有样例跳过，保留5项既有弃用警告 |
| 前端单元测试 | 187项通过，31个文件 |
| Chrome/WebKit | 84个不同场景经修正复验通过；首轮82通过/2空态高度失败，修正后52项专项全部通过，重复不累加 |
| 共享检查 | Ruff、临时迁移升级/模型漂移、TypeScript、生产构建、Markdown安全渲染与PDF实际渲染通过 |

业务测试使用临时数据库、隔离账号、自制资料和固定演示/替身，不写日常test账号数据，不调用真实模型。本次README整理只检查文档链接与格式，未重跑上述业务测试。

```bash
# 后端、单元、类型/构建、迁移与渲染等共享检查
bash scripts/check.sh

# Chrome使用已安装的本机channel，WebKit使用准备好的测试浏览器
HUSTUDY_E2E_CHROME_CHANNEL=chrome npm run test:e2e --prefix frontend -- \
  reference-notes.spec.ts continuity-workspace.spec.ts note-citations.spec.ts \
  reading-layout.spec.ts reader-ai.spec.ts user-manual.spec.ts \
  learning-loop.spec.ts responsive-layout.spec.ts
```

浏览器测试使用8056/5178端口与临时数据。运行前按[环境指南](docs/setup_guide.md)准备对应浏览器。真实AI教学质量、复杂私人课件、Safari/iPhone/Windows实机、长期容量和正式40任务/成员签收另行验收，自动测试不代替这些结果。

## 协作与文档

| 成员 | 主要职责 |
| --- | --- |
| zhy | 队长，共享基础层、M1 MaterialHub与最终集成 |
| gcx | M2 AI Study |
| fzk | M3 NoteGraph |
| xtc | M4 ExamPilot |

职责以[roles.md](collaboration/roles.md)为准。跨模块变化先记契约与交接，各域保留自己的业务事实；源码实现、自动验证与本人接收分别记录。

- 产品思想与40项任务：[main_idea.md](main_idea.md)。
- 完整现行操作：[user.md](user.md)；历史增量：[docs/user_guide.md](docs/user_guide.md)。
- 队长人工体验：[121项清单](docs/zhy/materialhub/captain_acceptance_2026_10_23.md#manual-checklist)。
- API与领域契约：[docs/api.md](docs/api.md)、[docs/contracts.md](docs/contracts.md)。
- 进度与交接：[docs/progress.md](docs/progress.md)、[collaboration/handoff.md](collaboration/handoff.md)。
- 队长状态与完成度：[任务状态](collaboration/zhy/task_status.md)、[完成度核查](docs/zhy/completion_audit.md)。
- 各模块与环境文档：[docs/README.md](docs/README.md)、[collaboration/README.md](collaboration/README.md)。
- 第三方依赖与许可：[docs/third_party.md](docs/third_party.md)。

## 账号、数据与部署

GitHub同步源码，不同步本机SQLite账号、资料、笔记或密码。另一台电脑运行自己的localhost会使用独立数据；跨电脑共用须连接同一后端与持久存储，见[云端账号说明](docs/zhy/shared_platform/cloud_accounts.md)。当前继续本地使用，云部署暂缓。

真实密钥保留在后端环境或加密配置中；`.env`、运行数据和在线备份不进入源码提交。完整账户ZIP用于符合条件的空账户恢复，资料包/笔记ZIP用于导出阅读，不能互相替代。旧二进制PPT/DOC应先另存为PPTX/DOCX；复杂动画、特殊版式与识别结果需人工核对。

## GitHub提交与推送

本机已是Git仓库，工作分支为 `feature/platform-materialhub`，主分支为 `main`，`origin` 对应 `HAOYI0727/Hustudy`。本机已通过仓库级地址映射使用现有HTTPS认证，未修改全局Git配置。按本项目当前约定：**先提交并推送功能分支，再将它合并到main并推送main**。

在功能分支提交当前累计源码、测试和文档：

```bash
cd "/Users/zhy/Desktop/hustudy"

git switch feature/platform-materialhub
git status --short

git add -- .gitignore .env.example AGENTS.md README.md user.md main_idea.md \
  backend/ frontend/ docs/ collaboration/ fixtures/ scripts/ deploy/ \
  hustudy/Hustudy_requirements.md

git diff --cached --stat
git diff --cached
git diff --cached --check

git commit -m "feat(platform): 完善学习闭环、资料阅读与笔记检索并同步文档"
git push -u origin feature/platform-materialhub
```

确认功能分支推送成功后，更新并合并main：

```bash
git switch main
git pull --ff-only origin main
git merge --no-ff feature/platform-materialhub -m "merge: integrate MaterialHub learning loop improvements"
git push origin main
```

如仓库要求PR或受保护分支检查，在GitHub从 `feature/platform-materialhub` 向 `main` 发起Pull Request并按仓库规则合并。推送需要可用的GitHub认证（SSH或HTTPS）与仓库写权限；遇到认证错误应先恢复认证，不使用强制推送覆盖远端历史。

下一轮在功能分支继续开发、提交和推送，再更新main合并。若只打算提交README，暂存命令改为 `git add -- README.md`，提交前仍核对 `git diff --cached` 的全部内容。

`.gitignore`已排除本机环境、数据库、运行文件、`local_only`、依赖与构建产物和临时浏览器截图；已有受控文件仍以暂存区实际列表为准。保留公开的环境示例和自制fixtures，勿把本机配置、用户备份或临时测试材料另外加入。

## 历史说明

下面保留整理前的README内容，便于追溯各成员和日期的记录。旧模型、停用入口、测试数量及“尚未提交/没有Git历史”等旧结论只代表当时状态，现行功能与提交方法以上文为准。

<details>
<summary>展开历史README（含原有分阶段记录）</summary>

2026-10-24 原文关联笔记增强：资料底部和阅读笔记侧栏共用按笔记聚合的检索，标题/片段查找、每页6篇、引用条数与摘录，正文按需预览。无引用时简短提示，已有笔记保持检索；切换预览保留编辑区，原笔记编辑后可回原版本。[使用与实际验收](docs/zhy/materialhub/reference_notes_acceptance.md)，[121项人工清单](docs/zhy/materialhub/captain_acceptance_2026_10_23.md#manual-checklist)。

2026-10-24 新增“当前课程复习日程”：总览按需查看到期/逾期/今天/未来/完成与全部待办，标题查找、真实分页和原错题回顾；主题日期卡片、手机两列、有界列表。后端复用计划接口做课程归属、时区及SQL聚合，不自动重做或改掌握。[使用与验收](docs/zhy/integration/course_agenda_acceptance.md)，[121项人工清单](docs/zhy/materialhub/captain_acceptance_2026_10_23.md#manual-checklist)。

现行完整使用说明见 **[user.md](user.md)**：24章覆盖建课、资料/PPT总结、笔记、题库练习、错题复习和备份，含可下载的传输层资料/题库闭环实例。网站“使用指南”可按章阅读、查找和下载同一份手册；示例下载不会自动导入。

2026-10-23 课件总结增加知识点导航：关键词搜索、每页8项、跟随当前阅读页反查有效引用、直达讲解与逐点切换，保留总结和笔记草稿。[体验与核验](docs/zhy/materialhub/reading_navigator_acceptance.md)，[121项人工Checklist](docs/zhy/materialhub/captain_acceptance_2026_10_23.md#manual-checklist)。

2026-10-23 阅读助手已按当前课件重新收拢：固定单版本、全面梳理/复习提纲/笔记写作、可编辑提示词，新增知识点与真实PPT引用页码导览、单知识点摘记和自定义笔记标题。独立AI学习工作区保持课程范围能力，底层服务复用；云部署暂缓。[体验与验证](docs/zhy/materialhub/ppt_companion_acceptance.md)，[121项人工Checklist](docs/zhy/materialhub/captain_acceptance_2026_10_23.md#manual-checklist)。

2026-10-23 跨电脑账号说明与部署适配：GitHub同步代码不含本机账号/资料库；正式构建默认访问网站同源`/api/v1`，开发默认保持本机，可显式连接公共后端。真正共用账号须部署同一后端与持久数据库/文件存储；[现有test迁移、配置与逐项验收](docs/zhy/shared_platform/cloud_accounts.md)。本轮未实际上线或上传日常数据。

2026-10-23 资料阅读新增「AI阅读助手」：原页预览确认、展示知识点总结与原文依据、标签审阅后保存笔记；两个阅读侧栏保留草稿，未知保存沿原请求重试。资料单文件上限现为30MiB，正常连接提示移除。[使用与验证](docs/zhy/materialhub/reader_ai_acceptance.md)，[121项人工Checklist](docs/zhy/materialhub/captain_acceptance_2026_10_23.md#manual-checklist)。


2026-10-23 按现有长PPT继续优化资料阅读/知识点学习排版：PPT默认单页原格式，文本分页、有界滚动和整版本查找；知识点原文/笔记/复习分区、手机目录收拢，图片工具按需展开。日常原件只读导入隔离账户，同145页样例高度从约7.46万px降至2137px。[实际指标与操作](docs/zhy/materialhub/learning_layout_acceptance.md)。

2026-10-23 队长模块新增「资料检查」：按当前课程每份资料最新版本核对可用正文、解析/索引/兼容预览及处理中状态，支持名称/类型筛选、真实分页和原任务恢复。首页提醒改用当前问题份数，旧失败记录继续保留。[7步体验与验收](docs/zhy/materialhub/readiness_acceptance.md)。

2026-10-23 原文关联继续补齐复习：资料「学习关联→相关错题」可查看原错题的掌握状态、待办/到期数量和最早日期；「错题与复习」先回看与安排日期，明确点击重做才开始。固定来源、原作答和计划分别保持。[功能与7步体验](docs/zhy/materialhub/source_reviews_acceptance.md)。

2026-10-23 新增资料「学习关联」：从当前版本或某段原文找回具有有效引用的笔记、问答、报告和知识点，真实分页/标题查找并回原对象；知识点一键带入练习设置，仍显式抽题。兼顾历史版本、撤权、首次离线和未保存草稿。[自制样例与7步闭环验收](docs/zhy/materialhub/source_connections_acceptance.md)。

2026-10-23 队长模块继续完善：M1支持跨页勾选后导出固定资料版本与来源图片；提交结果不明确时保留原请求，显式核对不扩大范围。处理记录支持类型/状态组合筛选和历史版本回跳，资料/任务独立加载。[完整功能体验与验收清单](docs/zhy/materialhub/captain_acceptance_2026_10_23.md)包含自制样例、10步主流程与共享层/M1矩阵。

2026-10-23 学习卡片增加当前课程真实记录快捷入口，直达原资料版本/笔记/结果/未完成作答；资料卡片新增折角封面、当前打开标记、解析/索引/预览独立状态及详细/精简显示，保留统一主色和当前阅读/勾选/整理输入。[设计与验证](docs/zhy/integration/action_cards_acceptance.md)。

2026-10-23 全站现在采用当前主题的一套主色，以深浅、留白和边线分层，图标与标题区分模块；覆盖此前五模块固定配色。外观切换同步到所有分界面、卡片、导航与学习记录。[设计与验证](docs/zhy/integration/unified_tone_acceptance.md)。

2026-10-23 全分界面继续统一：阅读、笔记管理/编辑、AI设置/报告、题库三模式、错题计划、搜索、备份、API、指南和反馈均细化内部工具/卡片；英文Times New Roman、中文宋黑楷按用途搭配。新增真实后端分页「学习记录」，各工作区顶部与首页共用同一入口，回原版本/笔记/结果/作答并保护草稿。[本轮实现与验证](docs/zhy/integration/all_workspaces_acceptance.md)。

2026-10-23 历史08配色（已由统一主色12替代）：资料蓝、AI紫、笔记青绿、题库琥珀、复习莓粉贯穿首页彩色卡片、实色入口、模块标题、导航与工具栏；个人主题继续控制主动作/焦点，正文保持舒适可读。[设计与验证](docs/zhy/integration/color_studio_acceptance.md)。

2026-10-23 控件与卡片细化：全站主次/图标/文字按钮、桌面主题下拉与工具折叠栏统一；标题适度收敛，卡片柔和阴影与轻微悬浮，手机保留原生选择与触控空间。[实现及验证](docs/zhy/integration/controls_acceptance.md)。

2026-10-22 全站外观升级：右上角「外观」可选择六预设/自定色、云白/暖纸/柔雾底色、浅深导航、舒适/紧凑和聚焦/舒展布局；四模块共享色彩/控件/层级。偏好仅此浏览器，切换保留当前编辑。[研究依据](docs/zhy/integration/appearance_research.md)与[实现/验证](docs/zhy/integration/appearance_acceptance.md)。

2026-10-22 阅读工具增量：原文片段支持本机书签、重命名/搜索/历史回跳；同资料两个解析成功版本可分页对照提取文本并分别回原文。书签按账户UUID/课程隔离，仅当前浏览器；对照不推断图片/排版或语义变化。[使用与验证](docs/zhy/materialhub/reading_tools_acceptance.md)。

2026-10-22 新增「知识点学习」：在同一知识点查看已确认原文、同源笔记/标签候选、题目与待复盘错题，并带入标签设置练习；资料库支持保存/应用/改名/删除本机常用筛选视图。[功能与验证](docs/zhy/integration/learning_hub_acceptance.md)，[官方设计研究](docs/zhy/integration/learning_hub_research.md)。无新依赖或迁移。

2026-10-22 学习连续性：新增阅读侧边笔记（原文引用/关联预览/完整编辑器）、账户/课程隔离的本机草稿恢复，笔记与考点目录改用元数据索引及按需正文，AI资料范围支持分页检索并保留选择。无新增依赖或迁移，保留原有未提交工作。[功能、使用与实际验证](docs/zhy/integration/continuity_acceptance.md)。

2026-10-22 M1连续完善：资料库新增跨页选择最多100份、原子批量分类与标签整理；单份整理增加冲突核对，资料/任务/笔记候选独立重试，引用目标按标题分页。公共弹窗样式复用。无新迁移/依赖，保存草稿后刷新；非reload后端需重启。[使用与验证](docs/zhy/materialhub/organize_acceptance.md)。

2026-10-22 学习闭环整合：课程总览提供四模块真实摘要/待办和最近学习入口；新增阅读继续、摘录带引用笔记、报告笔记直达、指定作答恢复、错题回源及未来复习计划；统一全站视觉。无新依赖/迁移，保存草稿后刷新即可体验。实现、验证与边界见[本轮闭环验收](docs/zhy/integration/learning_loop_acceptance.md)。下方旧日期记录保留，当前规则以最新记录为准。

2026-10-22 队长整合：资料库新增多选/拖放批量导入、逐项结果与显式重试；原文可直接进入当前版本问答/学习报告或就某片段提问。刷新前请先保存笔记草稿；本轮无后端/依赖/迁移更新。项目思想、四模块现状、40任务核对与后续优先级见[当前项目核查](docs/zhy/integration/project_review_2026_10_22.md)，使用与实际验证见[本轮验收](docs/zhy/integration/material_study_acceptance.md)。下方按日期保留历史记录；当前仅选择题/解答题，旧AI候选与填空说明不作为当前操作要求。

当前源码提交说明与验证限制见[2026-10-22版本记录](docs/m4/release_2026_10_22.md)。

2026-10-22 当前题型更新：填空题已取消，题库中的空位题统一作为解答题，保留原题干与参考解答，提交后可自评；选择题仍按原规则判分。旧库首次启动在线备份后自动转换，旧试卷/作答成绩保留。详见[使用说明](docs/user_guide.md)。

2026-10-20 M4：PDF上传后自动解析/拆题并展开、跳转题目区；分组重编号和无标签解答已用用户实际样本验证17题。新增ZIP逐条导入；图片需选择OCR。GLM-4.7-Flash结构化识别已接入发送确认，本机缺API Key，尚未真实调用。[验收与使用](docs/m4/pdf_zip_ai_acceptance.md)。

2026-10-20 M4：新增可选本地图片识别、批量阅读顺序/双栏切分、题目与答案/解析判别、原图核对和插图拖框裁剪；审核可直接勾选、批量标签/删除和统一确认。OCR已安装于本机项目.venv，重启后端/worker后刷新前端；其他机器可安装backend/requirements-bank-ocr.lock。实际样例、测试与限制见[图片题库验收](docs/m4/import_images_acceptance.md)。

## 用户题库练习（2026-10-22现行规则）

「真题与模拟卷」现提供用户题库上传/规则识别/校正确认和随机练习。上传PPTX/PDF/DOCX/Markdown，或粘贴带题号、A–D选项、答案、知识标签的正文；也可选已解析资料及已确认人工补录。识别不确定或无答案先保留草稿，不猜答案。四选项随机重排并同步标准答案；解答题保留参考解答，只检查提交，交卷后可自行核对与自评。

「历史统计与蓝图」提供已确认样本统计、标签改名/合并、资料缺口候选、可重算快照与题型/标签配额；题库可拆分合并题目、人工设置重复卷，复习任务支持改期。

AI学习仅保留资料原文检索、资料问答和学习报告；「练习题生成」整个入口与嵌入式练习已移除。练习统一在「真题与模拟卷→随机练习与作答」，本地抽题不要求模型密钥。首次体验可上传自制 [题库示例](fixtures/question_bank_demo.md)，核对题型与参考解答、确认题库，再选择「计算机网络」标签抽题。旧AI候选只保留历史读取，新生成入口返回410。迁移0019–0020在后端启动时执行，已有数据库会先自动备份；更新后需重启后端与worker。实施范围/真实结果/限制见 [M4验收](docs/m4/question_bank_acceptance.md)。

2026-10-19 M3提交说明：笔记/目录/批量整理、图片与选择导出、回收站、公式编辑和识别文本插入已完成；用户验收第1–8项通过，第9项跨课程/独立完整恢复暂缓。M3 AI整理与API启用已停用。当前使用、验收和更新说明统一见[fzk文档](docs/fzk/README.md)。以下按日期保留其他模块与功能切片记录，当前M3状态以该文档为准。

2026-10-18 M3回收站：中央列表支持批量删除，顶部“回收站”支持批量恢复/彻底删除、账户全部课程清空和保留天数设置（默认30天，可关闭）。本轮新增0016迁移，需要保存草稿后重启后端及worker，再刷新前端；无需重装依赖。[操作、启动命令与复验](docs/fzk/note_trash_acceptance.md)。上一轮工作区复验用户已全部通过，本轮回收站待本人复验；仍未提交/推送。

2026-10-18 M3笔记工作区：侧栏只保留文件夹与标题导航；中央列表集中勾选、批量整理与导出已选，管理/编辑切换保留草稿。导入、标签管理、分类推荐、图片与引用等按需弹窗；支持拖动笔记改变目录、拖动文件夹改变父目录，保留按钮移动。无新迁移/依赖，已运行0015的环境保存草稿后刷新前端即可。[使用与验收](docs/fzk/note_workspace_acceptance.md)。本地未提交，待本轮本人复验。

2026-10-17 M2-TOPICS-REUSE：新生成练习题逐题选择/校验本次所选知识点子集并显示名称；三种真实AI预览可显式复用同用户/课程/请求/来源/模型/当前提示词下的完整成功结果，无新任务或模型调用。保留确认后重新生成；变更或失效则拒绝复用，无依赖/迁移。[使用、验证与重启](docs/gcx/topics_reuse_2026_10_17.md)。

2026-10-17 M2报告容量修复：解除步骤8项/知识点依据3条等过小上限，改为学习步骤64项、知识点32项、每处依据64条等有界容量，完整保留内容并逐条核验，不靠截断掩盖假引用。报告v6，只改报告；重启worker后复测。[详情](docs/gcx/report_capacity_2026_10_17.md)。

2026-10-17 M2报告自测补救：模型漏自测依据时舍弃无引用原题，保留有依据题目，并基于已校验知识点/例题补足基础自测，页面和笔记明确标注；不猜引用、不增加模型调用。报告v5，重启worker、刷新页面。[说明](docs/gcx/selfcheck_completion_2026_10_17.md)。

2026-10-17 M2真实课件修复：学习报告纳入完整可提取正文（最多400段/24万字符），分批预览确认、持久进度与失败后显式续跑；候选最多128段/32000字符，报告/候选采用原文编号引用，编程选项保留运算符。AI宽屏双栏独立滚动，窄屏快捷跳转。需重启后端和worker、刷新网页，无新依赖/迁移。[使用与验收](docs/gcx/real_materials_2026_10_17.md)。

2026-10-17 M2学习报告：附加概念链接无效时移除并显示提示，不再丢弃整篇报告；必填结构与原文引用仍严格检查。结构错误显示“输出格式不符”，报告提示词v3，需重启worker、刷新页面。[说明](docs/gcx/report_structure_2026_10_17.md)。

2026-10-17 M2资料问答引用修复：由程序提供原文摘录编号，AI选择编号，程序取回原文，减少抄写差异导致的失败；原有引用、权限与确认校验保留。需重启worker，后端--reload自动加载，前端刷新即可。[说明](docs/gcx/qa_excerpts_2026_10_17.md)。

2026-10-17 M2引用反馈修复：AI返回内容但证据未通过原文检查时，显示“引用校验失败”；错误提示区分片段ID与摘录，练习提示词v3加强复制原文要求。保留严格校验、确认发送与失败不自动重试。重启worker，后端--reload自动加载，浏览器强制刷新；[详情](docs/gcx/citation_feedback_2026_10_17.md)。

## 2026-10-16 M2候选与基础完善（gcx）

AI学习新增「题目候选 · 待审阅」：单选/判断/简答，指定结构/同考点变式/自选弱项；预览设置与材料后确认生成，可查看答案/评分细则、来源和历史，导出作者审阅用JSON。报告和候选都有受自制样例约束的固定演示；问答/报告/候选可精确选择片段，课程问答有持久历史，模型错误区分余额、并发、频率等安全代码。

不再按轮换日期刻意分段，详见[当前M2状态与依赖](docs/gcx/m2_plan.md)、[验收](docs/gcx/candidate_acceptance.md)、[公开候选schema](docs/gcx/question_draft_schema.json)。无新迁移/依赖/环境，重启后端和worker即可加载。M4仍需映射正式蓝图章节并集成试卷，教师/真题事实标签和真人质量验收不冒称完成。手动上传见[累计清单](docs/gcx/changed_files_2026_10_16.md)。


## 2026-10-16 M2真实教学报告（gcx）

AI学习新增「章节学习报告 · 需确认」：选择资料/学习方式 → 来源预览与覆盖提示 → 明确确认 → 后台报告 → 目标/知识点/例题/自测/引用 → 可编辑笔记草稿，报告自动保存并提供最近20条历史。请重启后端和worker加载新代码；不需要新增迁移或安装依赖。Windows现有Python启动步骤见[环境指南](docs/setup_guide.md)，使用见[用户指南](docs/user_guide.md)。

成员现为gcx=M2、xtc=M4（含轮换时段互换），使用GitHub网页手动上传；旧分支/姓名描述按历史保留。模块关联回归45项、Vitest14项和Chrome2项通过；全量初次129通过/3项既有Windows权限相关失败，详情见[验收](docs/gcx/study_report_acceptance.md)。真实模型报告学科质量、WebKit/实机与M4候选仍待后续，不标全部M2/P0完成。


Hustudy 是面向大学生的本地优先课程学习工具，围绕“资料阅读 → 知识点讲解 → 笔记与引用 → 真题分析 → 模拟练习 → 错题复习”形成学习闭环。首版采用 React/Vite 前端、FastAPI 后端、SQLite 与本地文件存储，按共享基础层加四大业务模块协作推进。

## 当前版本

更新：2026-10-16。当前具备可演示的学习闭环；共享基础层 + M1 核心实现已通过自动验收，A01–A08 为 Review，A09/A10 正式集成交付为 Doing。其他模块仍有 P0 缺口，不代表完整初版或正式发布完成。

当前可运行流程：

```text
注册/登录 → 创建课程 → 上传资料 → 解析切片 → 搜索/阅读
→ Markdown 笔记与 Citation → 演示检索 / 确认发送的 GLM 课程问答
→ 真题导入/拆题 → 蓝图 → DRAFT 模拟卷
→ 审阅为 READY → 作答/评分 → 错题 → 复习任务
```

已完成的主要功能：

| 区域 | 当前能力 | 代码位置 |
|---|---|---|
| 共享基础层 | FastAPI/request_id、标准 JWT、课程整理与删除隔离、SQLite/Alembic 0001–0012、原子文件存储、完整账户备份/空账户恢复 | `backend/app/core`、`backend/app/routers/auth.py`、`courses.py` |
| M1 MaterialHub | 有界上传、hash 去重、不可变版本、独立 worker/租约/取消恢复/重试/幂等索引重建、四格式切片、中文 FTS5、分类/标签整理与版本筛选、原文关联笔记、人工补录确认/修订、图片改名/说明/标签查找与分页、后台课程资料ZIP/来源清单、PPTX/Word原格式与PDF原页阅读、独立兼容PDF、资料/笔记分页检索和删除撤权 | `backend/app/services`、`workers/materials.py`、`routers/documents.py`、`routers/assets.py` |
| M2 AI Study | 演示检索、GLM-4.7-Flash 课程问答、片段预览/逐次确认、结构化响应与引用校验；问答/报告/三模式候选/固定演示/精确片段/历史；真实质量与正式M4集成待验 | `backend/app/routers/ai.py`、`routers/remote_ai.py`、`schemas/remote_ai.py` |
| M3 NoteGraph | Markdown 安全预览、自动保存、revision 冲突、UUID 双链/反链、Citation 回源、图片嵌入/反链与解码校验 | `backend/app/routers/notes.py`、`frontend/src/components/knowledge.tsx` |
| M4 ExamPilot | 基础 Topic、拆题草稿/确认、蓝图、演示 DRAFT 试卷、审阅、作答与客观评分、错题复习；完整映射统计/真实三模式生成待补 | `backend/app/routers/exams.py`、`backend/app/models/exams.py` |
| 前端工作台 | Router/Query/Ant Design 基线、401原账户恢复保留草稿、统一视觉/图标/状态、电脑/iPad/手机布局、抽屉导航和可折叠目录 | `frontend/src/main.tsx`、`frontend/src/styles.css` |

最近验收分别记录，不能将不同日期的数量相加：

| 范围 | 已执行结果 | 证据 |
|---|---|---|
| 后端与共享检查（10-15） | 116项pytest、Ruff、迁移漂移、安全显示、PDF实际渲染通过；独立3.12亦有116项记录 | [测试报告](docs/test_report.md) |
| 前端（10-16） | 14项Vitest、TypeScript/构建、42项Chrome/WebKit完整回归（3.6分钟）通过 | [视觉与多端截图](docs/zhy/shared_platform/visual_polish_acceptance.md) |
| 本机容量/环境（10-15） | 10课程/200资料/1000笔记基线与同机干净源码重建通过；不是其他机器或所有复杂样本的成绩 | [实际范围与JSON](docs/zhy/materialhub/search_capacity_acceptance.md) |

当前状态以[队长任务表](collaboration/zhy/task_status.md)、[完成度核查](docs/zhy/completion_audit.md)为准，逐轮历史见[公共进度](docs/progress.md)。本次仅校正文档，没有重跑以上业务测试。

## 快速开始

推荐在网络可用的终端执行一次初始化：

```bash
# 进入已克隆的仓库根目录
./scripts/setup.sh
```

脚本会创建 `.venv`、按锁文件安装前后端依赖并生成 `.env`。前端 PDF.js 要求 Node >=22.13.0 或 >=24（本机实测 25.2.1），本地渲染检查需保留 npm 默认可选依赖。项目推荐 Python 3.12，本机既有服务使用 Python 3.11.15，独立 Python 3.12.13 锁依赖116项回归已有通过记录；需要指定解释器时执行：

```bash
PYTHON_BIN=python3.12 ./scripts/setup.sh
```

setup会为JWT空值或旧占位自动生成强随机密钥并保留有效配置。密钥仅保存在根目录 `.env` 并由后端读取，不要重复轮换；然后分别在两个终端启动：

```bash
# 终端一：开发API自动管理资料worker（含退出重启）
bash scripts/dev.sh
```

```bash
# 终端二：前端
npm run dev --prefix frontend
```

浏览器访问：

- 前端：`http://localhost:5173/`
- 后端健康检查：`http://127.0.0.1:8000/health`
- OpenAPI：`http://127.0.0.1:8000/docs`

后端依赖按 `backend/requirements.lock` 安装。development下API默认托管资料worker并在其异常退出后退避重启；同数据库/存储的进程锁防止重复启动。PPTX/DOCX本地原格式可直接打开，兼容PDF转换使用独立执行道，不阻塞新资料解析/索引；LibreOffice缺失/失败时原格式与文本仍可用。上传区显示实际处理服务连接状态，原件保存与后续处理分别反馈，不自动重传。若显式关闭托管（`HUSTUDY_WORKER_AUTOSTART=false`），才需另行运行 `bash scripts/worker.sh` 或外部守护。production默认外部管理，参阅[故障原因、自动恢复与Linux部署示例](docs/zhy/shared_platform/worker_deployment.md)；这些示例尚未部署上线。自制样例位于 `fixtures/materialhub_demo.md`。

课程图片可整理名称、说明和标签，并按元数据/标签/来源筛选与分页；改名保留原文件、UUID和来源。并发修改显示409冲突并保留本地输入；查找不识别图中文字。操作见 [docs/user_guide.md](docs/user_guide.md)，最新交接见 [handoff.md](collaboration/handoff.md)。

## 验证命令

```bash
PYTHONPATH=backend .venv/bin/python -m pytest -q
bash scripts/check.sh
npm run check --prefix frontend
npm run build --prefix frontend
# 浏览器测试使用8056/5178与临时数据；先按环境指南准备浏览器
npm run test:e2e --prefix frontend
```

浏览器验收建议依次检查：注册和课程创建、Markdown 上传与切片、正文/标题搜索、笔记双链与反链、Mock AI 引用、真题和蓝图、DRAFT 到 READY、作答提交、错题复习，以及两个账号之间的归属隔离。

## 四模块推进计划

### A：共享基础层 + M1 MaterialHub

负责认证课程、迁移、存储/任务、四格式解析、原格式与兼容阅读、版本/图片/来源、关键词分页检索和共享集成。标准JWT、原子存储、完整账户恢复及核心M1流程已有自动证据；下一步为复杂真实样本/实机矩阵、极限资源、成员评审/签收、集成发布和真实试用，不重复实现已通过的基础功能。

对外稳定提供 `DocumentVersion`、`ChunkRef`、`AssetRef`、`Citation`、`ProcessingJob`。其他模块不能直接读取原始文件或私自修改 M1 表结构。

### B：M2 AI Study

负责Provider/RAG、教学报告、结构化校验与预算。GLM-5.3-Flash课程问答已接入，必须先预览片段并逐次确认发送；问答、报告、结构化题目候选、固定演示、精确片段与持久历史已接入；下一步为M4正式蓝图集成、外部证据契约和人工质量验收。演示检索不代表真实理解，语义检索与费曼仍是P1。

只能消费 M1 已校验的 `Citation`/`ChunkRef`，不能上传文件、修改笔记正文或直接创建正式试卷。

### C：M3 NoteGraph

笔记整理与编辑器更新（2026-10-18）：左侧支持最多6级文件夹，新建、改名、移动和删除空文件夹；选中父目录可查看子目录笔记。批量勾选笔记后可移动、添加/移除标签；“管理当前课程的全部标签”可改名、合并或删除标记。导出保留所选笔记的文件夹层级，未归档笔记放根目录，仍只附带实际引用图片。展开“导入 Markdown”可一次选择最多20份UTF-8文件（每份≤2MiB），统一指定文件夹与标签，标题使用文件名去扩展名，失败可重试且成功项不重复导入。导入MD本身不上传其本地图片附件。

“推荐归类”按文件夹名、已有笔记标题/标签给出可解释的本地候选，由用户勾选确认后移动，不调用外部AI。编辑器支持选区格式、任务列表/表格/代码块、快捷键、撤销重做、分屏预览、大纲、查找和专注编辑。[操作步骤、兼容性与实际验证](docs/fzk/note_organization_acceptance.md)。用户确认上一轮引用管理复验2/3/4成功；本轮新增功能仍待本人复验，继续未提交。

资料引用补充（2026-10-18）：笔记“资料来源”显示资料名称、固定版本和定位，可刷新、失败重试及确认移除误引用；重复添加同一摘录复用原引用，每篇最多50条。移除保留笔记正文和原资料，已包含该引用的ZIP需要重新生成。页面切到后台暂停新的自动保存，回到前台继续计时；401/409仍保留草稿等待处理。[M3当前完成情况、余项与验收](docs/fzk/m3_completion_audit.md)。用户已确认图片上传和笔记导出成功；已审阅笔记供AI/出题使用、团队集成与实机试用仍需后续完成。

最新更新（2026-10-18）：笔记工具栏“上传图片并插入”和图库“选择图片”支持多选PNG/JPG/WebP，每批最多20张、每张10MiB；显示进度与逐文件失败，成功保留，未完成项可显式重试。展开“管理图片”可预览、改名、编辑说明/标签、查看引用位置和确认删除。单篇.md按标题下载；“选择笔记导出”可逐篇勾选，ZIP只包含所选“笔记标题.md”及其引用的images图片，共用图片只保存一份，同名加序号，不带入未选笔记或图库其他图片。完整解压后用Markdown阅读器打开，保持images目录位置即可显示有效图片。无需命令行校验；未选链接目标和已失效图片保留文字说明。[最新行为与验收](docs/fzk/note_batch_images_acceptance.md)。

负责Markdown、自动保存/冲突、双链/反链、Citation和图片。标签、搜索筛选、删除确认/并发保护、断网恢复保存和跨课程双链均保留。网络响应丢失重试不会重复新建，401/409保留草稿等待显式处理。来源摘录以可读文字附在导出的Markdown中；完整账户迁移仍使用“账户备份”。历次实现与验收见[fzk记录](docs/fzk/README.md)。仍未提交、推送或合并，新增修复待本人复验、队长整合。

当前文件夹更新增加0015迁移，无新依赖。停止旧worker，重启API完成迁移后再启动worker、刷新前端，并重新勾选导出；只刷新网页不能更新旧worker的打包行为。启动迁移前系统自动创建SQLite在线备份。此前0013/0014及新增0015仍待zhy团队整合；0015账户备份保留文件夹，继续兼容旧0012/0013/0014，旧笔记默认未归档。新包不改写已经下载的文件；笔记ZIP用于阅读，不用于账户恢复。

使用 M1 提供的有效来源，不自行解析资料，不改变原始版本，也不替用户确认考点或主观题最终得分。

### D：M4 ExamPilot

负责真题导入、拆题校正、Topic 映射、历史统计、蓝图、三种生成模式、审阅、作答、评分、错题与复习。下一步完善父子题/跨页引用、映射状态、统计快照、同考点变式/历史蓝图/薄弱项专项、题干 hash 去重、主观题 rubric、提交幂等和复习日历。

必须遵守 `DRAFT → REVIEWED → READY`，正式试卷需要保存生成时的资料和模型快照。

## 协作与文档入口

团队分工为：**zhy（A）共享基础层 + M1、gcx（B）M2 AI Study、fzk（C）M3 NoteGraph、xtc（D）M4 ExamPilot**。成员与模块映射由 [roles.md](collaboration/roles.md) 统一维护。

```text
collaboration/                    docs/
  README.md                         README.md
  handoff.md       # 实时交接        contracts.md / api.md / decisions.md
  workflow.md / task_board.md        progress.md / traceability.md
  project_handoff.md                 setup_guide.md / third_party.md
  zhy/                              zhy/
  xtc/           # 每人 progress     xtc/          # 每人 features
  fzk/                              fzk/          # 与 optimizations
  gcx/                              gcx/
```

个人进度在 `collaboration/<成员>/progress.md`，实现的功能与优化说明在 `docs/<成员>/features.md`、`optimizations.md`。同级公共文件继续维护统一接口、约束、操作与集成状态；个人说明引用公共契约，不另建一套。已有跨模块历史记录保留，不能将 AI 辅助的集成改动冒记为其他成员本人完成。

每次完成一个修改切片，在提交/PR 前：更新个人记录 → 在 [handoff.md](collaboration/handoff.md) 追加唯一交接 ID、修改范围、真实测试结果、风险与接收人 → 接收人记录复验 → 队长同步公共任务板、进度与追踪。影响下游的未完成接口和阻塞也要及时记录；“待接收”不等于“已验收”。完整规则见 [AGENTS.md 第 20 节](AGENTS.md#20-四人文档隔离与统一交接规则)。

个人入口：[zhy](collaboration/zhy/README.md)、[xtc](collaboration/xtc/README.md)、[fzk](collaboration/fzk/README.md)、[gcx](collaboration/gcx/README.md)。技术文档导航见 [docs/README.md](docs/README.md)。

2026-10-16队长核查：共享基础层 + M1核心自动验收通过，整体仍待正式评审与交付。[当前A01–A10任务表](collaboration/zhy/task_status.md)管理状态和后续依赖，[完成度核查](docs/zhy/completion_audit.md)列技术证据与缺口；[zhy文档](docs/zhy/README.md)按共享基础层、M1、跨模块集成及历史分类。公共契约/操作/全站进度与handoff保留根级，GLM问答记为队长辅助M2集成，不算M1独有功能。历史骨架Done、构建成功及自动测试均不能替代正式交付。

- [`AGENTS.md`](AGENTS.md)：项目开发规范、领域模型、API 契约和四模块边界。
- [`main_idea.md`](main_idea.md)：产品思路与学习闭环。
- [`Hustudy_requirements.md`](Hustudy_requirements.md)：需求基线入口。
- [`Hustudy_team_collaboration.md`](Hustudy_team_collaboration.md)：课程教案、团队协作和过程证据要求。
- [`collaboration/project_handoff.md`](collaboration/project_handoff.md)：合作者复现、验收和后续推进指南。
- [`collaboration/roles.md`](collaboration/roles.md)：A/B/C/D 职责与接口边界。
- [`collaboration/task_board.md`](collaboration/task_board.md)：任务状态和验收证据。
- [`collaboration/workflow.md`](collaboration/workflow.md)：分支、评审、契约变更和测试流程。
- [`collaboration/roadmap.md`](collaboration/roadmap.md)：P0 后续、P1/P2 和创新方向。
- [`docs/api.md`](docs/api.md)：已实现 API 概览。
- [`docs/contracts.md`](docs/contracts.md)：共享实体、引用和状态契约。
- [`docs/progress.md`](docs/progress.md)：真实进度、测试结果和未完成风险。
- [`docs/setup_guide.md`](docs/setup_guide.md)：环境安装与日常操作指南。

## 当前限制

P0仍需完成M2真实质量验收/教师与真题证据、M4正式候选接入、M3本地分支新功能人工验收与迁移/备份集成、M4完整拆题校正/映射统计/证据约束三模式生成，以及跨模块最终集成、实机/真人试用和正式发布。OCR、语义检索、费曼/间隔复习为P1。旧二进制`.ppt/.doc`需先另存为`.pptx/.docx`；直接预览不保证完整Office动画与所有复杂版式。扫描PDF可看原页并人工确认补录，不能声称已有OCR。

真实模型密钥只进后端读取的 `.env`。用户原件、数据库、依赖和构建产物不提交；`fixtures/`和文档证据仅使用自制/获授权资料。完整账户备份与课程资料包用途不同，恢复只到满足UUID/归属约束的空账户。
协作分支建议使用 `feature/m1-material`、`feature/m2-ai`、`feature/m3-note`、`feature/m4-exam` 和 `fix/<issue>`；跨模块字段先更新 `docs/contracts.md`，再修改代码和调用方。

## GitHub同步

当前用户使用GitHub网页手动上传，本地为源码副本，没有Git历史；本轮未上传或发布。先取得团队最新版本，再按[本轮变更清单](docs/gcx/changed_files_2026_10_16.md)上传源码、测试与文档，并注明删除文件和交接ID。早期SSH/分支操作留作历史参考，见[同步说明](collaboration/github_sync.md)。GitHub源代码同步不等于网站部署，课程要求的Gitee/Wiki证据仍需另行维护。

<details>
<summary>开发历史（旧状态按日期保留，当前结论以上文为准）</summary>

## 2026-10-13 集成更新

前端已按 `features/materials`、`features/ai`、`features/notes`、`features/exams` 拆分，共享 UI 位于 `components/workspace.tsx`。蓝图支持编辑题数/分值/时长；课程切换清空工作区旧状态，过期登录回到登录页。后端统一错误追踪编号，测试使用隔离临时库。本轮 pytest 为 6 passed，前端构建通过；Safari 已验证登录与蓝图动态重算。交接和下一轮优先级见 [集成记录](collaboration/integration_2026_10_13.md)。

2026-10-14 队长缺口分析与依赖顺序见 [M1 分析](docs/zhy/materialhub/materialhub_gap_analysis.md)，本轮交接见 [H-20261014-ZHY-001](collaboration/handoff.md#h-20261014-zhy-001)。

扫描 PDF 可在原页阅读点击“补录本页文字”：保存草稿 → 对照原页 → 核对确认 → 检索/引用。确认不会更改原始解析失败状态；修订与旧引用分开保存，撤回不自动回退。当前仅支持原始 PDF。

## 2026-10-14 最新任务管理验收

资料任务可取消和恢复，关键词索引可按选中版本幂等重建；租约保护防迟到结果覆盖，恢复不清零尝试预算，原文与引用不改。自动检查通过，完整Safari流程/附件备份/压力仍待补。具体判定见[本轮验收报告](docs/zhy/materialhub/acceptance_2026_10_14.md)，交接[004](collaboration/handoff.md#h-20261014-zhy-004)待成员接收。

## 2026-10-14 课程资料包与验收

在资料页展开“课程资料包”，后台生成各版本原件、可用预览、解析文本、确认人工来源、图片和来源清单，保留UUID与hash。源删除/撤回/文件损坏停止旧包下载；不是完整账户备份，当前不能恢复导入。40项自动检查通过；Safari实际3份资料/3版本包下载，374片段/377内容文件与整包hash验证通过。[验收及正式队长A01–A10关口](docs/zhy/materialhub/material_export_acceptance.md)保留完整备份/环境/压力/发布等待办。

## 2026-10-14 共享课程整理

课程总览支持创建时分类/标签、改名/描述/分类/标签整理、关键词与组合筛选/排序、可点标签和revision冲突对照。0009保留旧课程与资料/笔记UUID，改名不再清空未提交描述。43项自动检查通过；Safari创建/改名/刷新/双标签页冲突已验收。课程删除完整关联清理、资料/任务分页与完整恢复仍待补，详见[验收](docs/zhy/shared_platform/course_organization_acceptance.md)与[交接006](collaboration/handoff.md#h-20261014-zhy-006)。

## 最新基本功能验收（2026-10-14）

课程删除已补影响预览/名称确认/revision与同事务跨模块清理，保留其他笔记的失效来源，取消活跃任务，避免孤立笔记/复习与迟到结果。0010追加标记；最终47项测试及共享检查通过，Safari确认保护已观察，用户课程未删除。[公开测试报告](docs/test_report.md)、[基本功能与剩余关口](docs/zhy/shared_platform/basic_acceptance.md)。当前仍不是全部P0验收完成。

## 智谱真实课程问答（2026-10-14）

已接入GLM-4.7-Flash：后端密钥→课程片段预览→逐次确认→后台任务→JSON/原文引用校验→结果回源/笔记草稿。使用.venv/bin/python scripts/configure_zhipu.py隐藏输入配置，重启API与worker。默认演示不发送；真实调用仅发送确认的片段，保留/训练/删除政策细项未核实。

67项回归/共享检查通过，自制真实请求grounded/1引用/417tokens；Safari模式入口观察通过，完整正向浏览器闭环待补。[验收](docs/zhy/integration/zhipu_qa_acceptance.md)、[配置指南](docs/setup_guide.md)。真实章节报告、M4生成与完整P0仍未完成，密钥不提交Git/前端/文档。

2026-10-15共享层升级：标准HS256 JWT已启用，旧会话需重新登录；setup自动初始化后端强签名密钥并保留有效配置。文件/图片原子写入，低磁盘507；资料与全部处理记录可服务端筛选/分页，页外引用正常回源。最新96项回归/共享检查通过，完整恢复、前端基线与环境/性能/发布仍待补。

2026-10-15新增“备份与恢复”：后台生成包含资料/图片/笔记引用/AI/试卷作答/错题复习的完整账户ZIP，校验后恢复到新数据库的空账户，保持业务UUID/hash/关系。保留源对象的同库账户会拒绝UUID冲突，不覆盖数据；迁移0012。当前101项回归与共享检查通过，跨机器/Safari/压力及其余基线仍待验收。


## 2026-10-15 共享前端与当前验收

页面导航已接入React Router，地址记录课程和引用来源，支持刷新/前进后退及未保存确认；TanStack Query统一GET的会话隔离/去重/写入失效，变更不自动重试。登录过期弹出原账户登录框，保留原笔记和资料整理草稿。Ant Design主题沿用公共视觉，工作区按需加载，当前主包485.85KB。

最新共享检查101项后端、10项Vitest、迁移/显示安全/PDF实渲染/类型/构建通过；隔离Chrome/WebKit共8项浏览器闭环通过，包含真实API上传检索与完整备份下载hash。Python3.12.13独立环境101项通过，现有服务解释器未替换。命令和限制见[环境指南](docs/setup_guide.md)、[zhy前端验收](docs/zhy/shared_platform/web_base_acceptance.md)。LibreOffice成功转换、完整业务矩阵、容量/性能、人类评审/Gitee/发布及真实用户反馈仍待完成，不能称全部P0完成。

## 2026-10-15 PDF预览修复

PPTX/DOCX默认原格式阅读；LibreOffice仅用于用户按需发起的兼容PDF，阅读区保留环境检查和原版本重试。Safari因新Map方法缺失而渲染失败的问题已改用同版本PDF.js legacy解决；PPTX保留隐藏页并核对页号，旧错位截图不会被静默重新指向。

最新110项后端、10项Vitest、14项Chrome/WebKit闭环及共享检查通过；独立Python3.12相关17项补验通过。原课件旧缓存已146页/146张一致，当前Safari新标签页会话过期需原账户重新登录后查看。[验收与剩余限制](docs/zhy/materialhub/preview_recovery_acceptance.md)。

### 队长共享层与M1当前验收

知识查找现支持资料/笔记独立服务端分页和原文命中摘要，不再截断前50个结果；PPTX嵌套组合文字/表格提取已补齐。新增双引擎补录/撤回/来源回跳/课程删除闭环，10课程/200文档/1000笔记的本机容量读性能已测，Python3.12干净源码重建通过。具体范围、实际数值和限制见[zhy验收](docs/zhy/materialhub/search_capacity_acceptance.md)。

本地完整自动验收：`HUSTUDY_E2E_CHROME_CHANNEL=chrome bash scripts/accept_captain.sh`（需已准备浏览器，使用隔离临时数据）。功能自动通过不代表Gitee正式合并、成员签收或全站其他模块完成。

### PPT / PDF / Word 按原格式预览

选中资料后，`.pptx` 点“PPT 预览”，`.docx` 点“Word 预览”，`.pdf` 点“PDF 预览”。Office直接在本地浏览器读取原件，支持基础样式/表格/图片、翻页与缩放，PPT另有演示模式；不需等待PDF转换。转换路径另叫“兼容预览（PDF）”，用于静态版式核对和截图；文本引用保持原契约。

开发/构建会自动生成隔离运行时（npm run build:office）；不上传文档给外部服务。首版不支持旧.ppt/.doc或完整Office动画/编辑，复杂排版有差异。最新14Vitest、26项Chrome/WebKit闭环通过，具体说明见[zhy原格式验收](docs/zhy/materialhub/native_preview_acceptance.md)。


全站多屏布局：电脑使用紧凑侧栏；平板/手机使用吸顶导航菜单，手机资料与笔记目录可折叠。统一字号/卡片密度并保留触控热区、输入可读性与文档独立缩放。40项双引擎/14Vitest/类型构建通过，具体范围与实机待验边界见[响应式验收](docs/zhy/shared_platform/responsive_layout_acceptance.md)。


2026-10-16视觉细化：统一主色、文字层级、按钮/选中/禁用/焦点与语义状态，增加工作区/账户标识、功能图标与可见表单标签；保留电脑/iPad/手机布局及触控尺寸。最新42项双引擎、14Vitest、类型与构建通过，截图与实际边界见[视觉验收](docs/zhy/shared_platform/visual_polish_acceptance.md)。

</details>

### M2结构化响应诊断补充（2026-10-16）

候选真实测试反馈：约400字仍出现结构化输出失败，不能归因为资料过长。候选提示词v2增加完整字段示例；JSON语法错误与字段错误分开显示，只展示白名单字段路径和固定原因，不保留或输出模型原文。重启worker后重新预览确认才使用更新，旧失败记录不改写。模拟HTTP回归76 passed/12.34秒；未调用真实模型，原始失败的具体字段仍待新请求验证。

### M2基础完成状态纠正（2026-10-16）

M2基础功能尚未全部实现和验收。报告标签缺少逐项编辑交互，教师/真题标签依据未接入；真实候选修正复验、真实质量及M4正式组卷对接待验/依赖。当前优先补基础缺口，不以长课件增强或界面美化代替基础交付。逐项依据与下一步见docs/gcx/m2_plan.md最新核查。

### M2基础补齐：标签审阅与教学结构（2026-10-16）

新增重点/难点/考点建议逐项增删改及理由审阅，显式转为可编辑笔记，保留原始AI建议/身份与引用；切换模式和保存失败保留草稿。报告新增知识点分层、报告内概念关系、难点突破步骤及复习建议，兼容旧结果，固定报告演示可离线复验。后端87、前端17、Chrome桌面/窄屏4项通过，未调用真实模型。真实质量、教师/真题证据和M4正式组卷仍待验/依赖。[验收与使用](docs/gcx/basic_acceptance.md)。

M2-LABEL-REVIEW-01用户试用反馈（2026-10-16）：用户表示本轮新增功能尝试后没有问题；记录为本轮人工试用反馈，不代表真实AI质量或全部M2通过。详见docs/gcx/basic_acceptance.md。

M2页面入口现为“资料原文检索、资料问答、学习报告”，入口下显示用途；发送确认在预览区域，结果保留审阅提示。此次仅前端显示调整，刷新浏览器即可，不需重启后端或worker。

手动上传准备：按实际本地目录整理了[上传指南](docs/gcx/upload_guide.md)、[M2累计文件清单](docs/gcx/upload_files_m2.txt)和[完整源码清单](docs/gcx/upload_files_full.txt)。这些是路径清单，不是与远端的差异；排除.env、本机运行数据、依赖/构建/缓存。

### 2026-10-17 M2完整剩余范围审计

此前“主要只剩验收”的判断不完整。模型平台切换尚未实现；分批处理、步骤计数、失败续跑、缓存隔离、逐题Topic配额等仍有需求缺口。全部剩余开发、跨模块依赖、真实验收及P1范围见[完整审计](docs/gcx/m2_remaining_audit_2026_10_17.md)。旧成果已由用户报告上传合并并完成本地下载复验，不代表这些新待办已完成。本次只改文档，不需重启服务。

### 当前模型：GLM-5.3-Flash（2026-10-17）

原Hustudy-main已按用户要求切换默认及本机配置为glm-5.3-flash，保留glm-4.7-flash配置兼容。新模型必须开启思考，已适配JSON调用；原密钥保留。需重启后端与worker，前端刷新并重新预览确认。104项后端/4项Chrome模拟验证通过，未调用真实模型，不保证免费/额度/真实生成质量。其他下载副本和GitHub尚未同步。[变化及重启命令](docs/gcx/model_switch_2026_10_17.md)。

## 2026-10-18 M3 图标工具栏与公式编辑器

笔记编辑器改为分组图标，悬停显示中文说明。点击 Σ 或按 Ctrl/Cmd+Shift+M 打开公式编辑器，支持常用模板、数学符号、行内/独立公式和实时预览；将光标放回已有公式中可再次编辑。保存与导出保留标准 Markdown 公式，所有排版在本地完成。用户本轮暂缓 AI 识别后续开发。详见[使用与验收](docs/fzk/note_math_editor_acceptance.md)。

## 2026-10-18 M3 公式工作区扩展

点击笔记编辑器 Σ：按分类或搜索选择公式，点击参数逐项填写和嵌套；“矩阵 / 多行”通过表格生成结构，“语法速查”内置说明及示例。当前357项、16分类，支持中文/命令搜索、窗口撤销与实时预览。上轮手动复验通过，本轮扩展和验证详见[公式工作区](docs/fzk/formula_workspace_acceptance.md)。

## 2026-10-19 M3 图形符号与结构填写

Σ 公式窗口增加紧凑图形按钮：符号分类切换、12种结构快捷输入。点分数后可直接填分子/分母，Tab换字段，符号插入后保留字段光标；已有公式再次打开可恢复明确结构。“移到公式末尾”可继续输入，预览始终在填写区上方。参考AxMath交互独立实现，未增加依赖。详见[使用和复验步骤](docs/fzk/formula_graphic_input_acceptance.md)。

## 2026-10-19 M3 识别文本插入与AI整理停用

在笔记编辑区选择“文字识别”或“语音输入”，核对后点击“插入正文”，内容进入当前笔记光标处或替换选区，可撤销并随原笔记保存。识别不再直接生成新笔记，M3 AI整理及配置入口已停用。已有识别原文与笔记保留，M2 AI学习和普通Markdown导入保持。详见[使用与复验](docs/fzk/capture_text_acceptance.md)。
# 题库知识点自动索引（2026-10-20）

> 后续用户要求已覆盖本节：现改为 [AI知识点语义归类](docs/m4/topic_ai_acceptance.md)，停用短语推荐。API接入入口为题库页“API接入与模型配置”，亦可双击根目录 configure_ai.cmd 隐藏输入密钥。上传后点击“AI归类这N题”，核对范围后发送；已有匹配蓝色高亮，新标签只提供备选，用户选用后保存。

上传 PDF/ZIP/文档或识别图片后，按同课程知识点名称、别名和已确认题目的关键词自动推荐。明确且无歧义的名称匹配会设置新草稿的主标签；用户指定标签保留。题目校正区中推荐的已有标签排在前面并以蓝色标记，显示匹配依据；无明确匹配时提供题干短语备选，可一键创建并选中，再保存本题。分类完全在本地进行，无需模型密钥。[使用与验证](docs/m4/topic_index_acceptance.md)。
# 扫描PDF题库（2026-10-20）

支持检测无文字层及混合PDF（包括ZIP内PDF），明确点击“识别扫描页并拆分题目”后本地转图/OCR；保留正常文字页顺序，识别完成自动显示题目。每份有效PDF亦可整份强制OCR；原页仅供审核。新增可选pypdfium2渲染组件，安装backend/requirements-bank-ocr.lock后重启。[流程/边界/证据](docs/m4/pdf_ocr_acceptance.md)。
# 题库与资料分库、便捷删除（2026-10-20）

新题目原件独立进入“题库文件库”，不出现在资料阅读/资料搜索/资料导出；旧题目文件可显式“移入题库文件库”。标题行直接删题，支持批量删除与撤销，整份题库一键删除只确认一次，保留原件和历史作答。0021迁移复用统一数据库，完整备份兼容旧版本。[使用、边界与验证](docs/m4/library_delete_acceptance.md)。


### 批量题库、AI视觉转写与公式（2026-10-20）
ZIP先列目录，答案文件默认不选，可删除内部项/批量文件后再上传。扫描PDF点击“AI转写原页与公式”，图片可选择AI视觉识别；共用后端智谱Key，转写使用glm-4.6v-flash，归类使用glm-4.7-flash。默认只转写题目、不造答案，公式LaTeX预览与源码均保留；可确认转写后自动推荐已有知识标签或生成候选。原图和草稿仍须核对，失败显式续跑未完成页。上传列表移除、删除题目、删除原件各自独立。私人43页样例已本地转写对照，真实模型当前返回1305繁忙，未记为AI验收通过。详见 docs/m4/vision_import_acceptance.md。


### 当前题库：Markdown与GLM5.3（2026-10-20，优先于上文旧模型说明）
图片/扫描PDF直接交给GLM-5.3-Flash转写，文本拆题和知识点归类也使用该模型。题目保存为Markdown源码，表格自动转换，页面默认显示已渲染的表格/公式；展开“编辑Markdown源码与答案”校正，可“下载题目Markdown”。旧结果/历史试卷不重写。详见 docs/m4/markdown_53_acceptance.md。


2026-10-20 M4 标签交互更新：错题展示知识点并支持按标签查找；归类仅显示已选/AI推荐，随机练习用关键词搜索标签；全选本页可原子核验；考点词表收拢为名称/题数并跳转题目，管理操作折叠。见 docs/m4/topic_ux_acceptance.md。

2026-10-21：标签支持父子分级及已有标签搜索，子标签自动归属父级；图片/PDF默认自动判断并分离原文题目、答案与解析（本地OCR辅助＋GLM识别与原页核验），仍先入待审核草稿。见docs/user_guide.md最新说明。


2026-10-21：考点统计改为可展开/拖动分级的知识目录，末级直接查看渲染题目；“从资料库导入”支持搜索独立题库原件及直接打开已保存题库。操作与验证见 [考点目录说明](docs/m4/topic_ux_acceptance.md)。


2026-10-21：标签归类采用知识笔记式目录与页面内拖动，支持搜索父级/合并目标、删除未使用空标签；已有原件与本地上传共用规则、AI确认和扫描PDF识别队列。见 [归类与导入说明](docs/m4/topic_ux_acceptance.md)。


2026-10-21：非空标签也可删除，题目保留、空标签关联归入“未归类”，子标签提升；未自动判分的已完成练习支持逐题自评并记录错题。说明及验证见 [M4题库验收](docs/m4/question_bank_acceptance.md)。


2026-10-21：考点目录同题优先最深子标签展示；校正工具栏支持全选后“保存所选”，冲突整批回滚；进入上传校正从顶部展示。见 [操作说明](docs/m4/topic_ux_acceptance.md)。


2026-10-21：左侧新增“API接入”新手流程图、网页保存/连接状态（本机共用加密配置）和独立“使用反馈”；错题支持独立页面重做、自定每日目标（不足题量按现有待掌握题数），答对才计数；再次答错恢复待掌握，正确后可移出或保留。考点管理直接展示，标签只显示名称。见 [使用指南](docs/user_guide.md)。

2026-10-21：修复视觉核验提示词的source_status字段白名单/示例冲突；缺字段仍拒绝，超时不自动重发。仅模拟回归验证，未宣称真实模型可用性已复测。

2026-10-21：提交作答后直接展示原文参考解答/解析（Markdown公式与表格）；按原卷与大题自然题号合并展示子题，保留逐题判分。上传AI任务增加明显等待状态及“AI也会犯错，请仔细甄别”；标签创建控件统一对齐。见docs/contracts.md的M4-DISPLAY-REFERENCE-11。

2026-10-21 M4补充：继续按子题随机抽取，新练习携带原大题完整条件与图表，子题旁可点“查看整道题”查看其他子问；只回答当前抽中的题目。AI推荐的已有标签默认勾选，可取消后保存；上级标签单选直接回填搜索框。历史作答不回写，旧练习需重新抽题体验完整上下文。

2026-10-21 随机练习排序修正：题卡按本次冻结随机顺序编号1至N并依次显示，原卷题号只用于上下文关联；仅相邻同大题子问共用标题，不再按原卷重新排序。

2026-10-21 题库审核修复：全部有效题目核验后自动同步已确认；未改内容的重复保存保留核验状态。批量知识标签提供“都添加这个标签”（保留原标签）和“都改成这个标签”（替换原标签），工具栏统一对齐并支持手机。

2026-10-21 标签上限按最新要求改为每题5个；批量追加超限时逐题提示题库名、原题号及添加后标签数，整批不修改，历史标签不自动删减。

2026-10-21 题库校正交互：离开多题草稿只询问一次，取消可继续编辑；仅待审核无修改不阻塞。折叠题目直接显示具体待核对原因，填空判分方式移到题目顶部，选择框/展开入口增大并适配手机。


</details>
