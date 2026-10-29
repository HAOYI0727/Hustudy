# 专注笔记导航、多模型与笔记助手

2026-10-27，Codex辅助fzk；M3-NOTE-ASSISTANT-05 / PLATFORM-MODEL-CONNECTIONS-01。分支 `codex/fzk-m3-safe-merge`。原阅读模式与可选保存用户已验收；用户已于2026-10-27明确反馈本轮验收通过，原第9项继续暂缓；团队接收独立记录。

## 使用入口

- 笔记 → 阅读模式 → 专注阅读：默认“全部笔记”，按课程、文件夹及标题查找，每页30篇；父目录包含后代，未归档可单独筛选。切换后保持专注，“本篇目录”定位当前正文。列表只读元数据，打开时才获取正文，未保存切换沿原确认。
- 页面上方“当前AI模型 / 配置更多模型”，或原“API接入”页下方“其他模型与兼容接口”：保存多份DeepSeek或Chat Completions兼容配置。原智谱区继续独立保存和测试，切换当前模型不覆盖它。
- 编辑工具“笔记AI”：摘要、解释内容、整理结构、复习问题、自定义处理。可选全文或打开助手前的选文；核对完整发送文字、模型及地址后确认生成。预览结果后追加、替换选区或明确替换全文。采纳修改草稿，可撤销/重做；保存沿原手动/可选自动设置。

其他成员页面只补共享模型选择、能力刷新与必要提示；M2引用/分批预算、M4校正/确认业务沿原规则。切换模型令旧发送预览失效，运行任务不会静默改用另一份凭据。

## 模型与输入边界

模型ID可编辑，DeepSeek接口为 `https://api.deepseek.com/chat/completions`；参数依据[官方对话补全文档](https://api-docs.deepseek.com/api/create-chat-completion/)，包括可选thinking/JSON输出。需填写实际有权调用的模型；“已配置”不是连接成功或输出质量保证。兼容接口需支持本项目结构化对话约定，并非所有厂商协议通用。

每账户最多8份配置。密钥经现有账户派生加密保存在服务端私有目录，不回显、不进入浏览器存储或课程/账户导出。HTTPS主机白名单可由部署者通过 `HUSTUDY_ADDITIONAL_AI_HOSTS` 扩展（逗号分隔主机名），改部署设置需重启；不接受HTTP、本机地址、凭据URL、重定向或代理。图片能力显式声明，未开启时拒绝图片调用。保存/切换不触发调用，连接测试需同意发送短文本。

笔记助手只发送本次文本，不读取其他笔记或图片原件；正文≤24000字符、补充要求≤2000字符、输出≤12000字符。10分钟预览授权绑定账户、来源版本、文本与模型配置。单账户单请求处理中，10分钟最多20次，失败不自动重试。成功请求同一身份可取回结果，未知结果不重复发送。正文/配置变化、关闭/401、迟到响应不能覆盖当前草稿。结构整理校验内部双链/图片令牌，不允许增造内部引用；事实和公式语义仍需人工核对。

新功能不恢复旧识别任务的AI整理或直接新建接口。文字/语音识别仍核对后以文本插入；助手不自动新建笔记、标签、题库或已核实来源。无新依赖和数据库迁移；重启后端/托管worker，保存工作后刷新前端。

## 课程包样例与人工复验

运行 `python scripts/generate_note_assistant_sample.py`，默认输出到工程旁 `Hustudy验收样例/多模型与笔记助手-20261027`。可用 `--output` 指定另一个工程外目录。生成器使用临时数据库、普通业务API及自制材料，不连接日常服务或真实模型。

| 文件 | 内容 |
|---|---|
| `01-笔记阅读与AI助手验收课程.zip` | 标准课程包：40篇笔记（含32篇分页样例及验收说明）、6个文件夹、2张图片、1份资料、双链与资料引用；另有自制题库/练习和固定演示结果供共享入口核对 |
| `02-跨课程导航补充.zip` | 第二门课程和1篇笔记，用于专注窗口跨课程导航 |
| `课程包验收说明.txt` | 逐步操作及预期结果，同样嵌入主课程的00说明笔记 |
| `课程包验证结果.json` | 实际对象计数、SHA-256、新建回导/追加合并/关系校验/幂等结果 |

在课程总览“标准数据包”分别导入两份ZIP，新建两门课程，打开主课程 `00-先读我-验收步骤` 按顺序操作。无需手工上传散落Markdown。包中没有API Key；真实模型质量及账号权限需本人配置验证。标准包按关系清单保存笔记，并非供外部Markdown软件阅读的普通笔记ZIP。

生成器已实际验证两包：导入后全部笔记获得新身份，图片文件存在，双链指向新副本，资料引用匹配新资料；再次合并不会覆盖旧笔记/课程信息，重复请求不重复创建。主包与补充包合并后分别有80/2篇笔记。这不代签原第9项或跨机器完整备份验收。

## 自动验证

均使用临时账户/数据库和模拟HTTP模型响应，不发送真实笔记或消耗API额度；浏览器使用8056/5178。

- 后端集成：`pytest backend/tests/test_model_connections.py backend/tests/test_m2_execution.py backend/tests/test_remote_ai.py backend/tests/test_qa_batches.py backend/tests/test_bank_vision.py backend/tests/test_bank_topic_ai.py backend/tests/test_account_ai_isolation.py backend/tests/test_note_ai_config.py -q --tb=short`：143通过、1跳过。覆盖M2实际worker派发、引用/预算、M4能力及账户隔离，不代表全量后端测试。
- 补配置损坏/首次选择后，`pytest backend/tests/test_model_connections.py -q --tb=short`：20通过；再补兼容视觉JSON开关及所选模型元数据，`pytest backend/tests/test_model_connections.py backend/tests/test_bank_vision.py backend/tests/test_bank_topic_ai.py -q --tb=short`：58通过、1跳过（包含最终22项新配置/助手用例）。此前与旧账户隔离/停用配置组合回归34通过；测试重叠不累计计数。
- `npm.cmd run test --prefix frontend`：39文件、248单元通过；`npm.cmd run check --prefix frontend` 通过；更新站内手册后的 `npm.cmd run build --prefix frontend` 生产构建通过，包含Office/数学资源及类型检查。
- Chrome/WebKit定向复验24项通过（5.9分钟），含390/1440目录分页/跨课/草稿保护、五类助手任务、确认/采纳/撤销、关闭迟到/401、原智谱双账户隔离及只读来源回跳。frontend目录命令：

```powershell
$env:HUSTUDY_E2E_CHROME_CHANNEL='chrome'
node node_modules/@playwright/test/cli.js test note-assistant.spec.ts account-api.spec.ts note-reading.spec.ts --grep '个人API|阅读引用只读|专注|笔记AI|模型|助手'
```

首轮32项中27通过、5失败：原账户测试依赖本机默认模型，来源回跳未等待冷加载的真实片段请求。改为显式选择测试模型、等待片段响应并保留业务断言；上述24项包含全部失败场景。新增功能首轮12项均通过。Ruff新增源码/生成器检查通过；桌面及窄屏截图已核对。日志/图片在忽略的 `.tools/models-*`、`.tools/note-assistant-*`、`.tools/focus-library-*`。

接收人：fzk及队长，M2/M4成员核对共享模型消费。真人质量、实机和团队接收待本人记录；本轮提交验证统一见完成审计。
