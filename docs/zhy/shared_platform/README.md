# zhy 共享基础层技术证据

本目录保存认证/课程/生命周期等共享层的具体实现与验收报告。当前完成边界以[完成度核查](../completion_audit.md)为准；报告按发生日期保存，不把历史待办当最新状态。

| 文档 | 范围 |
|---|---|
| [课程整理验收](course_organization_acceptance.md) | 课程分类/标签/局部修改、revision冲突与Safari证据 |
| [基本回归与课程删除验收](basic_acceptance.md) | 有效课程授权、模块同事务清理、失效来源与回滚、认证风险 |

公共API/schema/架构决定仍唯一维护在docs根级，不在此复制。当前JWT、存储、备份、前端与环境进度见下方具体报告；未完成的正式验收/发布见[zhy任务表](../../../collaboration/zhy/task_status.md)。

- [标准JWT与会话验收](auth_jwt_acceptance.md)
- [统一存储/低磁盘验收](storage_acceptance.md)

- [完整账户备份/空账户恢复验收](account_backup_acceptance.md)

- [前端路由/会话与双引擎验收](web_base_acceptance.md)

- [干净源码环境重建与容量证据](../materialhub/search_capacity_acceptance.md)（共享层/M1联合验收）

- [全站响应式与统一密度验收](responsive_layout_acceptance.md)（电脑/平板/手机、抽屉/草稿/原格式阅读）

- [统一视觉与交互状态验收](visual_polish_acceptance.md)（主色/文字/按钮/语义图标，42项双引擎）
