# 全站外观与布局（2026-10-22）

PLATFORM-APPEARANCE-06，Codex辅助zhy。用户明确要求广泛参考美观网站并实现主题色/整洁排布，先记录[契约](../../contracts.md#platform-appearance-06)、[交接](../../../collaboration/handoff.md#h-20261022-zhy-007)、[11类官方设计研究](appearance_research.md)再实现；保留已有工作，无后端/API/schema/迁移/依赖变化，不复制商业源码/图标/字体，不调用真实模型或操作日常数据。

## 已实现的体验

- 右上角「外观」原地打开原生弹窗。六组预设色+自定#RRGGBB、云白/暖纸/柔雾三种明亮页面基调、浅/深导航、舒适/紧凑密度和舒展/聚焦宽度，立即应用、可恢复默认；手机也可重置，关闭回触发点。
- 自定色保留原色作装饰，主按钮白字/主题链接/选中小字以线性相对亮度派生至少4.5:1计算配色；六预设及白/亮黄/荧光绿等极端色通过算法测试。不将这些角色测试当全站WCAG认证，不把“深色导航”冒称完整深色模式。
- 根级设备偏好提供共享语义令牌，Ant Design同步更新；14份既有样式中的常用前景/强调/背景/边框角色复用令牌，资料选中、片段定位、AI/题库主动作及笔记链接联动。成功/错误/警告、学科公式显式颜色、图片和文件原页不重染，不用全局反色/缩放。
- 默认浅导航、统一主次按钮/边框、轻量阴影、柔和首页、系统字体和清晰字级；面板/行/栅格使用有界间距，大屏可聚焦到1240px，舒展上限1560px；手机保持44px触控与16px文本输入，沿系统reduced-motion。
- 切换只改变样式，原笔记编辑DOM节点/草稿保持，不跳页、不请求模型、不自动保存学习内容。阅读器原有字号、原文版本/引用和考试状态不重置。
- `hustudy-appearance:v1`只存版本和六个白名单偏好字段，2KiB上限，无账户/内容/凭据。读取损坏记录回默认但不写；显式修改才持久化，失败保留本次样式并明确未保存，允许重试；storage事件跨窗口校验同步且不回写。设备级偏好登录/退出后沿用，不随账户备份或跨设备同步。

## 实际验证

当前25文件154项前端单元测试、TypeScript/生产构建、安全Markdown/AI显示通过。首轮18项Chrome/WebKit专项全部通过（1.5分钟），覆盖六色、实际样式、刷新/四模块、极浅/非法自定色、导航/基调/密度/宽度、编辑节点与草稿、配额/损坏/多窗口同步、320/390/820/1440布局和焦点。截图审阅后补齐少数资料选中框残留旧色，66项Chrome/WebKit扩大回归全部通过（6.2分钟），涵盖五尺寸全站操作、关键配色、减少动效、完整学习闭环、书签/版本对照与401恢复。最后收紧导航文字对齐、兼容共享中性底色别名和触屏紧凑模式，12项最终定向复验全部通过（1.3分钟），含新增两引擎触控设备场景；重复场景不累加。

最后重新运行154项单元与生产构建均通过；Ruff、Markdown/AI安全显示及PDF.js实际渲染通过。无新增后端变更，未把历史后端全量结果记作本轮重跑。5173开发服务仍监听；截图已检查桌面/窄屏/实际主题联动，仅保存本机忽略目录`frontend/local_only/appearance-20261022/`。构建入口168.52kB（gzip54.13kB），没有500kB块提示；体积不代表实测加载速度。

复验入口：

```sh
npm test --prefix frontend
npm run check --prefix frontend
npm run build --prefix frontend
node scripts/verify_markdown.mjs
HUSTUDY_E2E_CHROME_CHANNEL=chrome npm run test:e2e --prefix frontend -- appearance.spec.ts responsive-layout.spec.ts learning-loop.spec.ts reading-tools.spec.ts --project=webkit --project=chromium
HUSTUDY_E2E_CHROME_CHANNEL=chrome npm run test:e2e --prefix frontend -- appearance.spec.ts --grep '六预设|布局|紧凑模式' --project=webkit --project=chromium
```

测试使用8056/5178临时服务、自制课程/资料和模拟失败；截图仅本机忽略目录。真人偏好/长期阅读舒适度、真实复杂课件/平台实机、全站无障碍审计与团队接收另列，不虚构满意度或全部P0完成。
