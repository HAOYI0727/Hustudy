# 后端测试目录

所有用例使用根conftest.py建立的临时数据库/文件，不能连接日常data或真实Key。

| 子目录 | 范围 |
| --- | --- |
| shared | 认证、账户、课程、存储、迁移、模型配置、worker与共享记录/日程 |
| m1 | 上传、解析/预览、资料整理、人工补录、索引与权限 |
| m2 | 资料问答/报告、提示词、来源、预算/续跑及历史复用 |
| m3 | 笔记、图片、引用、识别、导出、图谱及回收站 |
| m4 | 题库、答案导入、标签、统计、组卷/作答、错题与计划 |
| integration | 跨模块来源、笔记、课程包与完整主流程 |
| support | 共用模拟账户模型辅助；不作为业务实现 |

从仓库根运行`PYTHONPATH=backend .venv/bin/python -m pytest -q`；定向例如`PYTHONPATH=backend .venv/bin/python -m pytest backend/tests/m1 -q`。模块之间使用tests.<组>.<文件>显式导入，禁止再依赖平铺目录的隐式同级搜索。根conftest与__init__.py需保留。
