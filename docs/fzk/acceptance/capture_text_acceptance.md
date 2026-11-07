# 识别文本插入与AI整理停用（M3-CAPTURE-TEXT-01）

2026-10-19，fzk，未提交推送。用户已确认M3-EDITOR-MATH-03手动验收通过，本轮调整以最新要求为准。

最新人工反馈：用户确认本轮验收通过，M3-CAPTURE-TEXT-01记为个人手动验收通过。未单独反馈的设备/模型和识别准确率不补写实测结论，团队接收仍待进行。后续按[逐项复验记录](manual_recheck.md)补验尚未明确反馈的其他功能。

## 使用方式

打开一篇笔记，在正文中放置光标或选中文字，再点击编辑区的“文字识别”或“语音输入”。文字识别支持图片、PDF、DOCX和已配置本地模型的音频转写；实时语音沿用浏览器语音服务。识别完成后核对文字，点击“插入正文”，替换选区或插入光标处，随后使用原笔记自动保存/手动保存及撤销重做。

识别窗口没有笔记标题、文件夹、标签或“保存为新笔记”，管理页也不再提供识别新建入口。用户自己新建的空白笔记仍可接收文本，正常的新建笔记和Markdown文件导入不受影响。识别不添加AI排版、总结或来源标题；原文中的符号、换行保持。页号/音频时间在“查看原始识别文本与来源位置”中核对。

关闭识别窗口不改正文，当前页面中的手动核对文本保留；页面刷新后仍可读取后台原识别任务，但未插入的手动修改没有额外持久化。插入前校验编辑会话、正文快照和保存冲突；目标变化时保留文字，需关闭窗口重新定位。401让出登录窗口，409阻止覆盖。成功插入后走原编辑器历史与保存逻辑。

## 停用范围

- M3笔记AI整理入口及配置入口移除；整理接口返回410，仍先验证登录与资源归属。
- 后台不会发送笔记整理请求；遗留排队/运行中NOTE_ORGANIZE任务在新版worker中取消并撤销租约。历史结果和已保存笔记保留。
- 个人笔记AI配置PUT返回410，GET仅查看停用状态和已有凭据元数据，DELETE保留revision保护供清除旧密钥；不会解密/使用已有密钥，也不会回退到服务器配置。
- 本轮不改变M2“AI学习”、普通Markdown导入、M1解析和已有数据库结构。无新依赖或迁移。

识别result.text为parts.text按顺序以空行连接。旧任务优先从parts取原文本，缺失parts时原样使用旧text，不用正则删除正文中的井号。历史笔记不批量重写。

## 手动复验

1. 打开已有笔记，在一句话中选几个字，文字识别上传图片/PDF/DOCX，核对后插入。只替换选区，笔记标题、目录与数量保持。
2. 点击撤销和重做，再保存、刷新，正文结果应保持。
3. 关闭识别窗口再打开，手动核对文字仍在；未点“插入正文”时原正文不变。
4. 从实时语音或已配置的本地音频转写获得文本，核对后插入当前笔记。不会单独创建另一篇。
5. 笔记页面不再有AI整理/API配置入口，识别窗口没有新建笔记选项。新建笔记、导入Markdown和M2 AI学习入口保持正常。

## 自动验证与部署

使用临时数据库、隔离8056/5178及自制文件，不测试真实用户笔记、真实API密钥或真人麦克风。

| 检查 | 2026-10-19实际结果 |
|---|---|
| `pytest backend/tests/m3/test_note_capture.py backend/tests/m3/test_note_ai_config.py -q` | 13项通过，含真实DOCX、扫描PDF资源关闭/位置、图片文本、权限/幂等、410、旧整理任务取消/租约撤销、旧凭据脱敏/清除及禁止服务器凭据回退 |
| `npm.cmd test --prefix frontend` | 14文件、58项通过，新增旧任务parts纯文本兼容及原文本保留 |
| `npm.cmd run test:e2e --prefix frontend -- note-capture.spec.ts --project=chromium --project=webkit` | 12项通过，两引擎各6项；390/1440选区插入、关闭保留、撤销/重做、原笔记保存/刷新、真实DOCX上传识别、无额外新建、401恢复、409阻止覆盖及模拟实时语音 |
| `npm.cmd run build --prefix frontend` / 相关Python文件Ruff | TypeScript与生产构建、静态检查通过 |

日志位于本地`.tools/capture-text-backend.log`、`capture-text-unit.log`、`capture-text-e2e.log`、`capture-text-build.log`。截图：[Chrome手机宽度](../evidence/capture-text-390-chromium.png)、[Chrome桌面](../evidence/capture-text-1440-chromium.png)、[WebKit手机宽度](../evidence/capture-text-390-webkit.png)、[WebKit桌面](../evidence/capture-text-1440-webkit.png)。已检查窄屏/桌面截图；按钮和核对区随窗口滚动可达，无整页横向溢出。

真实DOCX已通过前端上传→后台识别→插入原笔记。OCR测试使用自制图片和模拟OCR适配器、真实PDF渲染，本轮没有重新评估OCR识别率；语音用模拟浏览器服务验收，真人麦克风/本地Whisper推理未代测。用户已确认本轮新增行为验收通过，团队接收仍另行进行。

本机在确认无QUEUED/RUNNING任务后，已停止两个旧项目worker并启动新版单worker，旧进程不再派发整理请求。后端原启动方式为`--reload`；保存笔记后刷新前端即可使用。其他机器更新时需重启后端（若未开reload）和worker，避免旧进程仍运行旧逻辑。新版worker启动前已发出的远程请求无法撤回；此本机检查时没有运行中的整理任务。

[共享契约](../../contracts.md#m3-capture-text-01)、[交接](../../../collaboration/handoff.md)。旧AI整理及识别直接新建操作指南已移除，当前流程以本文为准。

## 安装与运行

项目根目录安装基础依赖：`python -m pip install -r backend/requirements.lock`；OCR/本地转写可选依赖：`python -m pip install -r backend/requirements-capture.lock`。后端使用`python -m uvicorn app.main:app --app-dir backend --reload`；另开终端设`$env:PYTHONPATH="backend"`后运行`python -m app.workers.materials`。前端使用`npm.cmd run dev --prefix frontend`。worker代码更新后需要重启worker。

本地音频转写可用`python scripts/setup_note_speech.py`准备模型，模型位于忽略的data/models，识别任务不会自动下载。浏览器语音可能使用在线服务。图片/PDF/DOCX单文件20MiB，PDF最多40页，输出最多10万字；Word内嵌图片、文本框等不保证提取，识别文字需人工核对。识别缓存不进入完整业务备份。0017/0018保留以兼容已有数据库；旧整理/配置启用接口返回410，清除旧凭据仍需revision。
