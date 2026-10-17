# Hustudy 环境与验收指南

2026-10-17 M2真实课件更新：需停止并重启后端与worker，前端运行时Ctrl+F5即可；无新依赖/迁移，无需重设密钥。报告新预览纳入完整有界正文并分批，旧预览范围不变。重启命令、普通python与Anaconda完整路径见[本轮说明](gcx/real_materials_2026_10_17.md#重启与人工验收)。

## Windows当前复现（2026-10-16，gcx电脑）

已发现Python3.12.4位于`E:\Anaconda\python.exe`，Node24.14.1。用户要求复用现有环境、不创建venv，已手动安装backend/requirements.txt和npm ci。README历史Bash命令是其他平台路径。Windows完整锁文件含无条件uvloop，不直接照搬；复用环境安装曾提示现有Streamlit与Pillow/NumPy冲突，本轮未调整其他软件依赖。

项目根目录为`E:\aa大学\大三上\软件工程\Hustudy\Hustudy-main`。三个PowerShell分别在根目录执行：

```powershell
# 终端一
$env:PYTHONUTF8 = '1'
& 'E:\Anaconda\python.exe' -m uvicorn app.main:app --app-dir backend --reload
# 终端二
$env:PYTHONUTF8 = '1'
$env:PYTHONPATH = 'backend'
& 'E:\Anaconda\python.exe' -m app.workers.materials
# 终端三
npm run dev --prefix frontend
```

浏览器访问http://localhost:5173/；改worker代码后需手动Ctrl+C并重启worker。裸python曾指向不同解释器，使用上述完整路径；若先把E:\Anaconda及Scripts加到当前终端PATH，也可使用python。没有修改系统PATH/创建环境。报告本轮测试和完整Windows限制见[验收](gcx/study_report_acceptance.md)。


更新：2026-10-15。目标Python3.12，当前运行环境3.11.15；独立3.12.13锁依赖环境已通过101项后端测试。Node25.2.1实测，PDF.js要求Node>=22.13.0或>=24。Chrome/WebKit隔离浏览器14项通过，范围见[验收记录](zhy/shared_platform/web_base_acceptance.md)；LibreOffice26.8.1真实转换已通过，复杂版式/干净机器全量部署仍待验收。

## 安装和启动

在项目根运行：

```bash
bash scripts/setup.sh
```

脚本创建/复用.venv，按backend/requirements.lock安装；npm ci始终同步前端锁文件。只在.env缺失时复制示例，自动为JWT空值/旧占位生成随机密钥并设置0600权限，保留现有有效密钥和GLM配置。密钥不能提交Git或放VITE变量，不要在每次启动时轮换，否则旧会话立即失效。

新建环境可指定Python3.12：

```bash
PYTHON_BIN=python3.12 bash scripts/setup.sh
```

已有.venv会复用，指定PYTHON_BIN不会替换它。若需要验证另一解释器，先创建独立环境并安装锁依赖，确认通过后再计划切换现有服务，避免直接删除正在运行的环境。

分别在两个终端运行：

```bash
# 后端8000 + 持久worker
bash scripts/dev.sh
```

```bash
# 前端5173
npm run dev --prefix frontend
```

访问http://localhost:5173；API健康检查http://127.0.0.1:8000/health，OpenAPI为/api文档地址http://127.0.0.1:8000/docs。若只单独启动API，需另开终端运行bash scripts/worker.sh，否则解析/预览/AI/备份会停留排队；不要重复启动多个无意的worker。修改.env后重启API与worker。

PPTX/DOCX预览转换需要LibreOffice的soffice可执行程序。没有时保留明确失败状态和文本阅读；PDF直接由本地PDF.js阅读。不能把缺少转换器当作解析失败，也不能声称已验证Office成功预览。文件/数据库位于data，禁止提交用户原件；低磁盘预检默认保留64MiB，HTTP507时先释放空间再重试。

## 日常检查

```bash
bash scripts/check.sh
```

包含Ruff、隔离pytest、临时库迁移/ORM漂移、实际Markdown安全渲染、PDF.js双页PNG、Vitest、TypeScript与生产构建。保留npm默认可选依赖，Node渲染检查使用@napi-rs/canvas。当前1条Starlette/anyio弃用警告不冒记为无警告。

本机独立Python3.12复验入口（.tools不提交）：

```bash
PYTHONPATH=backend .tools/venv312/bin/python -m pytest -q
```

## 浏览器自动验收

默认使用Playwright Chromium与WebKit，浏览器首次需从官方源安装：

```bash
cd frontend
PLAYWRIGHT_BROWSERS_PATH=../.tools/playwright npx playwright install chromium webkit
npm run test:e2e
```

若本机已有Google Chrome，可使用独立临时profile运行Chrome项目，并只安装WebKit：

```bash
cd frontend
PLAYWRIGHT_BROWSERS_PATH=../.tools/playwright npx playwright install webkit
HUSTUDY_E2E_CHROME_CHANNEL=chrome npm run test:e2e
```

测试启动8056 API+worker和5178 Vite，仅绑定127.0.0.1；一次性数据库/文件与用户8000/5173隔离，默认Mock且远程密钥为空。不要改成复用当前用户服务。端口占用时先停止此前测试服务，不能随意终止用户进程；浏览器系统依赖按[官方安装指南](https://playwright.dev/docs/browsers)准备。test-results/playwright-report和下载浏览器均被Git忽略。

## 配置智谱GLM-4.7-Flash

工程根运行`.venv/bin/python scripts/configure_zhipu.py`，隐藏输入密钥；配置只在后端.env。真实课程问答先预览将发送的问题/原文/目的地，再逐次确认。预览不调用模型；失败、重登和任务过期不自动重发。演示模式、阅读、笔记和本地检索可独立使用。

可选自制连通检查：`PYTHONPATH=backend .venv/bin/python scripts/probe_zhipu.py --confirm-synthetic-send`。仅发送脚本苹果样例，不读数据库；仍是一次真实外部调用。费用/额度依服务账户，保留/训练政策未核实，不能承诺无限免费或全离线。见[真实问答证据](zhy/integration/zhipu_qa_acceptance.md)。

## 数据保护和部署

“备份与恢复”生成账户ZIP，下载后妥善保管；只在新数据库的空账户恢复，不覆盖已有数据。它与M1课程资料ZIP不同，版本/UUID冲突和损坏会拒绝。恢复前先读[用户操作](user_guide.md)与[恢复边界](zhy/shared_platform/account_backup_acceptance.md)。迁移前SQLite自动备份不包含附件，不能代替整账户备份。

页面使用history路由，部署静态前端须对非静态业务路径回退index.html；API和下载路径仍交给FastAPI。Vite开发/预览自动支持回退。部署到不同地址时配置前端VITE_API_BASE_URL和后端HUSTUDY_CORS_ORIGINS，不能把API密钥放前端。当前没有公开发布或Gitee/CI成功运行的证据。

## Office与Safari预览补验（2026-10-15）

本机已通过获准Homebrew官方cask安装LibreOffice26.8.1，soffice程序26.8.1.1，PPTX/DOCX真实转换与Chrome/WebKit截图回源通过。其他开发机器需自行安装LibreOffice；可设后端HUSTUDY_LIBREOFFICE_PATH为可执行程序绝对路径，留空则自动发现。修改配置后重启API与worker，安装后从阅读区检查环境并重试旧任务，不必重传资料。

新增浏览器预览测试依赖真实Office；普通pytest固定不可用的测试路径并注入转换结果，覆盖失败而不依赖本机软件。自制样例可用`.venv/bin/python scripts/create_preview_fixtures.py`生成；E2E仍使用临时数据库。PDF.js显示层/worker统一legacy兼容构建，不需要用户关闭浏览器安全设置或从外部CDN加载脚本。

## 队长完整本地验收入口

准备Chrome/Playwright WebKit后，`HUSTUDY_E2E_CHROME_CHANNEL=chrome bash scripts/accept_captain.sh` 依次执行共享check、隔离双引擎和容量测试，日志保存到独立临时目录；任一步失败立即非零退出。默认浏览器配置见frontend/playwright.config.ts，不连接现有8000/5173或用户课程。容量测试需要本机监听权限。

干净依赖重建另用 `.venv/bin/python scripts/verify_clean_setup.py --python <Python3.12绝对路径> --output /tmp/hustudy-clean.json`，需依赖下载网络；临时源码只复制backend/frontend/scripts/fixtures及.env.example，新建venv/npm ci，最后清理。2026-10-15同机Python3.12.13重建已通过115项pytest及12项Vitest/全部共享检查；后续新增用例以最新报告为准，不把同机重建称为跨机器验收。

## 本地原格式阅读运行时

新增直接PPTX/DOCX预览后，`npm run dev --prefix frontend` 和 `npm run build --prefix frontend` 的pre钩子自动执行build:office；若开发服务器早已运行，可先 `npm run build:office --prefix frontend` 再刷新。源码在features/materials/office，生成public/native-office被Git忽略，正式构建会复制runtime.js/notices.txt。不要删除钩子或改为远程CDN。LibreOffice仅供Office兼容PDF/截图，不是原格式入口前置条件。新增依赖按package-lock安装，旧干净环境记录是新增依赖前快照，非本轮重新安装成绩。

## 当前默认模型切换（2026-10-17）

当前默认glm-5.3-flash，旧glm-4.7-flash可配置。密钥新配置：项目根执行python scripts/configure_zhipu.py，默认新模型；如需旧模型，加--model glm-4.7-flash。此次用户现有.env已仅更新模型，不需重输密钥。配置修改后手动重启API和worker，前端刷新并新建预览确认；新模型不是沿用旧免费权益，费用/权限以控制台为准。[完整重启命令](gcx/model_switch_2026_10_17.md)。
