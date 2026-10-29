# fzk：M3 NoteGraph

成员：付振琨；实现与文档由Codex辅助。更新：2026-10-27。

## 当前入口

- [专注笔记导航、多模型与笔记助手](note_assistant_acceptance.md)：跨笔记/课程筛选翻页、保留智谱的DeepSeek/兼容模型接入、五类笔记AI任务及标准课程包样例；用户已确认本轮验收通过。
- [阅读模式与可选保存](note_reading_acceptance.md)：独立Markdown阅读、目录/字号/专注，默认手动且可选自动保存；用户已确认通过。

- [标准数据包与课程合并](portable_packages_acceptance.md)：自选ZIP导入／导出、追加到已有课程、工程外自动验收样例；用户确认本轮验收通过。

- [笔记关系图谱](note_graph_acceptance.md)：当前课程双链图、筛选与一跳聚焦，用户确认本轮验收通过。
- [逐段合并与草稿保护](note_merge_acceptance.md)：算法边界、测试与复验步骤，用户已反馈本人复验通过。

- [功能与使用](features.md)：笔记编辑、目录/标签、图片、导出、回收站和识别文本插入。
- [人工验收](manual_recheck.md)：第1–8、10–14项用户已确认；第9项仍暂缓，边界自动验证单独记录。
- [完成情况与提交验证](m3_completion_audit.md)：自动测试、迁移、依赖和待集成事项。
- [优化说明](optimizations.md)：设计取舍与实现边界。
- [个人进度](../../collaboration/fzk/progress.md)、[统一交接](../../collaboration/handoff.md)。

## 专项说明

- [目录、导入和批量整理](note_organization_acceptance.md)
- [工作区布局与拖动](note_workspace_acceptance.md)
- [图片与选择导出](note_batch_images_acceptance.md)
- [回收站](note_trash_acceptance.md)
- [识别文本插入](capture_text_acceptance.md)
- [Markdown和基础公式](note_math_editor_acceptance.md)
- [公式分类库与矩阵](formula_workspace_acceptance.md)
- [图形符号与结构输入](formula_graphic_input_acceptance.md)
- [标签接口验证](note_tags_acceptance.md)

专项文件保留相关自动验证证据；人工状态以本目录的验收表为准。已删除停用AI整理/API配置的旧操作指南，以及旧UUID/复杂清单ZIP的重复指南。公共API与数据契约以[API](../api.md)、[契约](../contracts.md)为准。
