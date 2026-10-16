# Hustudy 四人协作入口

本目录是代码仓库中的协作交接入口，和 `AGENTS.md`、`Hustudy_team_collaboration.md`、`docs/contracts.md` 一起使用。成员为 zhy（A 共享层 + M1）、xtc（B M2）、fzk（C M3）、gcx（D M4）；本目录中的状态只在真实完成并有证据后更新。

截至2026-10-16：共享层/M1核心自动验收通过，A01–A08 Review、A09/A10 Doing；M2–M4仍有P0待办，模块本人评审/接收未代填。当前功能看根README，实际证据看docs/test_report，发生过程看handoff。

- [project_handoff.md](project_handoff.md)：新成员复现环境、当前进度、四模块后续任务、验收步骤和排查说明。
- [handoff.md](handoff.md)：每个切片持续追加的变更、验证、接收和集成日志；与环境指南分工不同。

- [roles.md](roles.md)：四个模块的负责人、边界、输入输出和建议分支。
- [task_board.md](task_board.md)：首版 P0 任务、需求 ID、验收方式和当前状态。
- [github_sync.md](github_sync.md)：当前仓库GitHub功能分支提交、推送和PR步骤。
- [workflow.md](workflow.md)：分支、评审、契约变更、环境和交接流程。
- [roadmap.md](roadmap.md)：P0 完成后的优化、创新和 P1/P2 边界。

任何成员开始任务前，先检查 `git diff`、当前迁移、`docs/progress.md` 和共享契约；完成后附测试命令、真实输出和未完成风险。

## 四人独立记录入口

| 成员 | 个人任务与进度 | 功能与优化 |
|---|---|---|
| zhy | [zhy/README.md](zhy/README.md) | [docs/zhy](../docs/zhy/README.md) |
| xtc | [xtc/README.md](xtc/README.md) | [docs/xtc](../docs/xtc/README.md) |
| fzk | [fzk/README.md](fzk/README.md) | [docs/fzk](../docs/fzk/README.md) |
| gcx | [gcx/README.md](gcx/README.md) | [docs/gcx](../docs/gcx/README.md) |

本目录根级维护公共角色、任务板、约束、操作与交接；成员目录维护 progress.md，技术证据放入 docs 同名目录。已有 [集成历史](integration_2026_10_13.md) 与 [体验路线](experience_roadmap.md) 保留为跨模块公共记录。

zhy当前正式A01–A10状态见[个人任务表](zhy/task_status.md)，技术完成判断见[核查](../docs/zhy/completion_audit.md)。早期任务板使用聚合编号，其历史Done不表示正式十任务或全部P0完成；当前判断与历史过程分开维护。

提交/PR 前更新个人记录并追加交接；接收人填写实际复验后由队长汇总到公共进度/追踪。xtc/fzk/gcx 初始文件是待本人填写的模板，不能把现有仓库或队长会话的 AI 辅助实现计为其本人实验。完整约束见 [AGENTS.md 第 20 节](../AGENTS.md#20-四人文档隔离与统一交接规则)。
