# 所选笔记离线图片与批量上传验收

2026-10-19人工反馈：用户确认普通上传/导出及6A部分失败重试、6B图片管理和第8项来源失效导出通过；所有阅读器和团队集成仍分别验收。[当前M3余项核查](m3_completion_audit.md)。

2026-10-18；Codex辅助fzk；M3-BATCH-IMAGES-01，C05/C07/C09/C10，FR-09/14。当前本地功能分支未提交/推送/合并，无新迁移或依赖；[契约](../../contracts.md#m3-batch-images-01)、[API](../../api.md)、[交接](../../../collaboration/handoff.md#h-20261018-fzk-002)。本记录更新上一轮可选图片的默认行为，历史测试仍按当时版本理解。

## 当前行为

- 勾选A、B：只打包A.md、B.md和它们实际引用的images文件；不导出其他笔记、不递归加入双链目标、不带入图库闲置图片，也不带README/manifest/重复原文。同一Asset被多篇引用只保存一份，图片同名仍分配不同安全名称。
- 图片自动附带，标题和图片路径按既有Windows安全命名及URL编码处理。整包解压到同一文件夹后，用支持标准Markdown图片的阅读器打开；不要只移动md或只在ZIP预览器中打开。已失效图片显示说明，外部URL不下载；现有图片损坏时导出失败而不生成假成功包。
- 笔记编辑器“上传图片并插入”和图库“选择图片”支持一次多选，每批最多20张、单张非空且≤10MiB，PNG/JPEG/WebP，服务端校验实际图片内容。按文件选择顺序逐张上传，编辑器成功图片按顺序插入；图库导入后由用户选用。
- 进度显示当前序号/总数/文件名，部分失败列出文件名和原因；重试只处理未完成项。认证、网络、限流、服务错误停止后续请求，不自动重放；响应丢失可能已经上传，提示先核对图库，确认无须重试可清除未完成列表。
- 上传期间继续输入保留，离页/切换有保护，失败不清空正文。成功的图片进入同一M1图库，保留改名/说明/标签/引用/删除功能。
- 服务端include_images默认true；显式false兼容原API纯文本调用。旧请求和下载包保持原参数/字节，更新后需重新创建导出。

## 自动验证

全部使用临时账户、临时库/存储、自制PNG和模拟错误；不触碰用户笔记或调用真实模型。

| 验证 | 命令（项目根执行，npm在Windows使用npm.cmd） | 实际结果 |
|---|---|---|
| 导出及生命周期 | `.venv/Scripts/python.exe -m pytest backend/tests/m3/test_note_exports.py backend/tests/m3/test_note_simple_exports.py backend/tests/m3/test_note_export_names.py -q` | 18项最终通过。首次17通过/1新增测试断言误读响应中不存在的sha256字段；改为对原始存储字节计算hash后，`test_note_simple_exports.py`全6项复验通过（8.45s） |
| 队列/前端回归 | `npm.cmd test --prefix frontend` | 9文件36项通过（22.90s），含顺序/部分失败/仅失败重试/空文件/类型/超限，以及0/401/403/429/500/507停止队列 |
| Chrome闭环 | `npm.cmd run test:e2e --prefix frontend -- note-portability.spec.ts note-tags.spec.ts --project=chromium` | 17项最终通过：首轮16通过（4.5min），新增离线用例在断言成功后的收尾阶段超过60s总预算；该完整流程改90s预算后单独`--grep 批量图片插入`通过（用例14.5s，运行36.7s） |
| 编译/规范 | `npm.cmd run build --prefix frontend`；`.venv/Scripts/python.exe -m ruff check backend/app/schemas/note_exports.py backend/app/services/note_exports.py backend/tests/m3/test_note_simple_exports.py` | TypeScript、生产构建、Ruff通过；恢复构建产生的tsconfig.tsbuildinfo，保留源码改动 |

浏览器使用`HUSTUDY_E2E_CHROME_CHANNEL=chrome`，Python UTF-8与本地venv PATH；独立8056/5178后端/worker/前端。新增用例批量上传两张真实自制PNG，重载预览、两篇共享图片、排除第三篇专属图片，下载ZIP断言只有两篇md和两张图；用ReactMarkdown渲染实际导出正文，在offline浏览器上下文打开本地file页面，逐张核对file路径和naturalWidth=320。测试HTML只生成在忽略的test-results目录，不加入ZIP。部分失败用例验证第一张保留、只重试第二张、图库多选导入两张且不改笔记正文；既有图片校验、上传中编辑、改名/删除、草稿/标签/双链回归保持。

已检查[390px选择导出](../evidence/note-selected-images-390.png)、[1440px选择导出](../evidence/note-selected-images-1440.png)、[断网本地图片](../evidence/note-offline-images.png)截图：布局无横向溢出，离线两张图片可见。上述浏览器测试共17个不同用例，复跑不重复计数；不宣称完整后端测试套件通过。

## 手工复验

1. 重启API和worker，刷新前端；打开一篇笔记，点击“上传图片并插入”，按Ctrl或Shift多选两张图片，等状态显示保存成功，预览应显示两张。
2. 在“管理图片”中多选两张导入，确认都出现在图库，可分别整理。
3. 让笔记A、B引用图片，其中一张共用；另建C或保留其他图库图片。导出面板只勾选A、B，下载新ZIP，检查只有两篇md及必需图片。
4. 完整解压后断网，用Markdown阅读器打开A/B；图片应正常显示，共用图片只有一份。
5. 混选有效图片和伪装PNG文本，确认有效图片保留、失败文件单独提示；重试后成功图片不重复插入。

本机Chrome验证不代表所有Markdown阅读器、WebKit、移动实机或跨机器已验收；本人复验与队长集成待接收。单独.md下载不携带二进制附件，需要离线图片使用选择导出ZIP。
