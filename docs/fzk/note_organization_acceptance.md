# M3笔记整理、导入与编辑器验收

后续反馈：2026-10-18，用户明确确认下方本人复验1–5全部通过。继续提出布局和拖动改进，由[笔记工作区切片](note_workspace_acceptance.md)推进；本文保留当时界面/命令/截图证据，新入口以工作区说明为准，团队整合未代签。

2026-10-18，Codex辅助fzk。M3-ORGANIZE-IMPORT-EDITOR-01，C01/C02/C07/C08/C09/C10、FR-09/10/11/14/37。用户明确确认上一轮引用管理复验2/3/4正常，本轮按新要求实现文件夹、批量导入与标签、分类建议及编辑器；工作区未提交/推送，团队集成与本轮本人验收不代签。

## 已实现的使用流程

1. **文件夹**：笔记列表左侧可新建根文件夹和子文件夹，最多6级；“编辑文件夹”修改名称/父目录。选择父文件夹同时显示后代笔记，“全部笔记”“未归档”保留独立入口。编辑区“所在文件夹”单篇移动，列表勾选后可批量移动。删除仅允许空文件夹，笔记UUID和双链不变。
2. **批量Markdown导入**：展开“导入 Markdown”，指定文件夹（可选未归档）、统一标签，再选择多份文件并开始。每批20份、每份≤2MiB，UTF-8或UTF-8 BOM，支持.md/.markdown；标题使用文件名去扩展名，不被正文第一个标题覆盖。同名文件分别保存。成功/失败逐项显示，显式重试未完成文件沿用原请求UUID，响应丢失也不重复建笔记。
3. **批量标签与移动**：列表勾选或“选择当前筛选结果”，一次1–200篇，可添加/移除多个标签，或指定移动目标。“管理当前课程的全部标签”可改名/合并到现有标签、删除标记；不删除正文。该管理区覆盖当前课程，明确不受列表筛选影响。冲突/越权/超过12标签时整批拒绝，先刷新列表后重选。
4. **分类建议**：展开“推荐归类 · 本地规则”，选择文件夹，查看未归档候选与“共同标签/标题包含”依据，勾选确认后移动。没有足够匹配时明确为空；可先移入一篇代表笔记。不会自动移动、联网或发送笔记正文，不称为AI生成。
5. **导出目录**：仅包含选中笔记与其引用图片；保留文件夹层级，未归档笔记在ZIP根目录，空文件夹不单独输出。所有图片仍集中在根images目录，共用图片去重；层级中的图片和选中笔记间双链转换为相对路径，未选择目标保留说明。文件夹和文件的非法字符/同名/保留名安全处理，顶层名为images的用户文件夹自动加序号。需完整解压后阅读。
6. **Markdown编辑器**：选区加粗/斜体/删除线、标题、任务/有序/无序列表、引用块、链接、行内/块代码、表格、分隔线；Ctrl/Cmd+B/I/K、S保存、Z撤销、Shift+Z或Y重做。列表回车续写，空列表项回车退出，Tab/Shift+Tab缩进。分屏预览（手机上下排列）、标题大纲、正文查找、专注编辑及Esc退出。专注时隐藏整理工具，保留标题/正文/格式/预览；首次自动保存不丢焦点或撤销历史，切换笔记清空历史。安全预览仍禁止执行HTML脚本和自动加载外部图片。

笔记有未保存修改、未添加标签或冲突时先处理草稿，再导入或批量整理；批量请求期间编辑区暂时锁定，返回后恢复，避免同时输入被批量结果覆盖。后台保存、401/409处理沿用原有规则。MD只携带文本，文件中原本的本地图片路径不会自动上传图片，导入区已有提示；可使用既有图片上传功能补充。

交互参考[Obsidian编辑与阅读视图](https://obsidian.md/help/edit-and-read)的视图切换/并排阅读，以及[Typora快捷键说明](https://support.typora.io/Shortcut-Keys/)中的常见格式/保存快捷键；未引入其源代码、资源或依赖，不宣称完整复刻所见即所得编辑器。

## 迁移、兼容与启动

新增0015_note_folders，NoteFolder及Note.folder_id由M3维护、待zhy整合。旧笔记默认folder_id=null；SQLite原位追加可空外键列，不重建notes，保持既有引用/反链/图片关系。API启动迁移前会创建`.pre-migration-*.bak`在线备份。新账户备份包含文件夹，并校验同课程/循环/深度/字段；按父先子后恢复。旧0012/0013/0014账户备份显式补空文件夹和null归属，原正文/标签兼容。

无新增依赖。停止旧API/worker，在项目根目录先启动API，看到启动完成后再在另一个PowerShell启动worker；前端保持运行并刷新页面：

```powershell
# 后端窗口
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload
```

```powershell
# 另一个窗口：负责解析与导出等后台任务
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python.exe -m app.workers.materials
```

旧worker不会自动更新打包代码，需要重新启动；旧导出包不改写，重新选择生成新包才能保留最新文件夹结构。没有操作用户的数据库进行测试，也没有自动调用真实模型。

## 实际验证

Windows/Python3.11.9/本机Chrome，所有API/浏览器测试使用临时数据库、存储与演示模型；浏览器端口8056/5178。

| 范围 | 命令与结果 |
|---|---|
| 迁移/文件夹/导入/批量/备份兼容/目录ZIP | `.venv\Scripts\python.exe -m pytest backend/tests/test_note_organization.py backend/tests/test_note_tags.py backend/tests/test_migrations.py backend/tests/test_note_simple_exports.py -q`：33通过（14.95秒）。 |
| 既有账户备份、导出、引用与笔记行为 | `.venv\Scripts\python.exe -m pytest backend/tests/test_account_backups.py backend/tests/test_note_exports.py backend/tests/test_note_citations.py backend/tests/test_notes_workspace.py backend/tests/test_note_export_names.py -q`：23通过（31.07秒）。目录查询改为有界祖先加载后定向复验folder_zip，1通过。不同用例总计56，不宣称全量后端通过。 |
| 前端单元 | `npm.cmd test --prefix frontend`：10文件、41项通过；最终界面调整后复跑仍41通过（1.65秒）。覆盖标签解析/推荐依据/归属排除/安全祖先遍历/选区格式/列表续写/大纲跳过代码块等。 |
| 类型与构建 | TypeScript检查、Office和Vite生产构建通过；最后批量编辑锁定后再次构建通过（Vite 3.05秒）。Ruff检查涉及Python文件通过，Git空白检查通过。 |
| 浏览器 | 新增流程首轮5通过（1.1分钟）；增加首次保存焦点/撤销历史用例后，连同引用/图片/导出/标签/登录恢复31项回归，首轮30通过、1项旧提示文字断言失败（期望“它们引用的图片”，当前为包含目录说明的新提示）。按新提示修改断言后，该导出用例定向复验1通过（25.5秒），文件范围/ZIP实际断言保持。补上批量请求期间锁定正文的延迟响应测试，最终新功能7项全部通过（1.1分钟）；其余25项已在前述运行/复验通过。本轮32个不同Chrome用例最终通过。 |

浏览器回归命令：`npm.cmd run test:e2e --prefix frontend -- note-organization.spec.ts note-citations.spec.ts note-portability.spec.ts note-tags.spec.ts platform.spec.ts --project=chromium`。需将`.venv/Scripts`与Node目录加入PATH并设置`HUSTUDY_E2E_CHROME_CHANNEL=chrome`；截图用`HUSTUDY_M3_EVIDENCE=1`。

截图：[390px文件夹与导入后笔记](evidence/note-organization-390.png)、[1440px文件夹与分屏](evidence/note-organization-1440.png)、[专注编辑](evidence/note-editor-focus.png)。目录ZIP测试实际下载、解压并用标准Markdown渲染，离线file页面加载深层笔记的32px图片，验证跨目录相对路径。未使用真实API、用户资料或真实手机；历史全量Windows权限/执行位/symlink前提问题未冒称已解决。

已人工查看上述截图：桌面/390px无横向溢出，来源与操作可见，专注界面收起标签/图片管理，正文与预览在首屏显示。文档检查18份、455个本地文件链接均存在；其他成员已有截图与本轮开始时逐文件hash一致，未覆盖既有改动。生成的TypeScript构建缓存恢复为本轮前状态，不纳入功能变更。

## 本人建议复验

1. 新建“课程整理/第一章”两级目录，导入两份.md，统一添加“复习、重点”标签；检查标题为文件名，正文完整，重开仍在原目录。
2. 勾选两篇添加标签，管理区把“复习”改为已有“重点”，应合并而不重复；把其中一篇移至未归档，再检查另一篇目录不变。
3. 将目录内笔记、未归档笔记一起勾选导出；解压后应保留目录与根文件，引用图片正常显示。单选时不能夹带未选笔记或其他图片。
4. 给文件夹放入一篇带代表标签的笔记，在推荐区检查候选理由，勾选后确认归类；无匹配时保持空结果。
5. 正文选区加粗，撤销/重做，插入任务列表和表格；检查分屏、大纲、查找、专注及Ctrl+S。切换笔记后不能撤销到另一篇正文。

本轮新增能力待fzk本人反馈；0015团队整合、跨机器恢复、实机/WebKit/真实用户试用待后续执行。已审阅笔记作为M2/M4可信来源和P1图谱仍不包含在本轮交付中。公共[契约](../contracts.md#m3-organize-import-editor-01)、[API](../api.md)、[交接004](../../collaboration/handoff.md#h-20261018-fzk-004)。
