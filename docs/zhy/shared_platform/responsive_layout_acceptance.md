# 全站响应式布局与统一密度验收

2026-10-15；模块：共享基础层 + M1，队长 zhy 会话由 Codex 辅助实施；本人审阅、其他成员接收待填。任务 PLATFORM-RESPONSIVE-01，需求 CR-PLATFORM-RESPONSIVE-01、NFR-09/10，涉及 FR-06/10/17/25 展示；工作区未提交/合并。

## 输入、输出与范围

用户要求在已有网站上优化所有页面排布，适配电脑/iPad/手机，缩小界面字体、改善美观和操作性。先更新公共 contracts，再实现共享壳层和样式；输入为现有课程/路由/模块组件，输出为同一视觉体系的自适应工作台。无数据库迁移、API/数据结构或模型发送行为变化。M2/M4 内部业务及他人成员个人记录未改，M3 仅接入公共展示容器。

| 区域 | 最终行为 |
|---|---|
| 字号与密度 | 界面基础13px、页面标题20–26px；缩小顶部留白、卡片内边距与装饰，公共控件/配色/图标一致 |
| 电脑 | 固定208px侧栏，中等桌面188px；主体随可用宽度展开，大屏笔记三列；内容上限1520px |
| 平板 | 1100px以下抽屉导航与吸顶入口，保留正文宽度；820/1024px实际触控媒体条件下调整表单和网格 |
| 手机 | 760px以下资料库/笔记列表可折叠且保持挂载；小屏阅读、笔记、AI、试卷、备份、帮助均重排；320px可操作 |
| 触控与键盘 | 按钮/图标热区至少44px，触屏输入16px避免iOS聚焦缩放；抽屉Escape、首尾Tab循环、遮罩关闭、焦点恢复 |
| 可靠导航 | 路由成功后关闭菜单；取消离开保留菜单及草稿；屏宽切回桌面关闭抽屉，草稿继续保留；401沿用原恢复流程 |
| 长内容 | 课程描述3行摘要，整理可读全文；长代码/表格/文档在自身容器滚动，未用body横向裁剪掩盖溢出 |
| 原格式阅读 | 不缩小源文件字体；PPT外框贴合幻灯片比例，手机仍可翻页/缩放/演示；Word阅读页和Citation语义保持独立 |

## 修改位置与模块交接

- 公共：frontend/src/responsive.css、main.tsx、components/WorkspaceNavigation.tsx、CompactLibrary.tsx。
- M1：资料库展示容器、OfficeReader格式标识/预览外框；M3：笔记列表展示容器；课程总览说明摘要。
- 测试：responsive-layout.spec.ts 新增7场景/每引擎；native-preview.spec.ts 扩展390/820/1280px实际可视区、画布截图与外框边界。
- 不读取/变更用户原件或运行库，不调用真实模型，不引入新依赖。受影响 xtc/fzk/gcx 继续使用公共壳层与同一套CSS/控件，不能各自创建第二套导航或覆盖来源语义。成员签收由本人填写。

## 实际执行结果

| 命令/日志 | 实际结果 |
|---|---|
| npm run check --prefix frontend | TypeScript通过；最终构建再次执行tsc |
| npm run test --prefix frontend | 3文件、14项Vitest通过，最终261ms |
| npm run build --prefix frontend | TypeScript/Vite及本地Office构建通过；主入口488.37KB，按需PDF492.59KB；无500KB提示 |
| HUSTUDY_E2E_CHROME_CHANNEL=chrome npm run test:e2e --prefix frontend | 40项通过、3.2分钟、无重试；Chrome/WebKit各20项；日志/tmp/hustudy-responsive-all-e2e.log |
| 上述命令追加 responsive-layout.spec.ts native-preview.spec.ts | 吸顶导航收尾后20项通过、1.5分钟，日志/tmp/hustudy-responsive-final-e2e.log；这是原40项子集，不累加 |
| 上述命令追加 native-preview.spec.ts | PPT外框比例/可视区收尾后6项通过、31.8秒；日志/tmp/hustudy-responsive-office-final.log，不累加 |
| git diff --check | 通过 |

覆盖登录/注册和总览、资料、笔记、AI、试卷、复习、查找、备份、指南；五种尺寸1440×1000、1024×768、820×1180、390×844、320×740，其中1024px及以下启用isMobile/hasTouch，实际命中coarse指针样式。每页检查整页横向溢出/主体范围；小屏逐个检查可见按钮热区。实际API创建临时账户/课程/Markdown/笔记，执行资料打开、折叠、笔记预览、带长代码与表格、搜索资料与笔记、课程整理对话框、帮助展开；草稿取消/确认离开、Tab/Escape/旋转/焦点及吸顶入口另验。

既有全量回归继续覆盖三格式预览/截图、分页/来源、补录撤回、索引/删除隔离、历史定位/前后退、401同账户草稿恢复和完整备份下载hash。原格式收尾测试将iframe滚入可视区后检查实际文字在viewport内并截取画布，已查看手机PPT/Word样式、表格与图片；不将离屏DOM存在当作画布可见证据。

初次响应式14项中13通过，Chrome首个Shift+Tab进入浏览器焦点区导致1项失败；补抽屉首尾Tab循环后通过。构建曾发现Array.at不在当前目标lib，改为数组下标兼容后通过。首次沙箱禁止本地8056监听，获准在隔离服务运行后才计结果；没有将启动失败记为通过。

本轮未改后端，未重新运行pytest/迁移/容量/干净安装。此前116项pytest和其他环境结果仍为历史证据，不标成本轮重跑。Playwright使用临时数据库/文件与Mock环境，原5173/8000服务与用户数据保持。

## 图像证据和边界

下列画布来自本项目自制无个人资料样例：

- [手机PPT直接预览](evidence/responsive_2026_10_15/pptx_mobile.png)
- [手机Word直接预览](evidence/responsive_2026_10_15/docx_mobile.png)

补充WebKit三尺寸截图复验3项22.7秒通过（/tmp/hustudy-responsive-evidence.log，不与40项相加），保留以下自制数据截图：

- [电脑课程总览](evidence/responsive_2026_10_15/desktop_overview.png)
- [iPad尺寸资料阅读](evidence/responsive_2026_10_15/ipad_materials.png)
- [手机知识笔记](evidence/responsive_2026_10_15/phone_notes.png)

其他工作台截图由测试生成，下一次Playwright会覆盖临时输出。检查了桌面总览/AI、平板资料及手机笔记/试卷/PPT/Word等视图；不伪造所有真实设备或每份用户文档人工验收。iPad/iPhone尺寸与触屏媒体是浏览器模拟，尚无实机横竖屏/系统键盘/刘海安全区完整矩阵；TC-24至少5位真实用户试用、Gitee/正式成员签收和发布仍待完成。资料原格式复杂Office版式兼容限制保持，页面美化不等于全部P0完工。
