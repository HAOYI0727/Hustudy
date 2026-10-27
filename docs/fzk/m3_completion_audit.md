# M3 完成情况与提交验证

## 2026-10-27 提交前边界复验

用户已确认第11/12项本轮演示验收通过，并授权核对剩余边界后提交。用户验收范围与隔离自动测试分别记录。第9A/9B项仍按原决定暂缓，真人识别质量、实机和团队签收不因本次提交自动通过。

本轮检查覆盖图谱同向去重、完整度数、205节点/462边截断、回收/跨账户/跨课程排除、同快照计数、关闭迟到与401，以及标准包未归档/空目录/自选依赖、来源重映射、同名追加、目录深度、预览过期/配额/篡改、路径/重复成员/大小/哈希拒绝、并发确认幂等、响应丢失核对和文件/事务失败回滚。全部使用临时数据库、自制文件及模拟模型，不调用真实服务。

收尾修正：移除共享模型配置的重复导入与重复路由注册；新增路由(path, method)唯一性回归，避免重复API定义。最终后端静态检查通过。

- 后端边界：`python -m pytest backend/tests/test_note_graph.py backend/tests/test_portable_packages.py backend/tests/test_portable_content.py backend/tests/test_portable_roundtrip.py backend/tests/test_model_connections.py backend/tests/test_migrations.py -q`：106通过。
- 修正后模型配置/助手专项：`python -m pytest backend/tests/test_model_connections.py -q --tb=short`：23通过（包含新增路由唯一性；与上项重叠，不累计为独立用例总数）。
- 共享模型集成：M2执行/远程问答/长资料批次、题库视觉/归类、账户隔离及停用配置七个测试文件：126通过、1跳过（未提供私有ZIP样本）；模拟传输，无真实调用。
- 前端全量单元：`npm.cmd test --prefix frontend -- --maxWorkers=2`：39文件、248通过。
- 浏览器：`npm.cmd run test:e2e --prefix frontend -- note-graph.spec.ts portable-packages.spec.ts note-conflict-merge.spec.ts note-reading.spec.ts note-assistant.spec.ts`，Chrome/WebKit共88场景。首轮87通过、1失败：保存源码保持原换行时触发Vite热更新，WebKit选文场景丢失选区，同时出现重复createRoot提示。冻结源码后对该1440px场景以`--project=webkit --grep '笔记助手选文.*1440px' --repeat-each=2`复跑，2/2通过；未改断言或功能实现。最终88个不同场景均有通过结果，复跑不计为新增场景，不能称首轮全绿。
- `npm.cmd run build --prefix frontend`：类型检查与生产构建通过。
- `PYTHONPATH=backend python scripts/verify_migrations.py`：隔离库升级到0022、ORM漂移检查通过；`ruff check backend/app backend/tests backend/migrations`通过。

提交范围仅相关源码、测试、0022迁移、样例生成/合并基准脚本和功能/协作文档；不提交实际课程包、用户资料、密钥、数据库、截图、日志、依赖目录、构建产物或tsbuildinfo缓存。当前分支`codex/fzk-m3-safe-merge`基于`aa45665`，提交前fetch核对origin/main未新增提交；本轮只推送功能分支，main合并由后续流程决定。

2026-10-19，fzk（Codex辅助）；分支`codex/fzk-m3-note-tags`，基线`f789a6b`。

2026-10-26状态补充：上述提交已合入main，当前基线aa45665。共享层已补本机草稿恢复，M2已补明确选择/确认个人笔记；逐段冲突合并用户已复验通过，见[独立验证记录](note_merge_acceptance.md)。后续本地增量为[课程笔记关系图谱](note_graph_acceptance.md)，2026-10-27用户确认本轮演示验收通过。下方测试数字保留为10月19日历史结果，不作为当前全量验证。

## 当前状态

2026-10-27原阅读模式与可选自动保存已获用户验收。后续新增专注跨笔记导航、多模型及笔记AI助手，当前自动验证与两份标准课程包详见[本轮记录](note_assistant_acceptance.md)；用户已确认本轮新增功能验收通过，团队接收独立待填写。

2026-10-27本地新增匹配的标准课程／文件夹ZIP导入导出及课程包合并：可自选内容、预览依赖、以新身份追加到已有课程，保留原课程和同名内容；含0022控制记录迁移。自动验证与工程外验收样例见[标准数据包验收说明](portable_packages_acceptance.md)，2026-10-27用户确认本轮演示验收通过。本节以后的10月19日数字仍属历史记录。

Markdown/公式编辑、标签与目录、批量导入/整理、图片管理、双链与引用、选择ZIP、保存恢复及回收站已实现。用户已确认第1–8项和公式/识别插入流程通过；第9项跨课程及独立完整恢复按用户要求暂缓。详见[人工验收](manual_recheck.md)。团队接收、迁移整合和全站P0验收保持独立。

旧识别任务AI整理和其专用API启用仍停用，识别只提供待核对文本插入当前笔记；本轮新增笔记助手及共享多模型另走预览/确认流程。保留0017/0018及旧接口兼容，不删除历史笔记或识别结果。

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

第9项人工验收、真实手机/麦克风/手写质量、可选Whisper推理与目标用户试用仍待执行。通用笔记审阅来源契约尚未实现；本轮关系图谱使用课程内已有双链，不包含自动语义建图或跨课程展示。共享层整合及本机未保存草稿恢复已随后续main交付，浏览器容量、站点数据清理和过期仍影响恢复能力。

本次为定向回归；历史全量后端3项Windows权限/执行位/符号链接前提失败未据此声明修复。提交不包含本机密钥、运行库、上传原件、测试下载、依赖目录或构建产物。
