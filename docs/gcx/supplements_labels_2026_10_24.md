# M2：补充笔记与自动报告来源标签（2026-10-24当前实现）

> **接手必读：尚缺两个上游接口。** M1/zhy需实现阅读片段“教师强调”的保存/查询，并在API和worker注册reader；M4/xtc需实现明确真题身份的确认/保存入口及有效映射。M2已有消费、快照、标签和失效校验，模拟测试不是上游已实现的证据。字段与联合验收见[本轮交接](handoff_2026_10_24.md)。正常无记录时保持AI建议，不恢复手动事实表单。

用户明确纠正上一版：报告页只保留补充笔记；“教师强调”来自阅读时的片段标记，“已确认真题”来自已确认题目关系，均应由系统自动检测。M2-AUTO-LABEL-SOURCES-03覆盖02的手动录入方案。本轮仅修改Hustudy-gcx3，Hustudy-main-1024历史副本不改。

## 当前界面

问答和学习报告只有“补充笔记 · 可选”，可查找/选择当前课程笔记、核对正文、确认后预览发送。教师填写、原文选择、课堂说明和真题选择控件已全部移除；报告请求也不再接受相应手动字段。

补充笔记保持最多5篇/正文合计12000字符、完整预览、修订/正文hash快照、明确发送确认和120秒执行窗口。笔记只补充理解，不能冒充课件引用或教师事实；修改/移课/删除后旧预览拒绝派发，历史提示失效。

## 自动检测逻辑

报告预览时读取本次原文范围对应的依据并冻结，确认/每次派发和修复/结果采纳/续跑/复用时重新核对。生成报告时，服务端将已确认依据与每个知识点实际引用相交后附加标签。模型输出仍只能是AI建议，不能自行声称事实来源。

| 来源 | 检测条件 | 缺少或失效 |
|---|---|---|
| 教师强调 | 当前用户、当前课程、所选版本片段存在active且本人确认的teacher_emphasis阅读标记；摘录确实在发送范围，且与知识点引用相交 | 保持AI建议，不从课件文字/笔记标签猜测 |
| 已确认真题 | 同账户课程内，卷被上游明确确认为past_exam，卷/题已核验；人工确认知识点映射；映射课件原文有效且与本次知识点引用相交 | 保持AI建议，不把普通题库、自动分类或名称相似当真题 |

有依据时显示“教师强调”“已确认真题”及其证据；同一类型的两种依据可以并存。历史依据撤回/变化/新增后显示stale，不改写生成时快照，不继续复用旧输入。

**目前正常网页测试仍可能全部显示AI建议，这是预期。** 当前项目未实现阅读片段教师标记的存储/查询入口，也未提供明确真题身份元数据的录入入口。M2已经具备读取适配、校验、快照、按引用判断及失效分支，但不能称这两项上游录入功能已完成。这一轮不新增阅读页面功能，不改变M1/M3/M4写入业务。

## 后续上游如何接入

### M1阅读标记

`backend/app/services/reading_report_evidence.py`提供只读边界。M1实现持久标记查询后，在API和worker各自启动时调用`install_reader(reader)`接入；它是代码集成入口，没有HTTP设置或用户脚本入口。未接入时返回空记录。

读取器接收`db,user_id,course_id,sources`，返回有界记录，字段为：

- id/user_id/course_id/version_id/chunk_id：UUID；revision：正整数。
- status=active、mark_type=teacher_emphasis、confirmed=true。
- kind=key/difficult/exam，quote为原文连续摘录（最多500字），reason为说明（最多1000字）。

M2再次核对归属、定位、实际发送范围和引用，只接收符合契约的记录，最多200条。未确认、撤回、越权或不在发送范围内的记录不参与来源判断，不自动创建任何标记。

### M4真题关系

`backend/app/services/exam_report_evidence.py`复用既有核验题库、知识点来源和题目映射自动查询。明确真题身份约定为卷的`bank_meta_json.exam_identity={"kind":"past_exam","confirmed":true}`，由M4后续确认流程负责写入；M2不猜测、不补写。仍须卷/题CONFIRMED、映射selection_reviewed=true及有效课件来源。最多100项有关映射，超限明确提示缩小范围。

普通题库即使全部核验，也不等于确认属于真题。现在没有明确身份的记录就不触发，避免把现有测试题库都显示为真题。

以上新自动快照version=2。旧version=1的手动来源历史仍可只读查看，但旧手动预览不能确认/续跑/复用为新自动报告，须重新预览。v8及更早报告历史不隐藏。

## 你现在如何测试

1. 重启后端（默认托管worker随同重启），浏览器Ctrl+F5刷新。无需安装依赖、执行迁移或新建环境。
2. 进入学习报告，确认只有“补充笔记 · 可选”，里面没有教师填写或真题选择。
3. 不选笔记正常生成一次报告；没有上游依据时，标签应保持AI建议。
4. 在测试课程新建简短笔记，选择并核对正文、勾选确认，生成预览。实际发送前应显示完整笔记，再由你确认调用模型。
5. 修改所选笔记后尝试确认旧预览，应要求重新预览；原成功结果保留旧快照并提示依据变化。

无需人为制造教师/真题记录来完成网页验收。有/无/撤回依据的底层判断用下方隔离测试验证，后续接通上游数据再进行真实闭环测试。

重启后端的普通命令：

```powershell
Set-Location 'E:\aa大学\大三上\软件工程\Hustudy\Hustudy-gcx3'
$env:PYTHONUTF8 = "1"
python -m uvicorn app.main:app --app-dir backend --reload --reload-dir backend/app
```

完整解释器版本（替换最后一行）：

```powershell
& 'E:\Anaconda\python.exe' -m uvicorn app.main:app --app-dir backend --reload --reload-dir backend/app
```

后端终端先Ctrl+C；若手动关闭自动托管并独立运行worker，也要重启独立worker。前端若已关闭，在另一个项目根终端运行`npm run dev --prefix frontend`。

## 不消耗API的自动测试

```powershell
python -m pytest backend/tests/test_m2_supplements.py -q
```

或完整解释器版本：

```powershell
& 'E:\Anaconda\python.exe' -m pytest backend/tests/test_m2_supplements.py -q
```

使用临时库、自制材料、模拟模型和模拟上游记录，不读取或更改日常数据，不调用真实API。覆盖笔记确认/权限/修改/发送、自动标记命中和零记录回退、越权/撤回标记排除、已确认真题映射、普通题库不升格、来源变化失效、旧手动输入拒绝、续跑/复用及历史兼容。

```powershell
npm test --prefix frontend -- ai-supplements.test.ts
```

可选桌面/窄屏浏览器验证：

```powershell
$env:HUSTUDY_TEST_PYTHON = 'E:\Anaconda\python.exe'
$env:HUSTUDY_E2E_CHROME_CHANNEL = 'chrome'
npm run test:e2e --prefix frontend -- --config=playwright.m2.config.ts --project=chromium ai-supplements.spec.ts
```

## 验证记录

- 报告/执行预算/长资料/来源联合专项101通过（29.88秒）；随后复用/固定演示/结构与容量/历史/真题分析专项37通过（9.63秒）。最终新增旧手动预览停用用例后，来源专项37通过；重叠不累加。
- 前端196项/33文件通过（2.16秒），类型/生产构建通过（Vite860毫秒），相关Python Ruff通过。
- Chrome桌面/390px专项15项全部通过（1.1分钟）：笔记入口简化/自动来源零记录回退、执行预算、复用、学习报告和阅读助手。
- 核对历史指纹891文件，Hustudy-main-1024未修改。
- 一次测试命令误写不存在的test_ai_result_reuse.py，未运行任何测试；随后改用实际test_ai_topics_reuse.py并通过，不把未运行算作通过。

本轮没有把更正前527通过/12既有失败的全量运行冒充为当前全量重跑。真实学科质量、上游存储/录入和成员签收不代填；没有调用真实API。
