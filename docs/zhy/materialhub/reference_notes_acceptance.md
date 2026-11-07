# 原文关联笔记检索与阅读连续性

2026-10-24，M1-REFERENCE-NOTES-28，Codex辅助zhy。[实施前契约28](../../contracts.md#m1-reference-notes-28)、[API](../../api.md)和[交接029](../../../collaboration/handoff.md#h-20261024-zhy-029)。本轮为M1/共享层集成M3的只读接口，不改变fzk业务归属、笔记正文/revision/课程、原引用或保存协议。

## 体验路径

1. 打开一份已有引用笔记的资料。在下方“引用这份原文的笔记”按标题查找、选择原文片段、翻页；同一笔记只出现一次，徽标为当前范围的有效引用条数。
2. 打开“阅读笔记”，输入一段尚未保存的理解，切换“关联笔记”。用同样的检索卡片找到笔记，明确点击后才读取正文。
3. 点击“在完整编辑器打开”，取消离开后切回“写下理解”，核对原输入仍在；保存阅读笔记后可以进完整编辑器继续补充，再沿原引用回到原版本片段。
4. 在隔离课程删除笔记或撤回人工来源，明确刷新核对列表。断网或登录过期后依提示重试，不能把失败当作没有关联。

卡片使用统一主色浅底/边框、引用徽标/更新时间、轻阴影与细指针悬浮；桌面双列、窄屏单列，列表与摘录高度有界。引用预览不等于完整笔记或完整引用；本人未归课程与既有其他课程关系会标注并保留原归属，不自动移到当前课程。

## 后端与安全边界

新GET reference-notes复用M3 Citation/Note元数据与M1有效版本/逐字引用核验，SQL按笔记分区计数及最近有效样本，按笔记更新时间/id稳定分页。标题为字面子串，版本/片段严格固定；样本最多180个Unicode字符，不拿它新建引用。总量与本页来自同一read snapshot，列表每页6篇；服务端最高50。

旧GET references保持正常列表字段与顺序，去掉select(Citation, Note)带来的Note.content等无用列读取，改显式投影并排除假引用/撤回人工来源。新旧接口均不查询Note.content，不返回存储路径或其他账户内容。隔离测试同时捕获新旧两请求SQL，最多10条SELECT（含认证、授权和分页），无逐笔记查询或学习写入。

共用ReferenceNotes组件用于底部与侧栏，只有关联页激活才读取侧栏列表；正文沿原NotePreview按需获取，可取消直接读取，不重放401。切回写作保留表单DOM，隐藏/关闭取消旧列表与正文，迟到不覆盖。响应核对课程/资料/版本/片段，错误仅局部重试；仍由原离开保护控制跨页/跨版本，不自动生成笔记、审阅或改掌握。

## 自动验证记录

首轮接口专项8通过/2失败（4.55秒）：新测试构造缺quote_hash、人工补录parent传对象而非UUID；仅修正测试数据/调用后，10项全部通过（4.38秒）。最终全量478后端通过/2私有样例跳过/5既有弃用警告（89.79秒），Ruff与临时迁移升级/模型漂移检查通过。覆盖真实分页/同笔记多引用/相同更新时间稳定排序、字面%_标题、越权与伪造引用、未归课程、回收站/资料删除、新版不继承、180字符表情、人工历史确认与撤回，旧列表兼容。

最终187前端单元/31文件通过（3.21秒），类型与生产构建通过（Vite736毫秒），Markdown安全渲染/PDF.js两页图文与预算检查通过。新增10项Chrome/WebKit先行全部通过（1.1分钟），包含1440/390/320实际引用→预览→草稿取消→保存→完整编辑→回原片段、14篇三页与去重、失败/范围不一致、隐藏迟到与401不自动重放正文。已查看桌面/手机卡片截图。

扩大回归84项首轮82通过/2失败（8.1分钟），两引擎均暴露无关联笔记时新空态占位过高，80页自制PPT阅读区1582.17px超过既有1500px上限。修正为初始无引用/加载时简短提示，显式可展开；有笔记或使用过筛选后保持控件，错误仍单独呈现，不放宽高度门槛。最终52项专项全部通过（4.9分钟），两引擎阅读区均降至1309.25px，整页2425→2152px；额外验证新版0关联提示/展开、首篇笔记0→1与原输入保护。

84个不同双引擎场景经修正复验通过；新增10项和最终52项属于扩大回归子集，不重复累加。范围含原笔记引用/离开/未知保存/恢复、AI侧栏、长PPT与文本末页/搜索、真实四模块学习闭环/备份、五尺寸/触控/旋转/焦点/减少动效以及手册安全下载。user.md与121项人工清单同步，保持待本人勾选。截图在忽略的Playwright目录，不覆盖成员历史证据；80页样例不冒充全部复杂课件/真实设备。

## 命令与临时日志

```bash
PYTHONPATH=backend .venv/bin/python -m pytest backend/tests/integration/test_reference_notes.py backend/tests/integration/test_source_learning.py -q
PYTHONPATH=backend .venv/bin/python -m pytest -q
.venv/bin/ruff check backend/app backend/tests backend/migrations
PYTHONPATH=backend .venv/bin/python scripts/verify_migrations.py
npm test --prefix frontend
npm run build --prefix frontend
node scripts/verify_markdown.mjs
node scripts/verify_pdf.mjs
HUSTUDY_E2E_CHROME_CHANNEL=chrome npm run test:e2e --prefix frontend -- reference-notes.spec.ts
HUSTUDY_E2E_CHROME_CHANNEL=chrome npm run test:e2e --prefix frontend -- reference-notes.spec.ts continuity-workspace.spec.ts note-citations.spec.ts reading-layout.spec.ts reader-ai.spec.ts user-manual.spec.ts learning-loop.spec.ts responsive-layout.spec.ts
HUSTUDY_E2E_CHROME_CHANNEL=chrome npm run test:e2e --prefix frontend -- reference-notes.spec.ts reading-layout.spec.ts continuity-workspace.spec.ts user-manual.spec.ts responsive-layout.spec.ts
```

本机临时日志前缀`/private/tmp/hustudy-reference-notes-`：`target.log`/`target-final.log`、`api.log`、`unit-final.log`、`build-final.log`、`migrations.log`、`e2e.log`、`regression.log`、`final-e2e.log`及`height-before.json`。Playwright按正则选文件，扩大回归也包括manual-learning-loop；实际数量以日志为准。临时日志/截图不是永久交付证据。

所有业务验证为隔离数据库/临时账号/自制资料和固定演示或替身，未改日常test资料/笔记，未调用真实模型，无新表/迁移/依赖。真实复杂课件、学科教学质量、真人Safari/iPhone/Windows与正式40任务/成员签收仍待本人。
