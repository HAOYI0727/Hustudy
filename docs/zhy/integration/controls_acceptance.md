# 共享控件与卡片细化（2026-10-23）

2026-10-23 收尾：本页保留各阶段实际过程；最新全站434场景首轮及82项修复复验、163单元/443后端与当前关口统一见[全站功能核查](project_review_2026_10_23.md)。

PLATFORM-CONTROLS-07，10月22日先记录契约，跨日至23日完成实现与验证。Codex辅助zhy，依据用户对按钮、选项展开、适中字级、卡片阴影与整齐排布的要求实施。[契约](../../contracts.md#platform-controls-07)与[交接](../../../collaboration/handoff.md#h-20261022-zhy-008)。保留已有未提交工作，本轮仅共享前端与测试，无新依赖、API、迁移，不调用真实模型或操作日常学习数据。

## 实现与使用

- 主次、文字、图标、危险、禁用、已选按钮统一圆角、间距、轻量阴影和悬浮/按下反馈；题库和AI模式采用整齐分段栏。侧栏底部动作与导航左对齐，主题色沿用既有外观偏好。
- 展示标题收敛到20–31px层级，统计数字22–26px；桌面普通按钮12px。用户笔记正文、原文、公式、Office/PDF与阅读器自选字号保持。手机/粗指针按钮与选择器保留44px操作高度，选择器16px文本。
- 面板和学习卡片使用静态柔和阴影；鼠标悬浮交互卡片上移3px并增强阴影，阅读/编辑面板只改变阴影，不整体移动。系统减少动效时取消位移。课程学习栅格等高，工具折叠栏统一箭头、间距与展开态。
- 桌面鼠标/细指针且宽度至少768px，普通单选框展开主题浮层：当前项勾选、悬浮高亮、禁用分组、长文本换行、内部滚动、边界约束与向上翻转。短列表有足够空间时完整展示。支持上下/Home/End、文字快速定位、Enter/空格确认、Escape取消、Tab离开；同值确认不重复触发业务回调。
- 原生select仍为唯一值、label/name/必填/禁用及表单来源。增强层不替换业务DOM，不复制React业务状态。浮层用浏览器top layer并挂到所属原生dialog内；Escape先关选项，再关闭原弹窗。选项变化/禁用/移除、实际祖先滚动、窗口/路由变化或401关闭旧浮层，不写入迟到选择；恢复原ARIA属性，401不抢登录焦点。
- 手机/触控、多选/列表框、显式data-native-select、Popover能力不足或可用空间不足时使用原生选择。可继续通过原生selectOption自动化；没有额外偏好存储、后台调用或学习数据写入。

技术依据仅参考[MDN Popover使用指南](https://developer.mozilla.org/en-US/docs/Web/API/Popover_API/Using)与[MDN select元素](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/select)，独立实现，未复制第三方源码/图片/字体。

## 实际验证

26文件158项前端单元测试通过，包括四项新增选项导航/禁用/文字定位/视口定位逻辑测试；短列表高度加入既有定位测试。TypeScript/生产构建、Markdown/AI安全显示、PDF.js实际渲染与Ruff通过。构建入口176.56kB（gzip56.59kB），没有500kB分块提示；体积不代表加载速度实测。

首轮18项双引擎专项中8通过、10失败，发现浮层与原控件同名导致定位歧义、首次增强加载和延迟滚动关闭问题，已改为独立选项名称、同步加载增强层并核对实际滚动位置；同时修正隔离夹具的页面就绪与新版本内容。修正后Chrome/WebKit共18项全部通过（1.3分钟），覆盖实际资料筛选回调、原生程序化选择、键盘/禁用分组/滚动、同值幂等、弹窗内菜单、变化/禁用/移除/滚动失效、原生降级、后台401及320/820/1440布局/阴影/减少动效。

07扩大回归86项中82通过、4失败（7.2分钟），失败均为手机AI模式按钮被38px规则覆盖，已补44px触控规则；同时调整中窄资料侧栏筛选的自适应列宽，避免选项文字只露一两字。验证过程中用户追加「纯白模块缺设计感」反馈，继续先记录[PLATFORM-COLOR-STUDIO-08契约](../../contracts.md#platform-color-studio-08)并实施彩色模块。最终综合结果在[彩色模块报告](color_studio_acceptance.md)记录，不把中间失败记为全部通过。所有测试使用8056/5178临时服务与隔离数据库、自制资料，不操作5173日常账户。截图仅保存在本机忽略目录。

```sh
npm run test --prefix frontend
npm run build --prefix frontend
node scripts/verify_markdown.mjs
node scripts/verify_pdf.mjs
.venv/bin/ruff check backend/app backend/tests backend/migrations
HUSTUDY_E2E_CHROME_CHANNEL=chrome npm run test:e2e --prefix frontend -- controls.spec.ts appearance.spec.ts responsive-layout.spec.ts learning-loop.spec.ts reading-tools.spec.ts --project=webkit --project=chromium
```

无后端源码变化，未把历史后端全量测试冒称本轮重跑。自动浏览器WebKit不等同Safari/iPhone实机；Windows触控、真实读屏器、复杂课件和长期舒适度仍需真人复验，团队接收由本人填写，不将本轮视觉增量记为全部P0或全站无障碍认证完成。
