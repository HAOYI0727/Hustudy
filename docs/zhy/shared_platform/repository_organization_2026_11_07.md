# 仓库目录整理与数据保留（2026-11-07）

记录者：Codex辅助zhy队长；主责：共享层/M1与仓库集成；基线main@70096a8，含既有本地修改，未提交/推送。用户授权测试分类、协作/技术文档规划及冗余本地产物清理。本轮不删除测试用例、成员实验事实或日常业务数据。

## 目录规则

```text
backend/tests/
  conftest.py / __init__.py / README.md
  shared/ m1/ m2/ m3/ m4/ integration/ support/
frontend/tests/
  README.md
  unit/{shared,m1,m2,m3,m4,integration}/
  e2e/{shared,m1,m2,m3,m4,integration}/
collaboration/
  README.md / roles.md / workflow.md / task_board.md / handoff.md
  zhy/ gcx/ fzk/ xtc/             成员入口与真实进度
docs/
  README.md / api.md / contracts.md / decisions.md / progress.md
  traceability.md / test_report.md / third_party.md
  setup_guide.md / user_guide.md / final_acceptance_2026_10_30.md
  zhy/ gcx/ fzk/ xtc/             四人技术方案、进度与证据
  licenses/                       必须保留的公共第三方许可
fixtures/                         版本化自制输入，网站指南也直接引用
.artifacts/                       Git忽略的生成物
  inputs/                         可选私有样本选择器
  e2e/                            显式采集的截图/指标/下载样例
  playwright/test-results/        自动失败截图、trace和运行产物
data/
  hustudy.db及活跃WAL/SHM          本机业务库，不提交
  storage/                        原件/图片/预览/导出等业务文件，不提交
  api-connections/                本机账户加密配置，不读取/回显
  backups/pre-migration/           留存最近两份迁移前快照
```

测试分类表达模块责任，跨模块用例放integration，不按目录推定个人贡献。Python使用显式tests.<组>.<模块>导入，保留根conftest隔离设置；前端同步模块import、file-relative URL与cwd-relative路径，避免相对目录变化破坏样例和安全测试输入。Vitest/Playwright仍递归发现全部文件。

原docs/m4整体并入docs/xtc/implementation；M2分design/acceptance/history，M3验收分acceptance，M4格式分formats、日期记录分history。M1原shared_platform/materialhub/integration/history继续使用。根公共API/契约、过程证据与第三方许可仍唯一维护，不挪到某成员目录冒记贡献。

早期collaboration下project_handoff、roadmap、experience_roadmap、github_sync、integration_2026_10_13归档至docs/zhy/history/collaboration，保留内容并更新链接；必要的成员README/progress与正式任务状态保留。旧docs/setup_guide和user_guide改为指向根README/user的兼容入口，不再重复一整份过期手册。

## 清理范围与可恢复备份

整理前的受影响源码、测试、文档、原差异补丁、迁移清单/原SHA-256，以及一致性SQLite备份，保存在工程外`/Users/zhy/Desktop/hustudy-cleanup-backups/20261107-175318`。备份目录权限0700，不入Git。

- 迁移306个测试/辅助/文档文件，文件级映射在工程外manifest.json；测试没有删减。
- root local、local_only、frontend/local_only的296份历史截图/指标/下载产物共309,928,304字节移到外部local-evidence归档；不是网站运行依赖。显式私有样本选择器另保留在.artifacts/inputs。
- data原有14份迁移前备份，最近两份放data/backups/pre-migration，其余12份共20,639,744字节外部归档。此为本轮整理，不宣称程序已实现自动备份保留策略；后续迁移仍可能在数据库旁生成新快照。
- 合计约315MiB历史产物与旧快照移出项目，但外部备份仍占磁盘，不声称永久释放同等空间。
- 删除可再生成的Python/pytest/Ruff缓存及系统目录缓存；测试运行后部分缓存会正常再生成。
- 保留全部fixtures、锁文件、配置样例、依赖、迁移、Office/数学构建钩子、原件/图片/预览与第三方许可。fixtures不能整体忽略：站内下载和自动测试都依赖它。

未清理数据库行或storage文件：不同版本的相同内容、历史作答、课程包或图片可能仍被引用，不能仅凭文件较旧/重复hash就删除。活跃db-wal/db-shm和凭据目录保持，未打印密钥。整理前后用户13、课程22、资料62、资料版本62、笔记9的数量一致；这只证明本轮未删这些业务对象，不代表所有数据均已内容审计。

## 验证与真实问题

- 后端收集790项，迁移前后按文件名/测试身份的多重集合完全一致；前端40单测文件、706个双引擎浏览器场景保持。
- 前端全量单测251 passed；TypeScript/生产构建通过。
- 后端首次完整运行784 passed、4 failed、2 skipped。迁移测试仍期待0022而当前为0024，已改为核对Alembic实际头，迁移6项定向复验全通过。
- 余3项课程包测试仍失败，错误为“课程包含跨课程或跨账户对象”。使用工程外备份中的原平铺测试复验，同3项同错误失败，确认不是目录迁移或依赖丢失引入。本轮不改课程包业务、不跳过/删去失败用例，保留后续兼容修复。
- Ruff发现已合并BankAnswerImport模型导入未列入__all__，补全公开导出，保留模型注册，复验通过；数据库迁移/ORM漂移脚本通过。无新依赖或迁移。
- Chromium/WebKit专项44 passed：覆盖手册闭环、PPTX/DOCX原格式读取与隔离、长资料布局/末页查找、相近问答、图谱及题库样例下载。未重跑全部706场景，不把收集成功当执行通过。
- 本轮文档本地链接检查0失效，git diff --check通过；所有后端测试身份与前端场景发现数量不变。

```bash
PYTHONPATH=backend .venv/bin/python -m pytest --collect-only -q
PYTHONPATH=backend .venv/bin/python -m pytest -q
PYTHONPATH=backend .venv/bin/python -m pytest backend/tests/shared/test_migrations.py -q
.venv/bin/ruff check backend/app backend/tests backend/migrations
PYTHONPATH=backend .venv/bin/python scripts/verify_migrations.py
npm run test --prefix frontend
npm run build --prefix frontend
npm run test:e2e --prefix frontend -- --list
HUSTUDY_E2E_CHROME_CHANNEL=chrome npm run test:e2e --prefix frontend -- \
  shared/user-manual.spec.ts integration/manual-learning-loop.spec.ts \
  m1/native-preview.spec.ts m1/reading-layout.spec.ts m2/related-answers.spec.ts \
  m3/note-graph.spec.ts m4/m4-bank-default-example.spec.ts
```

工程外日志：`/tmp/hustudy-reorganize-20261107`，包含前后收集、后端全量/原用例复验、前端单元、构建与浏览器输出；临时目录不是长期发布证据。测试均隔离数据库与文件/模拟Provider，不调用真实AI，不操作日常账号，不代签真人/成员或全部设备。

## 后续维护

新增测试直接放所属组；需要共用辅助放support或明确导入，不能恢复平铺搜索依赖。新增功能文档只进入四成员或公共必要文件。临时截图/实验输出只写.artifacts，正式证据再由本人筛选/脱敏后纳入docs。日常data清理优先走网站删除/回收站/备份流程；对孤立文件应先实现完整引用核对和干运行清单，不能用时间或文件夹名猜测。

## 补充清理与课程报告（H-20261107-ZHY-003）

进一步把.tools根部12张旧截图及.artifacts/e2e、playwright历史输出共15,212,287字节移出项目，归档至工程外hustudy-cleanup-backups/report-pass-20261107-181137（0700，含路径/哈希清单和原reference备份）。本轮两项路径复验生成的小量截图亦归档，不保留重复运行产物。保留.tools中实际测试运行时、.venv、node_modules、全部锁文件/迁移/fixtures及运行数据；Hustudy内早期设计报告属于课程过程材料，暂保留。删除reference/.DS_Store，正在打开的Office/WPS锁文件不强删，改由.gitignore排除。

补齐M3图谱/冲突合并两个测试中残留的.tools截图路径，改写.artifacts/e2e/optional；隔离Chromium的390px对应场景2 passed（22.6秒），无业务代码、数据库或模型调用变化。其他测试结果沿上述真实范围，不重新宣称全站通过。

按reference课程教案、报告模板、72页汇报PPT及当前源码/四模块文档完成[项目报告](../../../reference/项目报告.docx)：第一、二章完整正文，第三至六章四人协作框架。32页、35组功能需求、22表、2张UML图和6张PPT内真实界面截图；目录33项逐项核对实际页码，全部页面渲染检查。原封面信息和模板页几何保留，模板/教案/PPT原件SHA-256不变。报告保留3项课程包失败、教师标记缺口和正式验收边界；个人体会与真实用户反馈由本人补充，未代签。未提交或推送。
