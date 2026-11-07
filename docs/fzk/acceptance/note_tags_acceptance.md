# M3-NOTE-TAGS-01：笔记标签验收

补记（2026-10-17）：用户后续明确反馈“以上功能验收均成功”，据此记录标签切片的fzk人工验收成功；不代表其他成员已签收或main已合并。下文保留本切片当时的测试与待办历史；独立ZIP等后续实现及当前剩余工作见[本轮记录](m3_completion_audit.md)。同日截图已刷新为后续功能完成后的最终页面。

日期：2026-10-17。实际实现者：Codex在fzk会话辅助；fzk人工审阅待填写。C02/C08/C09，FR-09/10/11，NFR-06/10；分支`codex/fzk-m3-note-tags`，基线`f789a6b`，工作区未提交/未推送/未合并。交接[H-20261017-FZK-001](../../../collaboration/handoff.md#h-20261017-fzk-001)，状态Review/待接收。

## 远端核对

由51252be同步至f789a6b，包含PR #1/#2与M2的两次业务提交，114个文件变化（部分为换行变化）。主要新增资料范围问答、教学报告/分批、自测与标签审阅、练习题候选及逐题知识点、已有结果复用。角色文档为gcx=M2、xtc=M4；fzk=M3不变。本地原有requirements.lock中的uvloop Windows条件保留。

## 实现与边界

- Note.tags持久化、规范化与旧调用兼容；标题/正文/标签查找，精确标签筛选；同revision保存，409返回服务端标签。本地草稿、待添加输入、401恢复和双链目标不被筛选覆盖。
- 新迁移0013_note_tags只追加tags默认[]；旧笔记内容/UUID/revision保留。迁移脚本由本分支准备，zhy整合评审待完成。
- 账户备份schema_revision从0012升级0013；旧0012缺标签显式补[]，新备份缺字段/非法/未规范化标签拒绝恢复。无单独标签数据库或平行备份机制。
- Windows专用tzdata==2026.5补齐本机时区数据。既有uvloop条件保留；不改变本地.env、模型密钥/模式，不向远端发送资料。
- 独立知识库附件ZIP尚未实现；单笔记.md格式不变。M3其余需求仍须继续逐项核查；本次不宣称全M3/全P0完成。

代码范围：backend/app的models/notes、schemas/notes、routers/notes、services/note_filters/note_search/note_backup；共享account_backups仅版本识别/升级调度；0013迁移、依赖；frontend的notes功能、Note类型及对应测试。未改M1解析、M2生成、M4组卷。

## 验证环境与命令

Windows、项目Python 3.11.9虚拟环境、Node 24.22.0；所有业务验证用临时数据库/文件、自制资料，固定模型或模拟响应。实际用户data未用作测试；浏览器服务使用8056/5178。

```powershell
$env:PYTHONPATH = "backend"
$env:PYTHONUTF8 = "1"
.\.venv\Scripts\python.exe -m ruff check backend/app backend/tests backend/migrations
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/verify_migrations.py
npm.cmd run test --prefix frontend
npm.cmd run build --prefix frontend
$env:PATH = (Join-Path $PWD '.venv\Scripts') + ';' + $env:PATH
$env:HUSTUDY_E2E_CHROME_CHANNEL = 'chrome'
npm.cmd run test:e2e --prefix frontend -- note-tags.spec.ts platform.spec.ts study-reports.spec.ts --project=chromium
```

| 验证 | 实际结果 |
|---|---|
| Ruff | 全部通过 |
| 后端全量pytest | 264 passed、3 failed，144.60秒；失败详见下方，不能写全量通过 |
| 新增M3后端 | 14项均在上述全量通过：标签持久化/CAS、7种非法输入、搜索/权限/删除、新旧备份2种往返、3种损坏标签回滚 |
| 原笔记/迁移/账户备份 | 均在全量通过；迁移模型漂移检查独立通过 |
| 前端Vitest | 27 passed（7 files）；含2项新增标签单元测试 |
| TypeScript/Vite生产构建 | 通过（含Office运行时预构建） |
| Chrome浏览器 | 最终12 passed，1.5分钟；6项新增M3、4项共享平台、2项M2学习报告/草稿（390/1440px），最终日志无服务端ERROR |

全量3个失败与远端已有Windows记录一致，文件未在本轮修改：

1. `test_jwt_contract.py::test_signing_setup_preserves_valid_keys_and_other_configuration`：测试假定POSIX 0600权限位，Windows不满足。
2. `test_preview_recovery.py::test_capability_is_authenticated_and_never_exposes_configured_path`：测试假定chmod(0600)移除可执行权限，Windows行为不同。
3. `test_storage_contract.py::test_storage_rejects_traversal_symlink_and_low_capacity`：创建symlink因WinError1314缺少本机特权失败。

初次标签/备份回归暴露本机缺少tzdata（以及新增测试DELETE参数位置错误，已修正）；安装并锁定时区数据后，完整备份往返与新增测试全部通过。前端首次沙箱缓存重命名遭EPERM，正常权限重跑通过。首次9项Chrome虽通过，但服务启动期间时区依赖未就绪产生后台错误，因此补齐依赖后重新运行最终集成集，结果以上表为准。

## 界面证据与操作

进入课程 → 知识笔记 → 标签输入名称 → Enter/添加 → 自动保存。目录可用关键词与“按标签筛选”组合查找，清除筛选恢复完整列表。校验失败保留输入；冲突可对照服务器标签/正文后显式载入。未添加输入需先添加或清空才保存。

- [桌面1440px](../evidence/note-tags-1440.png)
- [手机宽度390px](../evidence/note-tags-390.png)

截图来自临时测试账户；已目视检查换行、控件和排版。未执行WebKit与真实手机/iPad复验，未做性能基准或真实用户反馈。

## 重启、交接与下一步

Windows先安装更新后的requirements.lock，再停止旧worker并重启API，等待启动完成/0013迁移，再启动worker；前端刷新。既有init_db会在非空库升级前保存SQLite备份，新0013账户ZIP不能回灌旧0012程序。模型配置不自动更改。

zhy评审迁移号/备份版本后整合；gcx复验报告草稿→笔记；xtc后续消费Note附加字段。成员签收由本人填写。下一切片C07独立知识库ZIP及来源清单/hash验证；不以账户备份代替知识库导出。
