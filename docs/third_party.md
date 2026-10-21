# 第三方说明

当前 Phase 0 未复制第三方源码或资源。依赖版本仅记录在 `backend/requirements.txt`，集成前应按锁文件和实际安装结果补充许可证核对。参考资料 `reference/GitHub_Projects.md` 中的项目尚未在本轮核实版本与许可证，不作为已采用依赖。

## 2026-10-13 实际依赖核对

本轮通过标准包依赖加入 react-markdown 10.1.0 与 remark-gfm 4.0.1，独立编写 Hustudy 引用/图片适配组件，未复制第三方项目业务源码。已读取安装包 license，均为 MIT，保留原作者与完整声明于 docs/licenses；前端 public/third-party-notices.txt 收集安装包的许可证，并随构建复制到 dist。锁文件保存确切依赖与 integrity。

Pillow 12.3.0 用于实际图片解码、尺寸/帧数校验，许可证从已安装 distribution 的 licenses/LICENSE 保留在 docs/licenses。其余后端已安装依赖版本记录为 requirements.lock，第三方审查仍须覆盖完整发布包；本记录不宣称所有历史参考仓库已核实。

接口参考：[Alembic 官方教程](https://alembic.sqlalchemy.org/en/latest/tutorial.html)、[SQLite FTS5 文档](https://www.sqlite.org/fts5.html)、[python-docx Document API](https://python-docx.readthedocs.io/en/latest/api/document.html)、[react-markdown 官方说明](https://github.com/remarkjs/react-markdown)、[Pillow Image API](https://pillow.readthedocs.io/en/stable/reference/Image.html)。核对日期 2026-10-13；当前实现与测试结果独立记录在 progress。

## 2026-10-14 PDF.js 页级阅读依赖

安装并锁定 pdfjs-dist 6.4.299，安装包 license 为 Apache-2.0；Node engine 为 >=22.13.0 或 >=24，本机 Node 25.2.1。通过官方 npm registry 安装，未复制他人业务页面；Hustudy 阅读/截图组件为独立实现。[Mozilla 官方示例](https://mozilla.github.io/pdf.js/examples/)与[官方 API](https://mozilla.github.io/pdf.js/api/draft/module-pdfjsLib.html)用于核实 getDocument、页渲染和 worker 使用。

已保存安装包及其 CMap/字体/ICC/解码器的 11 份 LICENSE 于 docs/licenses/pdfjs-dist，并在 public/third-party-notices.txt 收录；Vite 同时把对应包内资源和随附声明输出至 pdfjs-assets，worker 自本地安装包构建。标准字体中 Foxit/Liberation 及解码库有各自声明，不能仅用 PDF.js 主许可证代替。

Node PDF 渲染验证使用包的可选 @napi-rs/canvas（MIT），已核对安装包声明并保留 docs/licenses/napi-rs-canvas-MIT.txt。该依赖不进入浏览器业务包；检查环境应保留 npm 默认可选依赖。未声称全部历史依赖已完成发布审查。

## 2026-10-15 标准JWT

锁定PyJWT 2.15.1用于固定HS256访问令牌；[PyPI该版本](https://pypi.org/project/PyJWT/2.15.1/)及[官方API](https://pyjwt.readthedocs.io/en/stable/api.html)已核对。安装包声明为MIT，完整LICENSE复制至[PyJWT-MIT.txt](licenses/PyJWT-MIT.txt)。不采用示例中的短密钥、不添加crypto扩展或第三方身份服务；现有密码hash保留，项目JWT校验与迁移行为独立实现/测试。

## 2026-10-15 共享前端与测试基线

从官方npm源锁定React Router/react-router-dom 7.18.4、TanStack React Query/query-core 5.104.2、Ant Design 6.6.6；安装包MIT声明已读取并完整保留在[许可证目录](licenses/)，运行时声明同时附入public/third-party-notices.txt随构建分发。业务页面/状态恢复为本项目独立实现，不复制参考项目UI源码。

测试依赖Vitest 4.1.11（MIT）与@playwright/test 1.64.1（Apache-2.0，附NOTICE）已锁定，完整声明保留在同目录；不进入浏览器业务包。Playwright WebKit/FFmpeg只在忽略的.tools目录作为本机测试工具，未作为网站资源分发；Chrome测试使用本机现有安装及独立临时profile。

核对接口参考：[React Router useBlocker](https://reactrouter.com/api/hooks/useBlocker)、[QueryClient](https://tanstack.com/query/latest/docs/framework/react/reference/QueryClient)、[Ant Design ConfigProvider](https://ant.design/components/config-provider)、[Vitest指南](https://vitest.dev/guide/)、[Playwright隔离服务](https://playwright.dev/docs/test-webserver)与[浏览器配置](https://playwright.dev/docs/browsers)。核对日期2026-10-15。未声称全部历史依赖/发布包完成许可证审查。

## 2026-10-15 预览兼容与本机转换工具

实际Safari抛出Map.getOrInsertComputed缺失，改用已锁定pdfjs-dist 6.4.299的legacy显示层与worker，不引入第二个PDF版本。包内兼容代码标明core-js 3.50.0及官方MIT链接，已核对[该版本许可证](https://github.com/zloirock/core-js/blob/v3.50.0/LICENSE)，保留[完整MIT声明](licenses/core-js-3.50.0-MIT.txt)并追加浏览器第三方声明。PDF.js及字体/解码器的既有许可证继续分发。[Mozilla构建说明](https://mozilla.github.io/pdf.js/getting_started/)提供modern/older-browser两种构建。

获准通过Homebrew官方cask安装LibreOffice 26.8.1（程序26.8.1.1），读取安装随附Resources/LICENSE/NOTICE；产品主许可MPL2.0，附属组件有各自声明。仅作为系统外部命令运行，不复制或随网站分发应用二进制。[官方命令参数](https://help.libreoffice.org/latest/en-US/text/shared/guide/start_parameters.html)和[PDF导出参数](https://help.libreoffice.org/latest/en-US/text/shared/guide/pdf_params.html)已核对，ExportHiddenSlides默认false，本项目显式true保证页号。此记录不把全部系统工具或发布包许可证审查写成完成。

## 2026-10-15 原格式 Office 预览

使用发布包而非拷贝仓库源码，固定 `@aiden0z/pptx-renderer@1.3.0` 和 `docx-preview@0.4.1`，均已核对包内LICENSE为Apache-2.0；无上游源码修改。构建工具显式锁定现有Rolldown1.2.13（MIT），运行时打包为本地IIFE，不使用CDN或在线文档服务。

- PPTX作者/源码/接口：[aiden0z/pptx-renderer](https://github.com/aiden0z/pptx-renderer)，保留发布包THIRD_PARTY_NOTICES及licenses；该文件明确预构建渲染器内含未修改的mtx-decompressor1.4.2（MPL-2.0），对应源代码见[上游版本tag](https://github.com/ChristopherVR/mtx-decompressor/tree/v1.4.2)。此MPL条款不能被主包Apache覆盖；未修改覆盖文件，保留许可证及获取源码说明。npm同时解析的mtx-decompressor1.8.0不是此预构建嵌入版本，不能据安装树改写上游嵌入声明。
- DOCX作者：[Volodymyr Baydalka/docxjs](https://github.com/VolodymyrBaydalka/docxjs)，包内0.4.1许可证/作者声明保留；接口renderAsync直接读OOXML，不代表Word原生排版引擎。
- JSZip3.10.2采用包内允许的MIT选项；ECharts6.1.0、zrender6.1.0、tslib2.3.0及JSZip依赖/嵌入组件的license/notice一并保存；ECMA几何派生资料遵循上游声明，未把标准来源删成自制资源。
- 完整[许可归档](licenses/native-office-notices-2026-10-15.txt)；build:office根据实际安装包重建浏览器`/native-office/notices.txt`，现有third-party-notices增加入口，生产构建包含该文件。生成runtime和notice不提交重复二进制包，由package-lock和构建脚本重现。

曾考察501351981/pptx-preview，其README含源码再分发/修改限制，未引入，不把npm元数据中的许可简称当作已核实许可。原格式预览的复杂动画、字体/图表兼容不作为第三方或本项目已全量验证成果。

## M3 本地识别与凭据加密（2026-10-18）

仅调用公开Python接口，不复制上游源码；运行依赖保留wheel自带完整许可证。发行打包时须同时保留以下包及其依赖的许可/NOTICE，模型权重与应用源码分别记录。

| 组件 | 锁定版本 | 作者/许可 | 核实来源与用途 |
|---|---|---|---|
| rapidocr-onnxruntime | 1.4.4 | RapidOCR Authors，Apache-2.0 | [上游许可](https://github.com/RapidAI/RapidOCR/blob/v1.4.4/LICENSE)，使用随包提供的PaddleOCR转换ONNX模型进行本地OCR |
| pypdfium2 | 4.30.0 | pypdfium2团队，Apache-2.0/BSD-3-Clause；PDFium及第三方许可随wheel附带 | [上游](https://github.com/pypdfium2-team/pypdfium2)，只渲染扫描页，非排版重建 |
| faster-whisper | 1.2.1 | SYSTRAN，MIT | [上游许可](https://github.com/SYSTRAN/faster-whisper/blob/v1.2.1/LICENSE)，可选本地CPU语音转写 |
| Whisper base转换模型 | 安装时记录仓库commit | OpenAI/SYSTRAN，MIT（模型卡） | [模型卡](https://huggingface.co/Systran/faster-whisper-base)，模型单独下载，不在任务中自动联网 |
| cryptography | 46.0.3 | Python Cryptographic Authority，Apache-2.0或BSD-3-Clause | [版本](https://pypi.org/project/cryptography/46.0.3/)，Fernet/HKDF，个人API凭据加密 |
| Web Speech API | 浏览器内置 | 无新增可再分发依赖 | [MDN](https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition)，浏览器可依赖在线服务，页面明确确认；非全离线识别 |

Windows Python3.11本地CPU组件安装和图片/扫描PDF实测；依赖闭包见backend/requirements-capture.lock。可选本地Whisper模型与真实音频质量未验收。浏览器语音交互测试为模拟，不能声称实际浏览器服务或麦克风已验证。

## M3 Markdown 公式（2026-10-18）

| 组件 | 精确版本 | 作者/许可 | 用途与来源 |
|---|---|---|---|
| KaTeX | 0.19.0 | Khan Academy and other contributors，MIT | [上游](https://github.com/KaTeX/KaTeX)，本地公式排版与随包字体；许可证以安装包 LICENSE 为准 |
| remark-math | 6.0.0 | Junyoung Choi，MIT | [上游完整许可](https://github.com/remarkjs/remark-math/blob/main/license)，数学 Markdown 语法。发布包未携带完整 license，按其 readme 指向补存 frontend/licenses/remark-math-MIT.txt |
| remark-parse / unified | 11.0.0 / 11.0.5 | Titus Wormer，MIT | [remark](https://github.com/remarkjs/remark)、[unified](https://github.com/unifiedjs/unified)，原有间接依赖显式声明，用 AST 定位公式及排除代码/转义文本 |

复用公开 API，不复制第三方编辑器 UI 源码；工具栏图标为本项目自绘 SVG。数学依赖闭包的完整许可由 `npm run build:math --prefix frontend` 从实际安装包生成到 `/math-notices.txt`（58 包，包括类型依赖）；predev/prebuild 保留原 Office 构建并增加数学许可生成，生产分发包含许可。KaTeX 版本覆盖消除 micromark-extension-math 的旧嵌套 KaTeX，具体闭包由 package-lock.json 锁定；当前 npm install 审计 0 漏洞。运行关闭 trust、限制长度/宏展开/尺寸，不从 CDN 获取渲染器、字体或公式图片。

## 2026-10-18 M3 公式工作区扩展

本轮没有新增第三方依赖或拷贝编辑器源码。用户指定[LaTeX速查页](https://blog.somnus.wiki/latex/)仅作为分类覆盖参考；符号命令、标准数学例式及中文帮助由本项目整理编写，使用既有KaTeX逐项验证，许可生成链保持。

## 2026-10-19 M3 图形符号与结构填写

本轮参考[AxMath官方手册](https://www.axsoft.co/AxMath_Help.pdf)的分类符号面板和结构子字段交互，自行实现数据、扫描器、按钮与样式。没有复制AxMath代码、图标、安装包或文档正文；没有新增第三方依赖。图形按钮使用既有本地KaTeX输出，完整许可生成流程不变。

## M4 图片题库本地OCR（2026-10-20）

复用RapidOCR 1.4.4公开Python API，不复制源码；接口已按[版本文档](https://rapidai.github.io/RapidOCRDocs/v1.4.4/install_usage/api/RapidOCR/)核对返回的行坐标、文字与分数，用于按阅读顺序和题号切分。当前Windows/Python3.12安装闭包见 `backend/requirements-bank-ocr.lock`，不安装语音组件；`pip check`无冲突。实际安装wheel许可/NOTICE及元数据记录保存在 `docs/licenses/m4-ocr/manifest.json` 与同目录包名子目录；模型使用RapidOCR包内现有ONNX，未下载、改写或单独再发布权重。自制三张PNG只含本项目编写的题目/线框图，不含第三方试卷。真实OCR样例可验证运行，不作为通用准确率指标；完整发行许可还需按发布包审阅。
## M4 扫描PDF本地渲染（2026-10-20）

M4可选OCR依赖复用pypdfium2==4.30.0；用途扩展为题库PDF原页渲染，识别继续使用既有RapidOCR。wheel随附完整PDFium/第三方许可已保存至docs/licenses/m4-ocr/pypdfium2，清单追加到manifest.json，不复制PDFium二进制到源码。无需引入语音组件；依赖检查以本轮实际pip check为准。
