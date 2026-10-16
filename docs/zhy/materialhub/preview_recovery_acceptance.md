# M1：Office预览恢复与Safari兼容验收

日期2026-10-15。任务M1-PREVIEW-RECOVERY-01，A04/A07/A10，FR-05/06/36/37与NFR-06/07/10。记录者Codex（zhy队长会话辅助）；本人审阅、成员接收待填，工作区未提交/合并。无数据库迁移，不重写M2/M3/M4内部实现。

## 实际问题与修复

用户反馈“为什么无法PDF预览”。Safari当前选中的是PPTX，版本预览失败原因明确为未安装LibreOffice；已通过获准的Homebrew官方cask安装LibreOffice 26.8.1，soffice --version返回26.8.1.1。原始PDF不依赖Office转换器，PPTX/DOCX需要先转换PDF。

进一步实际打开用户课件后，转换成功但Safari页面渲染失败：TypeError指出Map.getOrInsertComputed不存在。此前Node渲染使用legacy，而前端使用modern构建，新版测试WebKit也未暴露本机Safari差异。现显示层与worker统一使用pdfjs-dist 6.4.299的legacy构建；在本机Safari实际观察到第一页图像及可用截图按钮。增加错误详情和“重试打开”，不再只显示无法诊断的通用错误。

还发现原课件146张幻灯片只导出142页。LibreOffice默认跳过隐藏幻灯片，会使后续页号与Citation/截图来源错位。现在显式ExportHiddenSlides=true，输出后核对原幻灯片数与PDF页数；不一致拒绝发布。读取/截图也拒绝旧错位缓存；无截图时允许显式重建，有截图时拒绝静默改变来源并要求人工核对。已对上述无截图旧缓存经M1归属服务发起恢复，原件/版本/Chunk身份不变。最终实际结果在文末补记。

## 输入、输出、接口与异常

- 输入：本人有效版本、已有预览任务、本机可执行Office程序。输出：独立预览任务、有效PDF、可定位页及错误说明；预览失败仍可阅读结构化正文。
- GET /api/v1/material-capabilities需登录，返回原始PDF能力、转换器发现状态、说明和官方安装链接，不返回文件路径或密钥。HUSTUDY_LIBREOFFICE_PATH可指定绝对路径，默认PATH/macOS标准位置；不经过shell执行。
- POST /api/v1/versions/{id}/preview-jobs是显式恢复命令。活跃任务返回同一条202；失败/取消复用原任务与尝试上限；已有有效预览409提示直接打开。无转换器拒绝新增Office任务，缺文件404、不支持的文本格式422、越权或删除404。
- 转换在worker执行，独立临时目录/profile、60秒超时、100MiB输出/2000页上限，检查可读PDF后经FileStorage原子发布。超时、退出失败、空或坏PDF不会发布，安全提示不回传原始stderr。
- 阅读页显示原始PDF与课件转换的区别、环境检查、原版本重试，不要求重新上传。PDF阅读器可重试打开，截图仅在成功绘制当前版本/页后启用。

公共权威定义见[contracts](../../contracts.md)和[API](../../api.md)，个人文档只记实现证据。

## 实际验收

| 命令/场景 | 结果 |
|---|---|
| `bash scripts/check.sh` | 110 pytest passed / 15.47秒，1条Starlette/anyio弃用警告；Ruff、临时迁移/ORM漂移、安全Markdown/AI显示、PDF.js双页实渲染、10项Vitest、TypeScript/Vite全部通过 |
| `HUSTUDY_E2E_CHROME_CHANNEL=chrome npm run test:e2e --prefix frontend` | 最终14 passed / 约1.5分钟，Chrome与WebKit各7项；包括原先4条共享闭环及新增PDF/PPTX/DOCX真实预览、截图与回源 |
| 独立Python3.12 | `pytest`选定preview_recovery/storage_contract/preview_assets，17 passed / 3.40秒，1条相同依赖警告；本次未再次执行3.12全量，之前101项为历史结果 |
| 9项新增后端场景 | 能力鉴权/路径隐藏/可执行检查；缺依赖恢复/重复点击/预算/归属/删除；扫描PDF独立预览/文本格式拒绝；转换超时/退出/空/坏输出；有效PDF原子发布；旧错位预览拒绝/有截图不重定向 |
| 兼容与隐藏页浏览器场景 | 初始化时移除Map/WeakMap的getOrInsertComputed来复现实际Safari缺失；使用含隐藏第二页的自制PPTX，真实转换后可翻第二页、两页图像不同；PDF/DOCX也实际截图并核对版本/页号/locator类型和回源 |

普通pytest通过不存在的转换器配置维持确定性，不依赖本机安装或真实模型；浏览器测试另启动8056 API+worker、5178 Vite、一次性账号/数据库/文件，使用已安装Office真实转换。无远程模型调用，不把用户课程加入自动样例。首次新增测试因多个“下一页”同名定位失败，改为PDF region内定位后通过；14项最终证据包含后来legacy和隐藏页修复，不能沿用早期modern构建的通过结果冒记。

日志：`/tmp/hustudy-preview-recovery-final.log`、`/tmp/hustudy-preview-compat-e2e.log`、`/tmp/hustudy-preview-python312-final.log`。源码：[后端风险测试](../../../backend/tests/test_preview_recovery.py)、[浏览器预览测试](../../../frontend/tests/e2e/material-preview.spec.ts)、[自制样例生成](../../../scripts/create_preview_fixtures.py)。产物主包485.98KB、按需PDF阅读器492.59KB，无500KB构建提示；不是加载时间或容量性能达标证明。

## 尚未完成的关口

本切片解决预览环境/兼容/页号的实际缺口，不等于全部M1/P0验收。复杂Office排版与字体保真、转换超时的大课件、既有错误截图的人工校正、完整人工补录/取消恢复交互、容量/p95、干净机器/跨机器恢复、人类评审与发布仍按当前任务表继续。M1关键词搜索前50条限制仍是后续独立切片，本轮因用户当前预览故障优先处理，未把分页记为完成。


## 现有课件缓存的最终结果

经M1服务重建后，数据库只读复核为SUCCEEDED、错误为空；PDF146页/原PPT146张一致，原件/版本/Chunk未改。本机Safari在兼容修复后已实际显示原课件第一页；本次后续新标签页因原会话过期停留同账户重登，未获取或填写用户密码，未把最终146页版本的Safari再打开写成已验收。自动双引擎的隐藏页/截图回源另有上述通过证据，用户重登即可在当前阅读区打开重建结果。
