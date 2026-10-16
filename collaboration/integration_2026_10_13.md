# 队长集成切片：2026-10-13

## 已落地的协作基础

| 负责人 | 前端入口 | 本轮交接 |
|---|---|---|
| A | `frontend/src/features/materials/index.tsx` | 资料页面独立，平台会话和课程选择由 `main.tsx` 维护 |
| B | `frontend/src/features/ai/index.tsx` | AI 页面独立，消费统一 API client |
| C | `frontend/src/features/notes/index.tsx` | 笔记页面独立，切换课程重新挂载防止误存 |
| D | `frontend/src/features/exams/index.tsx` | 考试/复习页面独立，蓝图题型数量与分值可编辑 |
| A 共享层 | `frontend/src/features/platform/index.tsx`、`components/workspace.tsx` | 登录/总览与共享状态、空状态、标题组件 |

此次是目录拆分和集成缺陷修复；没有替换业务模型和数据库结构。各模块的深层业务逻辑仍待负责人完善，拆分不代表已满足全部 P0。

## 后端交接

错误响应保持既有形态，request_id 与响应头一致。404 路由和 Pydantic 校验错误统一封装，异常内部信息不返回客户端。API client 保留 code/requestId，便于后续错误反馈。

`backend/tests/conftest.py` 在应用导入前指定临时 SQLite 和临时文件目录；测试结束由 TemporaryDirectory 清理，不再向日常 data 目录写入烟雾数据。以后新增测试应沿用此入口，不自行硬编码运行库。

## 实际验证

- pytest：6 passed，含新增 404/422/500 错误契约验证；仍有 1 条第三方弃用警告。
- 前端构建（包含 TypeScript）：通过。
- Safari：原会话过期自动退回登录；用已有演示账号重新登录成功；学习路线、蓝图表单可见；简答题数 5 改 3 后显示 13 题、80 分。
- 窄窗口导航改为两行，退出登录保持可见。

## 下一轮队长集成优先级

1. A：数据库迁移与独立 worker、文件归属/删除隔离；定义供 B/C/D 使用的来源查询服务。
2. C：引用回源与笔记冲突交互；B：固定样例 Mock/Provider/schema 校验；均通过 M1 契约集成。
3. D：严格蓝图 schema 与 topic 配额、真题映射统计、作答恢复及答案隔离；当前表单改进尚未解决这些后端完整约束。
4. 全员：扩大跨用户与删除失效测试，补齐真实四格式 fixture 与浏览器闭环测试。

下一阶段的创新方向沿用需求基线：可追溯证据链、资料缺口提示和薄弱项练习。暂未实现的统计不得用虚构数字装饰工作台。

## 全模块 UI 交接补充

共用 `PageTitle` 提供模块配色和 SVG 图案，`ModuleStats` 展示真实数据；样式在 styles.css 的 Unified module workspaces 区域。M1 维护 reading-layout；B 维护 AI 提问模板与审阅草稿；C 维护笔记关联区；D 维护拆题展开、ShortAnswer 与复习完成接口。请勿把已接通的 UI 入口等同后端全部业务约束验收完成；完整端到端测试范围见 docs/progress.md。
