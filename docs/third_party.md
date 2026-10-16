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
