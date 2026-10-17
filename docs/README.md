# Hustudy 文档导航

最新M2：[逐题知识点与已有结果复用](gcx/topics_reuse_2026_10_17.md)。原文中的“尚无缓存/全部知识点统一附加”描述按时间保留，当前以本记录为准。

## 2026-10-16 M2继续推进（最新要求）

用户授权M2不再按轮换日期刻意分段，能独立交付的P0持续提前完成；日期仅作团队协调，不作为停工条件。当前已接入真实三模式/三题型候选、固定自制报告/题目演示、精确片段、问答历史与错误细分。M4正式章节映射/试卷集成、M1教师标注和M4完整确认映射/统计契约仍为真实依赖；学科质量、实机和签收需要实际验收。当前状态见docs/gcx/m2_plan.md及candidate_acceptance.md（相对本项目根）。以下保留前一切片和历史进度，不以旧“待后续”覆盖当前结果。


## 2026-10-16 当前协作变更

用户确认：gcx=B/M2，xtc=D/M4，fzk=M3、zhy=共享层/M1。gcx开发时段为10月16–17日、10月24–25日、11月1日；xtc使用原gcx时段。11月5–6日完善网站与汇报。当前使用GitHub网页手动上传，不要求本地Git或新建Python环境；历史分支/角色描述保留为当时记录。当前唯一分工见collaboration/roles.md。

本轮M2-STUDY-REPORT-01由Codex辅助gcx实现真实章节报告，覆盖预览/确认/任务/结构化讲解/例题/自测/引用/笔记草稿/历史。详见docs/gcx/m2_plan.md和docs/gcx/study_report_acceptance.md；M4真实题目候选、教师/真题标签与完整学科质量验收仍待后续，不标整个M2或P0完成。


公共文档维护全站唯一契约、操作与集成结论。四人成员目录维护各自的功能、优化、设计和实际证据，任务状态通过 collaboration 与统一交接连接。

## 公共文档

| 文档 | 用途 |
|---|---|
| [contracts.md](contracts.md) | 共享实体/状态/引用与跨模块变更意图 |
| [api.md](api.md) | 公共 API 与消费说明；详细实现以 schema/OpenAPI 为准 |
| [decisions.md](decisions.md) | 架构与技术决策的历史及当前调整 |
| [user_guide.md](user_guide.md) | 已实现的资料整理/阅读操作；完整指南仍在完善 |
| [setup_guide.md](setup_guide.md) | 环境操作；最新启动/检查入口以根 README 为准 |
| [progress.md](progress.md) | 队长汇总的真实集成进度，历史结果按日期保留 |
| [traceability.md](traceability.md) | 需求、实现、测试与未完成边界 |
| [test_report.md](test_report.md) | 全站实际检查结果与验收范围；不代替个人证据 |
| [third_party.md](third_party.md) | 依赖/资源许可证核实；licenses/ 保存必要声明 |

## 个人记录

| 成员 / 模块 | 技术入口 | 进度 |
|---|---|---|
| zhy：共享层 + M1 | [zhy/README.md](zhy/README.md) | [collaboration/zhy](../collaboration/zhy/progress.md) |
| xtc：M2 AI Study | [xtc/README.md](xtc/README.md) | [collaboration/xtc](../collaboration/xtc/progress.md) |
| fzk：M3 NoteGraph | [fzk/README.md](fzk/README.md) | [collaboration/fzk](../collaboration/fzk/progress.md) |
| gcx：M4 ExamPilot | [gcx/README.md](gcx/README.md) | [collaboration/gcx](../collaboration/gcx/progress.md) |

每人维护 features.md（功能输入/输出/异常与真实验收）、optimizations.md（优化问题/变化/验证与限制）；按需要增加设计和证据。通过 [handoff.md](../collaboration/handoff.md) 交接，队长用链接汇总，不复制成多套共享契约。新目录不改变代码模块边界，也不证明成员已完成实验。

规则见 [AGENTS.md 第 20 节](../AGENTS.md#20-四人文档隔离与统一交接规则)。正式需求与个人课程报告仍保持原有位置及本人审阅要求。

最新[测试报告](test_report.md)区分2026-10-15后端116项与2026-10-16前端14Vitest、42项Chrome/WebKit完整回归/类型构建，不把文档同步写成重新测试。队长完成边界见[核查](zhy/completion_audit.md)，正式任务见[zhy任务表](../collaboration/zhy/task_status.md)。

近期证据：[原格式预览](zhy/materialhub/native_preview_acceptance.md)、[检索/容量/重建](zhy/materialhub/search_capacity_acceptance.md)、[多端布局](zhy/shared_platform/responsive_layout_acceptance.md)、[视觉与截图](zhy/shared_platform/visual_polish_acceptance.md)。技术材料按[共享基础层](zhy/shared_platform/README.md)、[M1](zhy/materialhub/README.md)、[集成协助](zhy/integration/README.md)分类，历史报告不替代最新状态。提交推送步骤见[GitHub指南](../collaboration/github_sync.md)。
