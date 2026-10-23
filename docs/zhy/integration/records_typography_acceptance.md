# 字体、学习记录与前后端闭环（2026-10-23）

2026-10-23 收尾：本页保留各阶段实际过程；最新全站434场景首轮及82项修复复验、163单元/443后端与当前关口统一见[全站功能核查](project_review_2026_10_23.md)。

Codex辅助zhy，承接[共享控件07](controls_acceptance.md)与[彩色模块08](color_studio_acceptance.md)。用户依次追加Times New Roman/中文宋黑楷搭配，以及进一步完善前后端与学习闭环；先记录[PLATFORM-TYPOGRAPHY-09](../../contracts.md#platform-typography-09)/[PLATFORM-RECORDS-10](../../contracts.md#platform-records-10)、API与[字体交接](../../../collaboration/handoff.md#h-20261023-zhy-010)/[记录交接](../../../collaboration/handoff.md#h-20261023-zhy-011)再实现。保留全部既有未提交工作。

## 字体与排版

- 英文与数字优先Times New Roman，Times作为后备；界面标题/导航/按钮的中文优先黑体族，说明、资料提取正文与Markdown段落采用宋体族，少量学习寄语/反思提示采用楷体族并回退宋体。按元素角色应用，不拆字/插入额外DOM，不影响复制/查找/选区。
- 只引用系统字体，已只读确认本机存在Times New Roman、宋体和黑体相关系统文件；未复制系统字体、未引入外部字体请求或新依赖。楷体及其他平台是否安装具体字体由设备决定，有序后备正常显示；计算字体族测试不能当每台设备实际字形保证。
- 全站展示标题20–31px层级，控件/说明保持12–14px；登录宣传标题也收敛到最大31px、表单标题22px。手机触控与选择器仍44px/16px。正文与用户阅读字号保持，源码编辑器/代码、KaTeX、PDF/Office原格式与图片不重染/换字体；Ant Design使用同一UI字体令牌。六字段外观偏好不变。

## 课程学习记录与闭环

- 首页「最近的学习足迹 → 全部学习记录」按需打开原生弹窗；新增`GET /api/v1/courses/{course_id}/learning-records`，四域分别提供只读元数据SELECT，由共享层在同一read snapshot内汇总。
- 资料、笔记、资料问答、学习报告、练习作答、错题复盘可按类型和标题筛选，每页12条、服务端上限50条。按UTC更新时间降序、类型/UUID稳定排序；总数和各类型数量来自SQL计数，不把首页最近6条当全部。标题搜索把百分号、下划线与SQL样式字符串按字面处理，参数长度/分页范围经验证。
- 资料项含查询时的版本UUID，回跳原版本；笔记、已保存问答/报告、已有作答与错题按原ID打开，使用既有React Router，不整页重载、不创建新笔记/试卷/作答或模型任务。列表是当前可用资源汇总，不是不可变操作日志，不代表掌握度或完整历史事件。
- 逐域归属与生命周期过滤：有效material资料及本人版本、未入回收站笔记、非停用AI候选、双归属试卷/作答、未移出错题。课程/账户隔离；元数据列表不返笔记/AI正文、题干/标准答案/作答、路径或Provider配置；打开目标时原接口重验权限和来源。
- 类型沿08模块色系，卡片按原功能着色；支持真正分页、加载/空态/错误和显式重试。关闭/课程变化/认证过期取消读取且拒绝迟到结果，401让出重登；筛选输入保留。首页入口即使暂无记录也可使用，窄屏标题/按钮可换行。
- 首轮记录专项12项中8通过、4失败，均为WebKit关闭首次懒加载弹窗后焦点未返回入口。根因为Safari鼠标点击不自动聚焦且弹窗尚未挂载，已在入口点击时显式聚焦真实按钮，保持按需加载。入口显式聚焦的修复在全分界面18项双引擎专项中通过，包含原12项记录场景；后续唯一共享入口与草稿保护也通过，不将重复场景相加。

## 已实际完成的验证

443项后端全量通过、2项私有样本跳过（158.98秒）；没有把跳过或模拟样本冒充真人/实机。159项前端单元、TypeScript/生产构建、Ruff、Markdown/AI安全显示与PDF.js实际渲染通过。新增4项API测试覆盖六类型、权限、无正文/答案/写操作、真实分页与同时间排序、字面搜索、删除/回收站/停用/题库范围及跨归属练习链。

彩色模块阶段92项双引擎综合通过（8.4分钟），随后字体/彩色专项8项通过（1.0分钟）；这些有重复，不相加。曾启动106项综合回归，期间用户追加所有分界面与共享记录入口要求，因此主动中止旧切片校验：41项通过、1项受中止影响、64项未运行（4.9分钟），不能记为106通过或将中止项当业务失败。继续按[PLATFORM-WORKSPACE-POLISH-11](../../contracts.md#platform-workspace-polish-11)覆盖分界面与单一共享弹窗；最终证据见[全分界面报告](all_workspaces_acceptance.md)。

09/10阶段构建入口177.36kB（gzip56.88kB），无500kB分块提示；体积不当作加载速度实测。日常5173服务仍监听，8000公开OpenAPI已只读确认加载新接口，不读取日常账户或模型配置，不用日常数据测试，不需要手动重启服务。

```sh
PYTHONPATH=backend .venv/bin/python -m pytest -q
npm run test --prefix frontend
npm run build --prefix frontend
.venv/bin/ruff check backend/app backend/tests backend/migrations
node scripts/verify_markdown.mjs
node scripts/verify_pdf.mjs
HUSTUDY_E2E_CHROME_CHANNEL=chrome npm run test:e2e --prefix frontend -- color-studio.spec.ts controls.spec.ts appearance.spec.ts responsive-layout.spec.ts learning-loop.spec.ts reading-tools.spec.ts learning-records.spec.ts --project=webkit --project=chromium
```

浏览器仅8056/5178临时服务、隔离库、自制资料/账户和模拟异常，零真实模型调用；截图保存在本机忽略目录。无新领域实体/迁移/依赖/偏好字段，不改既有题目/作答/成绩或恢复停用功能。本轮未提交/推送。

正式成员接收、Safari/iPhone/Windows实机与读屏器、长期阅读体验/真实课程质量仍待真人复验；自动WebKit不当作Safari实机，不将本轮增量记为全P0/40任务或无障碍认证全部完成。
