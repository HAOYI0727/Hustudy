# 自行选题组卷

题库练习增加第三种方式「自行选题组卷」。用户先按题干字面包含及单个知识点筛选，再跨页勾选题目，按勾选顺序生成练习。知识点搜索复用现有名称、别名和层级组件，筛选父标签包含其下级。每页20题，每套最多100题。

GET /courses/{course_id}/question-bank/practice-questions 接收 query、topic_id、offset，返回 items、total。只列当前账户、当前课程已确认且来源有效的题目，不返回答案。不同记录的重复题保留。

POST /courses/{course_id}/question-bank/manual-practice 接收 request_id、question_ids、title、duration_minutes。生成时重新校验所有题目，任何一题失效则整体拒绝。沿用练习快照、请求幂等、作答、判分、自评和错题流程，保留选项顺序。

本轮隔离后端自选与整卷相关测试5项通过，前端TypeScript检查通过。真人页面验收单独进行。
