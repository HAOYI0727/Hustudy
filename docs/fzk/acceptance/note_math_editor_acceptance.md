# M3 图标工具栏与公式编辑器

日期：2026-10-18；负责人 fzk，Codex 辅助实现；分支 `codex/fzk-m3-note-tags`，工作区未提交。用户本轮明确暂缓 AI 识别后续开发，保留既有入口与代码，本轮没有调用 AI。

## 入口与行为

- 笔记正文上方改为分组线性图标：加粗、斜体、标题、删除线、列表、任务、引用、代码、链接、表格、分隔线、图片、公式、撤销/重做、分屏与专注。复用公共 Icon，中文名称保留在悬浮说明及 aria-label。触屏热区至少 44px。
- 点 Σ（公式编辑器），或在正文按 Ctrl/Cmd+Shift+M。支持行内/独立公式，分数、根号、上下标、求和、积分、极限、矩阵、分段函数模板和常用符号；模板插入公式输入框选区，之后仍可编辑 LaTeX。
- 即时预览与语法错误提示。确认才更新正文；取消不改正文。把光标放入已有公式后再点 Σ，修改原公式而不叠加定界符。专注模式中第一次 Escape 只关公式窗口，第二次才退出专注。
- 正文使用标准 `$...$`、`$$` 独立行定界。分屏/Markdown 预览真实排版，保存、撤销、重做和导出沿用现有笔记流程。导出保留公式源码，外部阅读器需支持 Markdown 数学公式；普通货币美元符号可写 `\$`。
- 解析使用 Markdown AST 位置，转义美元、行内代码和代码块不误认公式；在代码内打开窗口会提示移出代码。公式正文最多 4000 字符，宏展开最多 200 次、排版尺寸上限 10em，宏定义不跨公式共享。
- 公式内部的美元符号和多行 LaTeX 注释会触发行内 Markdown 的定界/折行问题，窗口明确提示改用独立公式后再确认，避免预览与保存结果不一致。
- KaTeX 使用 `trust:false`，禁止可信 HTML、外部图片/URL 指令；不启用 Markdown 原始 HTML。公式错误显示源码与提示，不让一处错误阻止整篇预览。字体/CSS/运行代码打包在本地，无外部渲染服务。
- 自动保存遇到 401 时公式窗口让出登录，原账户登录后重新点 Σ 可继续窗口中的草稿；正文在窗口打开后发生变化时拒绝用旧选区覆盖。

## 手动复验

1. 选中正文 `x^2`，点 Σ，选择分数模板或输入 `\frac{a}{b}`；确认后检查前后文字、分屏排版和撤销/重做。
2. 把光标放回公式中，点 Σ，改为 `\sqrt{x}` 并更新；应替换原公式。再次打开后改内容但点取消，正文应保持原样。
3. 在段落末插入独立公式，用积分或矩阵模板；在输入框中修改占位字母。输入不完整的 `\frac{a}`，应出现错误并禁止确认。
4. 保存、刷新、导出 `.md`，检查两种公式源码都保留。代码块中的 `$x$` 保持代码；可以正常插入原有图片/UUID 双链。
5. 390px 手机宽度与桌面分别检查工具栏换行、弹窗滚动、公式局部横向滚动；专注模式中关闭公式窗口后仍保持专注。

## 验证记录

Windows 本机，Node 24.22.0、项目虚拟环境 Python 3.11；测试使用隔离 8056/5178、临时数据库和自制笔记。没有改写用户笔记或调用 AI。命令中的 Chrome channel 显式设置为 `chrome`；WebKit 使用项目 `.tools/playwright` 下的测试运行时。

| 检查 | 实际结果 |
|---|---|
| `npm.cmd test --prefix frontend` | 11 文件、48 项通过；包括 AST 定位、CRLF、公式替换、代码/转义美元、真实 HTML/MathML 输出、资源/宏隔离、特殊输入保护 |
| `npm.cmd run test:e2e --prefix frontend -- note-math.spec.ts note-organization.spec.ts --project=chromium` | 11 项通过，包含既有 7 项目录/批量导入/图片双链/离线导出/编辑与草稿回归 |
| `npm.cmd run test:e2e --prefix frontend -- note-math.spec.ts --project=chromium --project=webkit` 及下述定向复跑 | 公式原 4 场景的 Chrome/WebKit 成功记录均已取得；390/1440完整编辑导出，五宽度触屏/安全，以及401恢复 |
| `npm.cmd run test:e2e --prefix frontend -- note-math.spec.ts --grep 特殊LaTeX --project=chromium --project=webkit` | 新增特殊输入场景 2 项通过；多行注释选择独立公式后正文和实际渲染均保留 |
| `npm.cmd run test:e2e --prefix frontend -- note-math.spec.ts --grep 触屏布局 --project=webkit` | 1 项通过（33.8s）；320/390/820/1024/1440无全页横向溢出，图标热区≥44px，超长公式拒绝 |
| `npm.cmd run build --prefix frontend` | TypeScript、Office预构建、58包数学许可生成和生产构建通过 |
| 依赖与文档 | 安装审计0漏洞；文档本地链接及差异空白检查通过 |

过程修正：初次 WebKit 没有安装运行时，安装后实际执行发现鼠标点按钮不自动取得焦点，导致关闭公式窗口的焦点恢复失败；已显式聚焦触发按钮并在两种宽度复验。五尺寸组合测试一次超过原45秒预算，将该组合预算设置为120秒后定向复跑通过；这不是页面性能验收或延迟承诺。各次日志位于忽略目录 `.tools/editor-math-*.log`，统计不重复累计重跑；共17个不同浏览器场景获得成功记录。

已查看截图：[桌面图标与分屏](../evidence/note-math-editor-1440-chromium.png)、[390px编辑器](../evidence/note-math-editor-390-chromium.png)、[桌面公式窗口](../evidence/note-formula-dialog-1440-chromium.png)、[390px公式窗口](../evidence/note-formula-dialog-390-chromium.png)、[WebKit公式窗口](../evidence/note-formula-dialog-390-webkit.png)。本机 Windows WebKit 和触屏媒体/尺寸模拟不等于真实 Safari/iPhone/iPad、真人可用性评分或所有 LaTeX 写法已经验收。无后端业务改动，本轮未重复运行完整后端测试集。

## 实现与交接

无后端 API、数据库迁移或笔记保存格式变更。契约 M3-EDITOR-MATH-01 已先写入 AGENTS、公共 contracts 与 handoff。新增精确依赖 KaTeX 0.19.0、remark-math 6.0.0，并显式声明已有 remark-parse 11.0.0/unified 11.0.5；通过 override 将数学语法插件中的 KaTeX 统一为 0.19.0，避免旧嵌套包。锁文件与完整许可生成流程同步，见 [第三方记录](../../third_party.md)。

不包含手写公式识别、化学扩展、完整 LaTeX 文档编译或完全所见即所得的公式排版拖拽；本轮提供模板辅助的 LaTeX 编辑和预览。2026-10-18用户确认本轮手动复验通过；共享层评审仍待团队进行。后续新增范围见[公式工作区扩展](formula_workspace_acceptance.md)，上轮确认不代表扩展已通过手动验收。
