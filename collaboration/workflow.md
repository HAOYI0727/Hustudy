# 协作与交接流程

## 开始任务

1. 从 `develop` 创建 `feature/<module>-<task>` 分支。
2. 阅读本文件、`AGENTS.md`、`docs/contracts.md`、相关需求、本人 `collaboration/<成员>/` 与 `docs/<成员>/`、相关 handoff 条目和现有 `git diff`。
3. 在 Issue 中写任务编号、需求 ID、输入/输出、禁止修改目录和验收命令。

当前仓库阶段的GitHub操作见[github_sync.md](github_sync.md)：先把已有未提交实现放到功能分支，推送后再评审进入develop；远程已有配置，不重复添加。

## 修改与提交

- 一个提交解决一个可审阅问题，使用 `feat(m1): ...`、`fix(m2): ...`、`test(m4): ...`、`docs: ...`。
- 跨模块字段先在 `docs/contracts.md` 写变更意图；A 合并迁移。
- 所有资源查询显式包含 `user_id`；禁止在前端隐藏答案来代替服务端隔离。
- AI 结果、题目引用和导入解析状态必须经过 schema/业务校验；没有依据时返回明确状态。
- 每个切片在提交/PR 前更新个人 progress、功能/优化证据，并在 [handoff.md](handoff.md) 追加交接 ID、实际实现者、接收人、测试真实输出和风险。接口/阻塞影响下游时及时追加，不等最终集成。
- 个人记录默认由本人维护；共享 API/schema 意图写在 docs 根级权威文件，不在个人目录另建契约。队长辅助其他模块的改动记入 zhy 集成交接，不能替接收成员填写个人成果或签收。

## 合并前检查

```bash
bash scripts/check.sh
```

按改动范围选择必要检查；纯文档变更检查链接与 git diff --check，不冒称业务测试已重跑。PR 描述包含：任务编号/需求 ID、修改文件、迁移、测试真实输出、截图或 API 证据、未完成风险、个人证据及交接 ID。接收成员在 handoff 本人栏写实际复验，队长在 `develop` 集成后更新 `docs/progress.md`、`docs/traceability.md` 和任务板；全部验收满足才标“已验收”。

公共 handoff 并发冲突：先基于最新 develop 合并，保留双方独立条目与历史，核对 ID 唯一和索引链接；不以覆盖整个文件解决冲突。不自动发送外部通知，受影响成员开始任务及提交前主动读取交接。

## 运行环境

后端与资料 worker：`bash scripts/dev.sh`；前端另开终端：`npm run dev --prefix frontend`。已有后端时可单独 `bash scripts/worker.sh`。Safari 访问 `http://localhost:5173/`，API 默认 `http://127.0.0.1:8000`。真实模型密钥只进后端环境变量。
