# 模块配色与彩色卡片（2026-10-23）

后续统一色调12已覆盖08固定五模块色，当前样式与验证见[统一主色](unified_tone_acceptance.md)。本页保留此前阶段过程。

2026-10-23 收尾：本页保留各阶段实际过程；最新全站434场景首轮及82项修复复验、163单元/443后端与当前关口统一见[全站功能核查](project_review_2026_10_23.md)。

PLATFORM-COLOR-STUDIO-08，Codex辅助zhy。用户在07控件迭代中追加反馈：纯白卡片与黑字缺少设计感，需要色彩更丰富的模块与按钮。先记录[增量契约](../../contracts.md#platform-color-studio-08)与[交接](../../../collaboration/handoff.md#h-20261023-zhy-009)，延续[07实际实现和测试过程](controls_acceptance.md)，保留全部既有工作。

## 最终设计

- 模块配色为资料蓝`#236e9b`、AI紫`#7351b5`、笔记青绿`#227865`、题库琥珀`#9c6023`、复习莓粉`#a84468`。云白/暖纸/柔雾分别派生色底、浅底、边框与可读文字，模块身份稳定，不随个人主题改成同一种颜色。个人主题继续控制主按钮、焦点和当前选中；状态成功/警告/错误、掌握状态和原文颜色保持原语义。
- 首页四张学习卡片有各自渐变色底、实色图标、淡几何图标水印、步骤徽标、实色按钮和圆形箭头；数据卡片延续模块色并配几何圆环。课程卡片使用稳定三色分配、顶端色条与实色课程首字图标。装饰只表达功能身份，不是假学习统计/进度图。
- 首页主视觉增加主题光晕、实色品牌中心及三种来源卡片色；下一步提示、笔记/复习侧栏、知识点学习入口形成不同层次。使用项目现有原创SVG图标与CSS几何，不下载第三方图片/字体或复制商业代码。
- 模块标题采用色底/边线/标牌/插图；侧栏不同模块有彩色图标底。笔记工具头与视图栏采用青绿，AI模式/提示采用紫色，题库模式采用琥珀，资料上传与目录采用蓝色，复习目标采用莓粉。知识点页的原文、笔记、复盘延续对应身份。
- 主按钮增加细微明暗层次和阴影，次按钮跟随当前模块浅底和边线；危险/已选/禁用继续保留行为与状态。新增图标不改变按钮名称/回调。字号与07一致，交互卡片轻浮，编辑面板不位移；减少动效时取消位移。
- 保留原select/业务DOM、编辑与学习数据。中窄资料侧栏按可用宽度换列，避免筛选文字过窄；手机/粗指针模式栏至少44px。笔记正文、考试题干、阅读原文与Office/PDF原页仍保留清爽阅读底色和用户字号。

## 实际验证

26文件159项前端单元通过；新增模块色跨三底色的按钮白字、模块文字和正文计算对比度验证，不改变六字段设备偏好，不将局部算法检查当全站无障碍认证。TypeScript/生产构建、Markdown/AI安全显示、PDF.js渲染与Ruff通过。入口176.90kB（gzip56.74kB），无500kB分块提示，未把体积当实测加载性能。

彩色设计阶段92项Chrome/WebKit综合回归全部通过（8.4分钟），覆盖主题/触控/五尺寸、下拉与失效、完整学习闭环、书签和版本对照。用户随后追加字体及前后端扩展要求，继续按[字体契约](../../contracts.md#platform-typography-09)与[学习记录契约](../../contracts.md#platform-records-10)实施，最后字体/彩色专项8项双引擎全部通过（1.0分钟）；最终综合结果在[本轮总验收](records_typography_acceptance.md)记录，重复场景不相加。

```sh
npm run test --prefix frontend
npm run build --prefix frontend
node scripts/verify_markdown.mjs
node scripts/verify_pdf.mjs
.venv/bin/ruff check backend/app backend/tests backend/migrations
HUSTUDY_E2E_CHROME_CHANNEL=chrome npm run test:e2e --prefix frontend -- color-studio.spec.ts controls.spec.ts appearance.spec.ts responsive-layout.spec.ts learning-loop.spec.ts reading-tools.spec.ts --project=webkit --project=chromium
```

测试仅8056/5178隔离库、自制资料和临时账户；不操作5173日常内容，不触发真实模型，不新增依赖/API/迁移/偏好字段。无后端变更，未冒称重跑历史后端全量测试；保留已有未提交内容。本轮未执行Git提交/推送。

正式团队接收、真实Safari/iPhone/Windows及读屏器、长期视觉舒适度与复杂课程资料仍需真人复验，自动WebKit不冒充Safari实机或真人签收，不把本轮视觉增量记为全部P0完成。
