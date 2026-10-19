# M3 完成情况与提交验证

2026-10-19，fzk（Codex辅助）；分支`codex/fzk-m3-note-tags`，基线`f789a6b`。

## 当前状态

Markdown/公式编辑、标签与目录、批量导入/整理、图片管理、双链与引用、选择ZIP、保存恢复及回收站已实现。用户已确认第1–8项和公式/识别插入流程通过；第9项跨课程及独立完整恢复按用户要求暂缓。详见[人工验收](manual_recheck.md)。团队接收、迁移整合和全站P0验收保持独立。

M3 AI整理和个人API启用已停用，识别只提供待核对文本插入当前笔记。保留0017/0018及旧接口的必要兼容处理，不删除历史笔记或旧识别结果。

## 本次提交前验证

全部使用临时数据库、自制文件及模拟服务，不调用真实模型、不修改日常账户。

| 检查 | 实际结果 |
|---|---|
| 12个相关后端测试文件：笔记/标签、图片导出、目录、回收站、识别、停用配置、引用、迁移、完整备份 | 82 passed；Starlette/AnyIO一条弃用提示 |
| `npm.cmd test --prefix frontend` | 14文件、58项通过 |
| `npm.cmd run build --prefix frontend` | TypeScript、Office/数学许可生成和Vite生产构建通过 |
| Chrome：note-trash、note-portability、note-capture | 22项通过，包含草稿保护、旧快照、导出/离线图片、创建幂等和真实DOCX识别插入 |

后端命令：`python -m pytest backend/tests/test_note_tags.py backend/tests/test_note_exports.py backend/tests/test_note_export_names.py backend/tests/test_note_simple_exports.py backend/tests/test_note_organization.py backend/tests/test_note_trash.py backend/tests/test_note_capture.py backend/tests/test_note_ai_config.py backend/tests/test_note_citations.py backend/tests/test_notes_workspace.py backend/tests/test_migrations.py backend/tests/test_account_backups.py -q`。

浏览器命令：`npm.cmd run test:e2e --prefix frontend -- note-trash.spec.ts note-portability.spec.ts note-capture.spec.ts --project=chromium`。Windows使用项目venv及Node PATH、`PYTHONUTF8=1`、`HUSTUDY_E2E_CHROME_CHANNEL=chrome`。详细分项与既有Chrome/WebKit证据保留在专项说明中，不把各轮重复用例数量相加。

提交收尾补验：发现SQLAlchemy 2.0对SQLite内联外键的反射遗漏ON DELETE动作，现仅在迁移比较时按PRAGMA补全实际动作，不改运行数据库。新增测试同时验证真正的动作差异仍会报错；迁移/目录/回收站24项通过，独立迁移升级及模型漂移检查通过，Ruff通过。迁移检查脚本在异常时也释放数据库连接，避免Windows临时文件占用。

## 更新与集成

- 迁移0013–0018分别覆盖标签、导出记录、目录、回收站、识别缓存及旧配置兼容；按既有Alembic链执行，禁止删库重建。
- 先安装`backend/requirements.lock`，启动后端完成升级，再启动worker；OCR/本地转写可选依赖见[识别说明](capture_text_acceptance.md)。
- 完整业务备份版本为0016，兼容0012–0015；识别缓存、导出缓存、旧个人凭据不作为可恢复业务内容。跨机器恢复人工验收暂缓。
- Windows依赖补充tzdata并排除uvloop；新数学依赖和完整许可随源码与锁文件提交。

## 保留待办

第9项人工验收、真实手机/麦克风/手写质量、可选Whisper推理、目标用户试用及zhy共享层整合仍待执行。知识图谱、笔记审阅来源契约、崩溃后未保存草稿持久恢复尚未实现。

本次为定向回归；历史全量后端3项Windows权限/执行位/符号链接前提失败未据此声明修复。提交不包含本机密钥、运行库、上传原件、测试下载、依赖目录或构建产物。
