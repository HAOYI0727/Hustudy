# Hustudy 四人协作入口

2026-10-23 [现有长PPT与知识点排版](../docs/zhy/materialhub/learning_layout_acceptance.md)、[交接019](handoff.md#h-20261023-zhy-019)：队长按用户追加反馈，用本机现有资料只读隔离测量与优化；原件、日常数据、业务主责和正式签收保持。

2026-10-23 [最新版本资料检查](../docs/zhy/materialhub/readiness_acceptance.md)、[交接018](handoff.md#h-20261023-zhy-018)：队长继续共享层/M1状态与恢复闭环，原历史任务及四模块业务保持，正式成员接收不代记。

2026-10-23 [原文关联错题与复习摘要](../docs/zhy/materialhub/source_reviews_acceptance.md)、[交接017](handoff.md#h-20261023-zhy-017)：队长继续M1/M4只读集成及共享回看路由，原成绩/计划/掌握规则保持，业务主责与正式签收不代记。

2026-10-23 [资料学习关联](../docs/zhy/materialhub/source_connections_acceptance.md)与[交接016](handoff.md#h-20261023-zhy-016)：队长继续四模块原文/成果/练习/错题集成，只读适配和原业务UUID，成员贡献及正式接收不代记。

2026-10-23 队长继续整合：07–11共享控件/彩色模块/字体/记录后端与所有分界面细化，跨四域只读消费、共享记录入口和旧草稿/权限保护。[总验收](../docs/zhy/integration/all_workspaces_acceptance.md)及[H-20261023-ZHY-012](handoff.md#h-20261023-zhy-012)，成员正式接收由本人。

2026-10-22 全站外观继续迭代：[研究](../docs/zhy/integration/appearance_research.md)、[功能与验证](../docs/zhy/integration/appearance_acceptance.md)、[H-20261022-ZHY-007](handoff.md#h-20261022-zhy-007)。仅共享展示/设备偏好，成员业务主责与接收不代填。

2026-10-22 M1阅读工具继续迭代：[书签/版本对照验收](../docs/zhy/materialhub/reading_tools_acceptance.md)、[H-20261022-ZHY-006](handoff.md#h-20261022-zhy-006)；Codex辅助zhy，其他模块主责与成员签收不变。

2026-10-22 H-20261022-ZHY-005：知识点只读学习中心及M1常用视图已自动验证，跨M1/M2/M3/M4的消费契约与官方设计研究已记录；成员接收仍由本人核对。 [实际范围与边界](../docs/zhy/integration/learning_hub_acceptance.md)。

2026-10-22 H-20261022-ZHY-004补充阅读连续性与按需正文，影响gcx/fzk/xtc消费；成员接收由本人复验填写。 [使用、验证与边界](../docs/zhy/integration/continuity_acceptance.md)。

2026-10-22 后续整合：H-20261022-ZHY-002已完成实现与隔离自动验证，待成员接收；不改变其他成员正式状态。[实现与验收](../docs/zhy/integration/learning_loop_acceptance.md)。

2026-10-22 队长最新核查：[四模块现状、正式40任务覆盖与下一步](../docs/zhy/integration/project_review_2026_10_22.md)。本轮共享路由/M1批量导入/M2来源适配见[交接H-20261022-ZHY-001](handoff.md#h-20261022-zhy-001)与[验收](../docs/zhy/integration/material_study_acceptance.md)。未代改成员正式接收状态；下方旧分工/候选/待办说明保留原日期。

## 2026-10-16 M2继续推进（最新要求）

用户授权M2不再按轮换日期刻意分段，能独立交付的P0持续提前完成；日期仅作团队协调，不作为停工条件。当前已接入真实三模式/三题型候选、固定自制报告/题目演示、精确片段、问答历史与错误细分。M4正式章节映射/试卷集成、M1教师标注和M4完整确认映射/统计契约仍为真实依赖；学科质量、实机和签收需要实际验收。当前状态见docs/gcx/m2_plan.md及candidate_acceptance.md（相对本项目根）。以下保留前一切片和历史进度，不以旧“待后续”覆盖当前结果。


## 2026-10-16 当前协作变更

用户确认：gcx=B/M2，xtc=D/M4，fzk=M3、zhy=共享层/M1。gcx开发时段为10月16–17日、10月24–25日、11月1日；xtc使用原gcx时段。11月5–6日完善网站与汇报。当前使用GitHub网页手动上传，不要求本地Git或新建Python环境；历史分支/角色描述保留为当时记录。当前唯一分工见collaboration/roles.md。

本轮M2-STUDY-REPORT-01由Codex辅助gcx实现真实章节报告，覆盖预览/确认/任务/结构化讲解/例题/自测/引用/笔记草稿/历史。详见docs/gcx/m2_plan.md和docs/gcx/study_report_acceptance.md；M4真实题目候选、教师/真题标签与完整学科质量验收仍待后续，不标整个M2或P0完成。


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
