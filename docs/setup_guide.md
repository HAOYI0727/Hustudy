# Hustudy 环境与推进指南

## 当前环境结果

已在项目根目录创建 `.venv`，解释器为 Python 3.11.15。当前沙箱禁止访问 PyPI/npm registry，因此 `backend/requirements.txt` 和前端依赖尚未安装；不要把“虚拟环境已创建”理解成“依赖已安装”。

项目技术基线目标是 Python 3.12；本机没有发现 3.12，现阶段使用 3.11。安装 3.12 后，可删除 `.venv` 并重新执行初始化。

## 你需要在本机终端操作

在网络可用的终端进入项目根目录：

```bash
cd /Users/zhy/Desktop/hustudy
./scripts/setup.sh
```

脚本会创建/复用 `.venv`、安装后端依赖、复制 `.env.example`，再安装前端依赖。若你希望明确使用 Python 3.12：

```bash
PYTHON_BIN=python3.12 ./scripts/setup.sh
```

若公司/校园网络使用镜像，请先按网络管理员要求配置 pip/npm 镜像；不要把账号、密码或 token 写进仓库文件。

## 配置与启动

1. 打开 `.env`，至少修改 `HUSTUDY_JWT_SECRET` 为随机长字符串；密钥只保存在本机，不提交 Git。
2. 终端一启动后端：

```bash
.venv/bin/python -m uvicorn app.main:app --app-dir backend --reload
```

3. 另一终端启动前端：

```bash
npm run dev --prefix frontend
```

4. 检查 `http://127.0.0.1:8000/health` 和前端开发地址。OpenAPI 在 `/docs`。

## 每次开发前后

```bash
.venv/bin/python -m pytest backend/tests
./scripts/check.sh
npm run check --prefix frontend
npm run build --prefix frontend
```

当前 API 测试、Ruff 和前端构建在依赖安装前不能执行；执行后把真实结果补进 `docs/progress.md`，不要填写推测结果。

## 需要你准备或确认的产品材料

- 选择一门首版演示课程，准备自制或获授权的 PPTX、文本型 PDF、DOCX、Markdown 和 PNG/JPEG/WebP 小样本；不要直接提交来源不明的课程资料。
- 确认四名成员姓名、模块分工、分支名和 Gitee 仓库地址，并把占位角色 A/B/C/D 替换到团队 Wiki。
- 确认首版是否启用远程模型。启用时再配置服务端密钥、端点和发送确认；未确认前只使用 Mock，不把密钥放前端。
- 组织至少三份自制或获授权的历年样卷，明确年份、卷别、是否有官方答案；未知值保持为空，不补造。
- 安排真实用户试用与反馈记录。访谈、性能、引用语义和题目质量必须实际测量后再写入报告。

## 四人推进顺序

A 先完成 Alembic 第一版迁移、文件存储和 ProcessingJob；M1 再完成四格式解析、预览降级、切片和关键词索引。Citation 契约稳定后，C 实现笔记/图片/双链，B 实现带来源 AI，最后 D 接入真题、蓝图、作答和复习。各成员只修改自己模块目录，跨模块字段先更新 `docs/contracts.md`。

## 常见问题

- `pip` 报无法连接 PyPI：换到允许访问 registry 的终端，或配置经批准的内部镜像后重新执行脚本。
- `npm install` 长时间无输出：停止命令，检查 npm registry 和代理配置；不要提交不完整的 `node_modules`。
- 端口被占用：后端可用 `--port 8001`，同时把前端 API 地址配置方案记录在协作文档中。
- 依赖安装完成但 API 启动失败：先执行 `.venv/bin/python -m pip check`，再检查 `.env` 和 `data/` 写权限。

## 两个服务的终端用法

后端是常驻进程，会占用当前终端。请打开两个终端窗口：

终端一：

```bash
.venv/bin/python -m uvicorn app.main:app --app-dir backend --reload
```

终端二：

```bash
npm run dev --prefix frontend
```

如果看到旧的 SQLAlchemy `String object has no attribute _set_parent_with_dispatch`，先停止旧进程并重新启动；该问题已修复为 `String(36), ForeignKey(...)` 的正确参数顺序。

## 本轮环境复核（2026-10-09）

当前 `.venv` 已可运行 FastAPI、SQLAlchemy、pytest、Ruff；前端依赖已可执行检查和生产构建。由于执行环境无法访问 PyPI，`pypdf`、`python-docx`、`python-pptx` 尚未下载。请在本机网络可用时执行：

```bash
.venv/bin/pip install pypdf==5.1.0 python-docx==1.1.2 python-pptx==1.0.2
```

安装后，重新上传对应格式资料即可启用解析；缺少这些包时，系统会把解析失败原因写入资料版本和 ProcessingJob 状态，不会伪装成解析成功。
