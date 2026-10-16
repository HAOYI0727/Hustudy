# 共享前端基线与会话恢复验收

日期：2026-10-15。任务PLATFORM-WEB-BASE-01，对应A01/A02/A09/A10、FR-01/06/09/11/13/15、NFR-06/07/09/10。记录者Codex（zhy队长会话辅助），本人审阅/其他成员接收待填，工作区未提交/合并。

## 输入、输出和边界

输入为现有React工作台、已授权课程/资料/笔记API和原账户会话；输出为统一路由、会话隔离的请求入口、原账户重新登录对话框，以及可复现的浏览器验收。共享契约先写入[contracts](../../contracts.md)。未改数据库、API字段、M2 Provider/报告或M4出题评分；M1/M3仅调整初始定位加载，避免同账户重登覆盖编辑草稿。

- React Router 7.18.4使用浏览器history，页面/课程及来源跳转的note/document/version/chunk/page进入URL。UUID与不完整/非法定位先检查，最终授权仍由后端执行。已带定位的地址刷新恢复，前进后退统一执行已有未保存保护；浏览器整页关闭仍走beforeunload。
- TanStack React Query 5.104.2统一处理JSON GET：同会话、路径和数据代次的在途请求去重；staleTime=0，每次读取重新授权，不落盘。query key只含不透明会话分区，不含令牌。写入成功递增代次/失效，刷新不复用写入前仍在途的旧列表。写入、模型确认均不自动重试；下载Blob不缓存，退出清空。
- 401通过公共入口通知，即便业务组件只显示局部失败也能触发重登。Ant Design 6.6.6使用全站主题/Alert/按需Modal，背景工作区保留并inert；同一用户名只读，不能在保留草稿的对话框中切换账户。登录失败保留窗口，成功更换token并刷新列表，已打开笔记/资料不重新初始化草稿；失败的保存需用户再次点击。缺失原账户名时只能退出，避免把草稿交给新账户。
- 全部工作区及登录恢复对话框按需加载，保留原CSS/SVG/减少动画设置。此次构建主包485.85KB，PDF阅读器434.68KB，未出现500KB警告；这是产物体积，不是首屏耗时或p95达标证据。

## 实际测试

| 命令/范围 | 实际结果 |
|---|---|
| `bash scripts/check.sh` | 101 pytest passed / 15.52秒，1条Starlette/anyio弃用警告；Ruff、临时迁移/ORM漂移、笔记与AI回答SSR安全、PDF.js双页实渲染、10项Vitest、TypeScript/Vite通过 |
| `PYTHONPATH=backend .tools/venv312/bin/python -m pytest -q` | 独立Python3.12.13环境锁依赖安装成功，101 passed / 24.19秒，同一条依赖警告；没有替换当前运行的Python3.11.15环境 |
| `HUSTUDY_E2E_CHROME_CHANNEL=chrome npm run test:e2e --prefix frontend` | 8 passed / 52.2秒，已安装Google Chrome与官方Playwright WebKit各4项，串行、无重试 |
| Safari人工操作（Codex） | 已有会话下查看资料页与备份恢复页，地址随导航变化，分页/处理状态/备份表单可见；未在真实账户执行恢复或删除 |

浏览器测试启动8056 API+worker和5178 Vite，使用TemporaryDirectory中的一次性数据库、文件与测试账号；测试进程结束清理。默认Mock、空远程密钥，不读取或发送用户现有课程。4个场景各在两个引擎执行：

1. 真实API登录→界面建课→上传自制Markdown→worker解析→阅读→课程关键词搜索。
2. 资料版本/chunk深链接→刷新→后退/前进→笔记草稿离开时取消/确认。
3. 注入单次保存401→真实API原账户登录→原笔记草稿保留→确认没有重放→显式保存成功。
4. 注入资料整理保存401→同账户重登→整理草稿保留→显式保存→后台完整备份→实际下载→SHA-256与服务端一致。

401为浏览器测试中的状态注入，不伪称等待真实令牌自然过期；登录、其余读写、解析、备份worker均连接真实隔离API。WebKit自动测试不是用户Safari全功能验收。首次WebKit运行因相对安装目录随进程cwd改变而无法启动，修正绝对路径后上述最终8项全部通过。此前3项/4项Chrome运行是增量证据，不重复累计为测试数。

日志位于本机临时目录：`/tmp/hustudy-web-base-final.log`、`/tmp/hustudy-python312-tests.log`、`/tmp/hustudy-e2e-final.log`；可复现测试源码见[单元测试](../../../frontend/tests/unit/platform.test.ts)、[浏览器测试](../../../frontend/tests/e2e/platform.spec.ts)、[隔离服务](../../../scripts/e2e_server.py)。安装/运行命令见[环境指南](../../setup_guide.md)。测试报告与截图/trace只含测试数据且被Git忽略，不把原始token/用户资料放入文档。

## 剩余验收

本切片不等于全部P0或队长任务Done。LibreOffice成功转换、Office/图片/人工补录/取消恢复等完整浏览器矩阵、容量与真实性能、跨机器恢复、Gitee/CI/正式评审发布和真实用户试用仍待完成。M3独立相对图片路径的知识库ZIP、M2完整真实教学报告、M4正式拆题映射统计/真实拟卷仍属于原模块待办。导航保护允许用户明确放弃内容；整页刷新、崩溃或关闭不会把未保存草稿持久化到浏览器。

最终文档检查：61份当前范围文档、577个本地链接无缺失，统一handoff的16个锚点唯一；git diff --check通过。setup/check脚本bash语法、隔离服务Ruff通过，Python3.12临时迁移/ORM漂移另行通过。最后类型/构建复核主包仍485.85KB；未改动其他成员个人记录或恢复用户已删除的个人报告。
