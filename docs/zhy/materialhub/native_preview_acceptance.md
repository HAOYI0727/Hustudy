# M1 按原格式直接预览验收

2026-10-15，Codex辅助zhy；任务M1-NATIVE-PREVIEW-01，FR-06/36、FR-07/37兼容依赖、NFR-06/10、TC-04/26；工作区未提交/合并，zhy审阅与xtc/fzk/gcx接收待本人填写。

## 原因与用户变更

早期规划明确使用“LibreOffice转PDF + PDF.js”统一显示Office版面，因此原按钮叫PDF预览，原件没有被替换。这提供静态兼容图像，不能冒称PPT/Word原格式。用户本会话明确要求按原文件格式预览，已在公共contracts、根/正式main_idea、正式需求CR-M1-NATIVE-01与AGENTS技术基线同步变更。

本轮支持项目已允许的 `.pptx`、`.pdf`、`.docx` 三类。旧 `.ppt`/`.doc`、在线编辑、完整动画/宏/音视频与微软Office完全保真不属于本切片；不要把DOCS理解为已接入在线Google Docs账号。

## 输入、输出和界面

- 仍从现有GET versions/{id}/original取本人有效原件，所有权/课程删除/下载限制保持；不新增数据表、版本或转换任务，不改原文Chunk/Citation。文件读取可取消，切版本/卸载丢弃旧结果。
- PPTX显示“PPT 预览”，按原幻灯片顺序/隐藏页前后翻页、序号跳转、缩放与演示模式；左右方向键/PageUp/PageDown切换，Escape退出演示。文本、样式、表格、图片由原OOXML渲染。
- DOCX显示“Word 预览”，直接保留基础段落、字体样式、表格、图片、显式分页；前后页/跳页/缩放/窗口变动适配。阅读页由浏览器排版，不能当Word原始页码或docx_block引用偏移。
- PDF仍显示“PDF 预览”，直接打开原PDF，现有分页、缩放、截图/补录不变。Office原转换路径另叫“兼容预览（PDF）”，转换器缺失/处理中不禁用原格式入口；兼容状态/修复折叠展示，避免误以为原格式也必须转换。
- 原格式失败给明确错误、显式重试/原件下载，兼容PDF可用时提供切换；25秒观察计时用于结束等待，不宣称硬实时CPU中断。可返回文本选择结构化引用。截图仍用兼容PDF页和现有服务端来源校验，未将原格式DOM截图冒充PDF截图。
- 后台解析完成仅补文本数据，不能将已打开的PPT/Word/PDF视图切回文本；此问题在首次完整WebKit回归中被发现并修复，测试用暂空chunks后释放来固定时序。

## 本地隔离与依赖

Office渲染在 `sandbox="allow-scripts"`、无allow-same-origin的iframe中执行，父页面只传原件ArrayBuffer和随机通道，不传token/用户名/凭据。nonce限制可执行脚本，CSP禁止connect、外部图片字体、媒体、子框架/worker、base和表单；只允许本地data/blob图片字体及样式。父消息同时校验Window source、opaque origin、随机通道、类型及1–2000页范围；伪造父页面state不能改变页数。文件内容中的链接不能触发导航。

固定@aiden0z/pptx-renderer1.3.0、docx-preview0.4.1及构建用Rolldown1.2.13；原运行时代码未修改，IIFE本地生成、按需取用，不使用CDN或外部Office服务。OfficeReader约6.74KB，独立原格式runtime约1.31MB，不塞入主入口；原始字体/复杂图表/SmartArt兼容有边界。完整许可/嵌入MPL对应源码说明见[第三方声明](../../third_party.md)和[许可归档](../../licenses/native-office-notices-2026-10-15.txt)。这不是原生PowerPoint/Word应用嵌入。

构建入口为 `npm run build:office --prefix frontend`；npm run dev/build的pre钩子会重建public/native-office，生成产物被Git忽略，锁文件及源码脚本保留。Vite已在运行时本轮也手动生成运行时文件，可刷新现有页面使用，无须重新上传资料。

## 实际验证

- [自制样例生成](../../../scripts/create_native_preview_fixtures.py)：2页PPTX含隐藏页/字体/背景/表格/自制图片；2阅读页DOCX含粗体/表格/图片/外部链接/显式换页与字面script文本。不读取用户课程，不伪造人工核对或Word原版截图。
- [隔离单测](../../../frontend/tests/unit/native-office.test.ts)：nonce/CSP、结束script字符串转义、防注入标识；连同原有前端单测共14项通过。
- [浏览器场景](../../../frontend/tests/e2e/native-preview.spec.ts)：两格式直接原件渲染/样式表格图片、2页导航/隐藏页、缩放/演示；强制PDF预览不可读且请求次数0，验证无需转换；隔离读取父localStorage抛错、主动fetch被CSP阻止、无外网请求、父窗口伪造state无效、字面script不执行。渲染坏ZIP给错误并卸载iframe，显式重试重新读原件成功，不偷偷转PDF。
- 首轮4项原格式双引擎通过（21.7秒）；完整回归新增故障注入最初被React StrictMode重复GET干扰，改为持续坏数据直至用户重试；随后WebKit暴露后台解析切回文本问题，已修复并补确定性时序。不将失败或首轮部分通过冒记最终全部通过。
- 共享check已运行：116 pytest / 19.60秒、14Vitest、Ruff、迁移漂移、安全Markdown/AI显示、PDF双页、类型/构建通过；日志/tmp/hustudy-native-check-final.log。随后文件读取取消/后台模式修复的最终类型/构建及26项浏览器复验通过；最终构建日志/tmp/hustudy-native-build-final.log。
- 最终双引擎全量26项通过（2.1分钟，Chrome/WebKit各13项，无重试）；日志/tmp/hustudy-native-all-e2e-final.log。不使用现有8000/5173/用户账户或真实模型。

截图在隔离Playwright输出目录，已实际查看PPTX和DOCX的WebKit页面，确认标题/表格/图片与公共面板风格。截图不含私有课件且被Git忽略，不宣称人工Office全版式对照已完成。本机Safari当前真实账户完整操作仍未作为本轮已通过证据。

## 交接与限制

zhy交xtc/fzk/gcx：现有预览任务状态仍表示PDF兼容状态，原格式是否成功由本地阅读器报告，不能写回覆盖旧状态；来源仍按不可变UUID。M3/M4回源/截图继续消费既有契约，不能把Word浏览器页改成正文页码。成员本人填写接收/复验，不能代签。

旧二进制格式需另存为PPTX/DOCX；不存在字体可能替换，复杂图表/公式/布局或宏动画不保证完整。外部链接图片/音视频被阻止，遇到缺失内容可切换兼容PDF或下载原件核对。不推定用户当前146页课件已经按原格式完整验收，也不据自动通过关闭Gitee/真实试用或其他模块P0。

最终静态复核：64份文档638个本地链接无缺失、19个handoff锚点唯一；git diff --check、Ruff、新构建脚本Node语法通过，许可归档与实际生成notice逐字节一致。最后前端构建474ms通过，主包486.40KB、PDF492.59KB，无500KB提示；未重新跑完整后端，因为最终增量仅为前端模式保持/取消读取。所有实际修改保留工作区，未提交/合并，原用户已删除个人报告未恢复。
