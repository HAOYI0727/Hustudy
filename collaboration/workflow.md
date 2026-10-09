# 协作与交接流程

## 开始任务

1. 从 `develop` 创建 `feature/<module>-<task>` 分支。
2. 阅读本文件、`AGENTS.md`、`docs/contracts.md`、相关需求和现有 `git diff`。
3. 在 Issue 中写任务编号、需求 ID、输入/输出、禁止修改目录和验收命令。

## 修改与提交

- 一个提交解决一个可审阅问题，使用 `feat(m1): ...`、`fix(m2): ...`、`test(m4): ...`、`docs: ...`。
- 跨模块字段先在 `docs/contracts.md` 写变更意图；A 合并迁移。
- 所有资源查询显式包含 `user_id`；禁止在前端隐藏答案来代替服务端隔离。
- AI 结果、题目引用和导入解析状态必须经过 schema/业务校验；没有依据时返回明确状态。

## 合并前检查

```bash
./.venv/bin/python -m pytest -q
./scripts/check.sh
npm run check --prefix frontend
npm run build --prefix frontend
```

PR 描述包含：任务编号/需求 ID、修改文件、迁移、测试真实输出、截图或 API 证据、未完成风险。队长在 `develop` 集成后更新 `docs/progress.md`。

## 运行环境

后端：`.venv/bin/python -m uvicorn app.main:app --app-dir backend --reload`；前端另开终端：`npm run dev --prefix frontend`。Safari 访问 `http://localhost:5173/`，API 默认 `http://127.0.0.1:8000`。真实模型密钥只进后端环境变量。
