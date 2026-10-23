# Hustudy frontend

React + TypeScript + Vite前端，业务工作区在`src/features`，统一接口在`src/api`。安装锁定依赖后运行`npm run dev`；`npm run build`执行类型检查和生产构建，`npm test`运行单元测试。不在React渲染阶段直接启动后端任务。

未配置时，开发API为`http://127.0.0.1:8000/api/v1`，生产API为同源`/api/v1`。需要显式连接公共后端时参考[环境模板](.env.example)，在本机`frontend/.env.local`设置`VITE_API_BASE_URL=https://实际域名/api/v1`，并在后端允许准确的前端CORS来源。修改后重启Vite；生产环境须重新构建。该变量是公开地址，禁止放入密钥。

GitHub同步源码不会同步账号或学习数据；跨电脑须连接同一套后端与持久数据。现有账号迁移、部署与验收见[云端账号说明](../docs/zhy/shared_platform/cloud_accounts.md)。

使用指南新增完整手册阅读/下载与自制学习示例。正文唯一来源为根[user.md](../user.md)，由显式`?url&no-inline`静态引用发布；修改手册后需随生产版本重新构建。仅打开弹窗才读取正文，不依赖认证API或数据库；示例只下载，导入须用户确认。验证入口为`manual.test.ts`、`user-manual.spec.ts`与`manual-learning-loop.spec.ts`，实际范围见[验收记录](../docs/zhy/integration/user_manual_acceptance.md)。
