# Phase 0 需求追踪

本文件只记录本轮真实落地的垂直切片；完整 48 项需求和测试矩阵以 `hustudy/Hustudy_traceability_matrix.md` 为基线，未实现项保持待办。

| 需求 | 本轮实现 | 代码/证据 | 验证状态 |
|---|---|---|---|
| FR-01 注册、登录、密码不明文 | 注册、登录、PBKDF2、签名访问令牌 | `backend/app/routers/auth.py`、`backend/app/core/security.py` | 安全原语已验证；API 待依赖安装后测 |
| FR-02 课程 CRUD 与归属隔离 | 课程列表、创建、更新、删除均按当前用户过滤 | `backend/app/routers/courses.py` | API 待依赖安装后测 |
| NFR-06 跨账户隔离 | 资源查询同时约束 `id` 与 `user_id`，不存在统一返回 404 | `backend/app/routers/courses.py` | 设计已落地；集成测试待补 |
| NFR-10 可重建 | 依赖文件、环境示例、启动脚本、前后端基线 | `README.md`、`backend/requirements.txt`、`scripts/` | 前端依赖未安装 |
