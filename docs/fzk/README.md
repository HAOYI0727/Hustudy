# fzk：M3 NoteGraph

成员：付振琨；实现与文档由Codex辅助。更新：2026-10-19。

## 当前入口

- [功能与使用](features.md)：笔记编辑、目录/标签、图片、导出、回收站和识别文本插入。
- [人工验收](manual_recheck.md)：第1–8项通过；第9项暂缓。
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
