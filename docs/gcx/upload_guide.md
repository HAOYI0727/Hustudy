# GitHub网页上传清单（当前本地源码）

2026-10-16，Codex辅助gcx，仅检查文件路径/类型/大小并整理清单，没有读取.env内容、没有上传、没有核对远端最新提交，也没有执行完整密钥审计。清单相对Hustudy-main根目录，不是与远端的真实差异。

## 两种上传范围

- [本轮M2文件清单](upload_files_m2.txt)：83个文件，由本轮累计变更记录去重、补齐后逐项检查存在性。适用于向已有团队仓库交接M2。公共文件和xtc分工更正记录也在其中，须对照远端保留其他人的修改，不代签他人。
- [完整源码文件清单](upload_files_full.txt)：357个文件，包含运行/重建所需源码、配置样例、锁文件、测试、自制样例、文档、许可证及验收证据。适用于确需提交完整本地源码快照；不能据此将本地旧共享文件整体覆盖远端。

所有路径均保持原目录层级；不要增加Hustudy-main外层目录。纯文本清单每行一个路径，包含清单自身。GitHub网页分批上传时保持同一分支和正确路径；本说明不表示已建立分支、上传或合并。

## 根目录选择规则

| 路径 | 处理 |
|---|---|
| backend/ | 源码、迁移、测试、alembic.ini、requirements.txt和requirements.lock；排除所有__pycache__/和.pyc |
| frontend/ | src/、tests/、scripts/、index.html、README.md、package.json、package-lock.json、tsconfig.json、vite.config.ts、vitest.config.ts、playwright.config.ts、public/third-party-notices.txt |
| collaboration/、docs/ | 保留协作文档、许可证、自制验收证据，包含其他成员既有内容；M2增量上传按专用清单 |
| fixtures/ | 保留项目自制测试样例，与data/storage中的个人上传资料不同 |
| hustudy/、scripts/ | 保留需求文档和源码脚本；scripts中排除__pycache__/ |
| 根目录文件 | .env.example、.gitignore、AGENTS.md、Hustudy_requirements.md、Hustudy_team_collaboration.md、main_idea.md、pytest.ini、README.md |
| data/ | 仅保留data/.gitkeep；数据库、WAL/SHM、上传原件、图片、预览、导出包均不进源码提交 |
| reference/ | 本次默认不纳入新上传：课程教案DOCX和GitHub_Projects.md不是运行依赖；已有仓库文件无需删除，如需新增共享请确认内容和授权 |

## 本地存在、此次排除的内容

- .env：实际模型密钥、签名配置可能位于其中。使用.env.example提供配置结构，由接收人自行生成本机配置，不共享真实密钥到仓库。
- data/hustudy.db、data/hustudy.db-wal、data/hustudy.db-shm及data/storage/：本机账户、记录和上传课程材料。若要转交演示数据，另外准备确认可分享的备份包；不要复制正在运行的SQLite文件作为源码交接。
- frontend/node_modules/：npm安装产物，通过package.json和package-lock.json重建；两个清单文件要上传。
- frontend/dist/、frontend/public/native-office/：构建生成，安装依赖后由构建脚本生成；保留frontend/scripts/build-office.mjs及许可证。
- frontend/test-results/、.pytest_cache/、.ruff_cache/、各级__pycache__/、*.pyc、frontend/tsconfig.tsbuildinfo：测试/缓存/增量编译产物。
- 如以后出现.venv/、.tools/、playwright-report/等，继续排除。

.env与个人数据应排除；依赖/构建/缓存并非技术上绝不能上传，而是本项目源码交接不提交它们，避免体积大、难比较及本机状态混入。删除上传准备副本中的内容即可，不要删除实际项目中的.env或data。

本次只生成文档，无运行逻辑变化，不需重启后端、worker或前端。网页手动上传不要依赖.gitignore自动过滤；按清单自行选择。
