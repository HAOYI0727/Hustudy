# 账户独立API配置与验收（2026-10-24）

用户明确要求将网站API接入由后端全站共享改为每个账户使用自己的智谱API Key。本轮在Hustudy-gcx3修改共享设置、M2及题库AI凭据适配；先更新AGENTS与契约，没有修改Hustudy-main-1024历史副本，没有读取或自动使用用户真实密钥。

## 当前行为

- 每个账户独立保存Key、文本模型、配置修订及连接测试状态；登录切换即切换对应设置。A保存/更换/清除不会影响B。
- 无个人Key时，真实问答、学习报告、题库AI识别/归类/视觉转写明确提示未配置；不回退到.env、旧ai-connection.json、其他账户或停用的note-ai密钥。
- 后台根据任务user_id取得凭据，校验资源归属、预览修订和现有发送确认。更换Key/模型、重新保存相同Key或清除都会递增个人revision，使旧预览及后续批次失效；已经发出的请求无法撤回，迟到结果不会采纳。
- 问答和报告沿用120秒窗口、有限修复和显式续跑；题库原识别/核验/评分业务保持。视觉第一阶段后清除Key，会阻止后续核验调用。
- 每次配置连接测试只在本人明确同意后发送固定短文本，不包含课程资料。网络期间不持配置文件锁；返回后检查本人revision，丢弃迟到状态。其他人的配置变化不导致本人的测试失效。
- 仍仅支持智谱和现有模型。题库视觉/归类按现行能力使用glm-5.3-flash，资料问答/报告使用本人选择的文本模型；未开发多平台或自动付费回退。M3旧笔记AI整理仍停用。

## 存储与接口

`GET/PUT/DELETE /api/v1/api-connection`、`POST /api/v1/api-connection/test`沿用原路径，但scope改为account。服务端仅使用current_user，不能从请求指定其他账户。PUT和测试的revision为严格非负整数，测试confirm必须严格true；空Key可以保留本人已有Key，不能借用服务器Key。

个人配置位于storage_root的父目录下`api-connections/{user_id}.json`。UUID路径隔离，HKDF包含账户UUID并结合服务端JWT主密钥派生后使用Fernet加密，原子替换和短时跨进程文件锁保护修订。密钥不回显、不进入日志、前端localStorage、账户ZIP或资料导出。复制A的密文到B也不能解密使用。

服务端必须保留原JWT主密钥和私有配置目录，才能在重启后读取原个人配置。账户备份刻意不迁移密钥，恢复账户/换后端后需重新输入。该目录属于运行数据，不能加入GitHub上传副本。

新增个人配置使用独立文件，不需要数据库表或迁移，不复活旧note-ai设置。旧.env和机器共享文件保留原样，但不作为网站账户的AI回退，也不自动分配给第一个登录用户。原configure_zhipu脚本只写旧环境配置，不能代替现在网页中的个人Key保存。

## 这次升级如何使用

1. 停止原后端并重启，让API与默认托管worker加载新代码；前端Ctrl+F5刷新。无需装依赖或创建环境。
2. 登录自己的账户，进入“API接入”，重新粘贴完整智谱模型标准API Key并保存。旧共享Key不会自动沿用，即使升级前页面显示已配置。
3. 若要检查真实可用性，勾选短文本发送同意再点“测试连接”；可能消耗少量额度。保存成功不等于模型服务已经验证可用。
4. 回到AI学习或题库，重新生成预览并明确确认。旧共享预览、改Key前的旧预览需要重新核对，成功历史结果仍可阅读。
5. 此后保存/修改/清除个人配置立即生效，不必再重启服务；设置页面说明会提示仅影响本人。

后端普通命令：

```powershell
Set-Location 'E:\aa大学\大三上\软件工程\Hustudy\Hustudy-gcx3'
$env:PYTHONUTF8 = "1"
python -m uvicorn app.main:app --app-dir backend --reload --reload-dir backend/app
```

完整解释器版本（替换最后一行）：

```powershell
& 'E:\Anaconda\python.exe' -m uvicorn app.main:app --app-dir backend --reload --reload-dir backend/app
```

后端终端先Ctrl+C。默认自动托管worker，无需第三个终端；若关闭托管并单独运行worker，也须重启该worker。前端若已关闭，在另一个根目录终端执行：

```powershell
npm run dev --prefix frontend
```

## 手工检查

用两个浏览器配置文件或普通/隐私窗口分别登录A与B，避免同一localStorage登录令牌互相覆盖。

| 操作 | 预期 |
|---|---|
| A保存Key，B尚未配置 | A显示已保存；B仍未配置，不能使用A的AI额度 |
| B保存自己的Key或选择不同文本模型 | A原配置保持，双方看到各自的模型和测试状态 |
| B清除配置，A刷新状态 | 只有B变成未配置；A仍可用 |
| A预览后更换Key，再确认旧预览 | 返回配置改变提示，要求重新预览 |
| A开始多步任务后清除Key | 不再追加调用或采纳迟到结果；成功部分依原规则保留 |
| 导出并恢复账户 | 不含个人Key；新账户需重新配置 |

没有第二份真实Key时，可以先检查“A配置、B未配置”的隔离，不必为了测试另外申请或发送真实请求。自动测试覆盖两份假Key的实际HTTP Authorization，见下节。

## 不消耗额度的自动测试

项目根目录运行二选一：

```powershell
python -m pytest backend/tests/test_account_ai_isolation.py backend/tests/test_api_connection.py -q
```

```powershell
& 'E:\Anaconda\python.exe' -m pytest backend/tests/test_account_ai_isolation.py backend/tests/test_api_connection.py -q
```

预期16项通过，只有临时账户、自制材料和MockTransport，没有真实模型请求。覆盖加密/复制密文失效、两账户worker各自Authorization、全局配置不回退、本人清除及他人修改、同Key重存修订、连接迟到、题库真实worker、视觉两阶段阻断和备份恢复无密钥。

浏览器专项（现有Chrome，临时API8056/前端5178）：

```powershell
$env:HUSTUDY_TEST_PYTHON = 'E:\Anaconda\python.exe'
$env:HUSTUDY_E2E_CHROME_CHANNEL = 'chrome'
npm run test:e2e --prefix frontend -- --config=playwright.m2.config.ts --project=chromium account-api.spec.ts
```

## 实际验证结果

- 个人密钥及设置联合专项：16 passed、1个既有Pillow提示（6.80秒）。新增两个M4实际派发/视觉阻断用例是在全量收集后补入，已在该专项验证，不冒称包含于先前全量数字。
- 最后全量后端：542 passed / 13 failed / 5 skipped（173.08秒）。13项与接手基线一致：9项题库PDF/OCR可选组件缺失，3项Windows权限/可执行位/符号链接前提，1项M4目录顺序敏感断言；没有新增失败，未修改这些断言或无关业务。
- 前端196项/33文件通过（1.75秒），类型/生产构建通过（Vite689毫秒），本轮相关Python Ruff通过。
- 浏览器首轮17项中原M2/阅读报告15项通过、2项新双账户用例在模型下拉框标签定位超时；为模型框补充明确aria-label并使用combobox角色定位后，两项390/1440px复验通过（17.3秒），共17个不同场景验证通过，不累加重复次数。
- 第一轮全量曾有3项新失败：旧测试仍调用被移除的共享配置函数，以及配置改变/旧停用题目任务的原错误被最终来源检查覆盖。已更新测试为真实个人设置路径并修正错误保留，最后全量没有这3项失败。原修订、取消、权限断言未放宽。
- 一次备份测试试图在同库保留原业务UUID时恢复，按既有契约正确拒绝；改为纯个人配置空业务账户测试密钥排除，不修改UUID冲突保护。

本轮未自动调用真实API，未提交GitHub，未代签真实课程质量、成员接收或部署。所有代码修改在gcx3，历史1024副本另行指纹核对。
