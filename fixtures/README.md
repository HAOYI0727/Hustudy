# Fixtures

新增`learning_loop_material.md`与`learning_loop_questions.md`为项目自制传输层闭环体验材料；题库示例和`question_bank_demo.md`均采用当前`# Hustudy 题库 v1`严格Markdown格式，可直接从本地入口或资料库版本导入：配套3选择题/1解答题，没有新填空题或真实用户内容。根user.md说明先上传题库原件并从版本导入以保留原题出处，讲义来源另行确认到知识点；网站使用指南提供显式下载，不自动导入或调用模型。原`materialhub_demo.md`的固定报告演示仍仅适配操作系统材料。

仅放自制或已获授权的小型测试资料。当前尚未加入真实课程文件，避免把未核实版权材料提交到仓库。

materialhub_demo.md 为自制 Markdown 上传/目录/中文搜索/引用回源样例，不是教师课件或官方真题。后端 test_materialhub.py 在临时目录自行生成 PPTX、DOCX、PDF 和图片样本，不写入用户账户。

preview_demo.pdf：2026-10-14 使用 pypdf 自制的两页英文图示，仅用于页号/PNG 渲染/截图来源验证，不含用户课件内容；正文有明确的 Page 1/Page 2 标记。由 scripts/verify_pdf.mjs 核对两页输出不同和越界拒绝。

[GLM课程问答自制样例](glm_qa_demo.md)用于真实模型的可选连通验证。发送问题可用“两个加三个苹果共有多少个？”。只发送这份自制资料和问题，不能把其他用户课件加入自动验收；真实请求不纳入默认测试命令。

preview_demo.pptx与preview_demo.docx：2026-10-15由scripts/create_preview_fixtures.py使用python-pptx/python-docx生成的自制英文原页预览样例，不读取用户文件。PPTX共2张，第二张明确设为隐藏，要求导出仍保留；DOCX含正文段落/表格及后续段落。供真实LibreOffice转换及浏览器截图来源验收，可运行生成脚本复现。

`no_text_demo.pdf`：自制单页空白PDF，无可提取正文；用于原页仍可预览、人工补录草稿/确认/撤回与引用失效的浏览器验收。不是OCR识别样本。可通过 `scripts/create_preview_fixtures.py` 与Office样例一同重建。组合PPTX由 `backend/tests/test_grouped_pptx.py` 在临时目录生成，不包含用户课件。

`native_preview.pptx` / `native_preview.docx` 由 `scripts/create_native_preview_fixtures.py` 自制：PPT两页（第二页隐藏）含字号/背景/表格/自绘PNG；Word两阅读页含粗体、表格、图片、显式换页及不得自动加载的外部链接。用于原格式渲染、隔离和模式保持验收，不含用户课件；不是Office全版式基准或OCR样本。
