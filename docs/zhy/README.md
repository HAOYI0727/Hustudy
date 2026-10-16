# zhy：个人技术与验收记录

成员：张昊轶｜A 队长｜共享基础层 + M1 MaterialHub。

**截至2026-10-16，核心自动验收通过，正式评审/交付仍未全部完成。** 先读[完成度核查](completion_audit.md)和[正式A01–A10任务状态](../../collaboration/zhy/task_status.md)。两表分别维护技术证据与任务调度；历史验收报告中的测试数量、待办和编号不替代当前状态。

| 分类 | 入口 | 维护内容 |
|---|---|---|
| 当前功能 | [features.md](features.md) | 按共享层、M1、跨模块集成列实际行为和边界 |
| 优化记录 | [optimizations.md](optimizations.md) | 变化动机、验证、限制，保留日期 |
| 共享基础层 | [shared_platform/](shared_platform/README.md) | 课程、生命周期与基础回归验收 |
| M1资料库 | [materialhub/](materialhub/README.md) | 资料任务、导出、解析/预览/图片等证据及缺口演进 |
| 队长集成协助 | [integration/](integration/README.md) | GLM等M2–M4业务的队长辅助记录，业务主责不变 |
| 历史日志 | [history/features_2026_10_13-15.md](history/features_2026_10_13-15.md) | 逐轮功能记录，保留原有结果和未决项 |

- [features.md](features.md)：实现的功能、输入/输出、异常、调用入口和验证边界。
- [optimizations.md](optimizations.md)：优化的问题、前后行为、取舍、真实验证与风险。
- [个人进度](../../collaboration/zhy/progress.md)、[统一交接](../../collaboration/handoff.md)。

可以按任务增加 design/、tests/、evidence/ 等材料，使用任务 ID 和日期命名，并从上述记录链接。AI 提示词、采纳/修改/否决、人工核实与课程实验必须按本人实际使用记录，不自动生成“本人已核实”。

公共 [API](../api.md)、[契约](../contracts.md)、[决策](../decisions.md) 与 [需求追踪](../traceability.md) 保持唯一；个人文件只说明具体实现并链接公共定义。密钥、用户私有文件与运行数据库不放入证据目录。

下列报告是具体日期的历史证据；最新未完成项以完成度核查为准。

2026-10-14 [MaterialHub 缺口分析](materialhub/materialhub_gap_analysis.md)：当时缺口、优先切片、依赖与验收边界。

2026-10-14 [课程资料包验收及队长A01–A10关口](materialhub/material_export_acceptance.md)：40项测试、共享恢复修复、Safari实际导出下载/hash校验与仍未完成的任务。

2026-10-14 [课程整理与验收](shared_platform/course_organization_acceptance.md)：正式A02、FR-02/09、0009/43项检查、Safari持久化/双标签页冲突与父需求剩余关口。

2026-10-14 [基本功能回归与课程删除](shared_platform/basic_acceptance.md)：47项检查、跨模块撤权/失败回滚/迟到结果、Safari确认保护与全部P0剩余关口。

2026-10-14 [智谱真实课程问答验收](integration/zhipu_qa_acceptance.md)：GLM接口核对、后端配置、67项检查/自制真实请求、确认/引用/异常/取消及剩余关口。

2026-10-15新增[共享前端/会话/环境验收](shared_platform/web_base_acceptance.md)：10项Vitest、8项Chrome/WebKit闭环和独立Python3.12回归；剩余关口已同步当前核查与任务表。

2026-10-15新增[M1预览恢复验收](materialhub/preview_recovery_acceptance.md)：LibreOffice实际转换、Safari兼容、隐藏幻灯片定位与110项后端/14项浏览器结果。

- [M1检索/解析完整性、容量与环境验收](materialhub/search_capacity_acceptance.md)

- [原格式直接预览与兼容PDF](materialhub/native_preview_acceptance.md)

最新界面证据见[多端布局](shared_platform/responsive_layout_acceptance.md)与[统一视觉/截图](shared_platform/visual_polish_acceptance.md)；GitHub操作见[公共指南](../../collaboration/github_sync.md)，本轮文档同步未执行提交/推送。
