# P0 任务板（初始状态）

状态：`Todo / Doing / Review / Done / Blocked`。下面的 `Done` 只表示当前骨架或本轮垂直切片已有代码与验证，不代表全部 P0 验收完成。

| 任务 | 负责人 | 需求 | 当前状态 | 验收证据 |
|---|---|---|---|---|
| A01 运行环境与应用工厂 | A | NFR-10 | Done | `README.md`、启动脚本 |
| A02 认证与课程归属 | A | FR-01–02/NFR-06 | Done | `routers/auth.py`、`courses.py` |
| A03 资料版本/切片/任务模型 | A | FR-03–05 | Doing | `models/material.py` |
| A04 四格式解析与关键词检索 | A | FR-04、06、09、36 | Doing | `services/materials.py`、`documents.py` |
| A05 文件预览/图片/导出/备份 | A/C | FR-08、14–15、37 | Todo | TC-05、09、27 |
| B01 Mock Provider 与证据状态 | B | FR-16–20 | Doing | `routers/ai.py`、API 冒烟 |
| B02 StudyReport 教学结构 | B | FR-18、38 | Doing | StudyReport schema/test |
| B03 真实 Provider 与预算 | B | FR-20、45 | Todo | TC-12 |
| C01 Markdown 笔记与 revision | C | FR-10–11 | Doing | `routers/notes.py` |
| C02 双链/反链/Citation | C | FR-12–13 | Doing | API 冒烟、TC-08 |
| C03 图片引用/导出/备份 | C | FR-14–15、37 | Todo | TC-09、27 |
| D01 真题导入/拆分/确认 | D | FR-39–40 | Doing | `routers/exams.py` |
| D02 Topic 映射与统计 | D | FR-35、41–43 | Todo | TC-29–30 |
| D03 蓝图/拟卷/审阅 | D | FR-21–24、44–45 | Doing | API 冒烟、TC-13–14 |
| D04 作答/错题/复习 | D | FR-25–30 | Doing | API 冒烟、TC-15–18 |
| I01 前端工作台与四模块导航 | A + 全员 | NFR-10 | Doing | `frontend/src/main.tsx`、Vite build |
| I02 权限/API/E2E/性能测试 | 全员 | NFR-02、06–10 | Todo | TC-21–25 |

真实姓名、Issue 链接、开始/结束日期由团队在 Gitee/GitHub 建仓后补充。
