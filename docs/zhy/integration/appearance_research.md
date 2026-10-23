# 全站视觉与主题研究（2026-10-22）

PLATFORM-APPEARANCE-06，按用户要求广泛搜索后采用官方一手页面。以下为设计原则研究与本项目独立取舍；不复制商业源码、图片、图标或字体，不引入主题库。没有将营销页的动画搬入高密度学习操作。

| 参考 | 页面与实际观察 | Hustudy采用 |
| --- | --- | --- |
| Linear | [UI重设计](https://linear.app/now/how-we-redesigned-the-linear-ui)、[更平静的界面](https://linear.app/now/behind-the-latest-design-refresh)：导航、表头、面板层级和减少噪声 | 浅色主导航、弱化非当前项、统一边框/层级/密度；深色导航可选 |
| Notion | [账户与外观偏好](https://www.notion.com/help/account-settings)：集中外观设置 | 独立面板即时切换；本轮提供三种明亮基调，不冒称系统深色模式 |
| Todoist | [主题选择](https://www.todoist.com/help/account-and-billing/account/change-your-todoist-color-theme-zD0N5K)：预设主题与设备同步选项 | 六种预设色与明确的“仅此浏览器”范围，不假称云同步 |
| Raycast | [Themes](https://manual.raycast.com/themes)：即时预览与自定色 | 页面内预览、自定十六进制主题色、恢复默认，不引入外部主题执行 |
| Obsidian | [Themes](https://obsidian.md/help/themes)：集中管理并可回默认 | 统一外观入口与恢复默认；不安装任意CSS主题 |
| Radix | [Color](https://www.radix-ui.com/themes/docs/theme/color)、[色阶语义](https://www.radix-ui.com/colors/docs/palette-composition/understanding-the-scale)：强调色、背景、边框和前景分工 | 自制语义令牌与可读颜色派生，不只替换一个按钮 |
| Stripe | [Accessible color systems](https://stripe.com/blog/accessible-color-systems)：颜色需兼顾区分、对比度与一致视觉权重 | 对实际主按钮/选中/链接配色计算可读前景，错误/成功保留语义 |
| Vercel Geist | [Design System](https://vercel.com/geist/introduction)：统一组件、色彩/字级/栅格 | 整齐的边框和内容对齐，主次动作层级；不引入品牌字体或资源 |
| Atlassian | [Spacing](https://atlassian.design/foundations/spacing/)、[Typography](https://atlassian.design/foundations/typography)：8px基础与可读性/层级 | 8/16/24节奏、有界间距、舒适/紧凑密度、系统字级 |
| IBM Carbon | [2x Grid](https://www.carbondesignsystem.com/building-blocks/foundations/2x-grid/overview)：8px微单元与断点栅格 | 统一横向对齐与响应式宽度，不强制移动端桌面列数 |
| Microsoft Fluent 2 | [Typography](https://fluent2.microsoft.design/typography)：清晰文字层级、原生字体栈 | 中文系统字体，不下载远程字体；工作区正文与注释分层 |
| W3C | [Contrast Minimum](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)：普通文字4.5:1、大字3:1等条件 | 新主题主按钮白字/主题链接小字以4.5:1为算法测试门槛；不宣称全站WCAG认证 |

Craft官网抓取超时、Material 3页面仅返回JavaScript要求，因此不把它们记作已完整审阅的实现依据。广泛参考不等于混搭所有风格：本项目选“安静、清晰、适合长时间学习”的共享工作台方向，保留四模块的信息结构、来源准确性与草稿保护。
