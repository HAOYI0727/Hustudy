# 标准JWT与会话体验

2026-10-15，PLATFORM-AUTH-02，正式A02/FR-01/NFR-06。Codex辅助zhy实施，工作区未提交/合并，本人审阅/成员接收待填。范围为共享认证、配置/初始化、统一401及登录失效提示；不修改M2–M4内部实现或数据库。

使用[PyJWT 2.15.1](https://pypi.org/project/PyJWT/2.15.1/)替换自定义两段签名，按[官方API](https://pyjwt.readthedocs.io/en/stable/api.html)固定HS256、issuer/audience、必需claims；进一步检查UUID、整数时间、access用途与JWT类型。没有根据不可信头部选择算法，拒绝旧格式/none/其他算法/过大输入。401保留WWW-Authenticate与统一request_id。

密码hash和用户/课程UUID不变；现有账户重新登录即获得新JWT，旧两段令牌不继续接受。后端密钥最少32字符且隐藏配置repr/校验错误输入；setup生成64字符随机签名密钥，只替换空值/已知开发占位，保留既有有效密钥与智谱配置，原子写入.env0600。没有在本文记录密钥或访问令牌。

前端收到401显示“登录状态已失效，请重新登录。已保存的数据仍保留在账户中。”；登录表单补autocomplete/长度约束与可读错误。当前不提供刷新令牌、服务端登出撤销或长时间会话续期能力。无数据库迁移。

新增22个JWT确定性风险场景，涵盖错误issuer/audience/用途/UUID/时间、缺少必需claim、none/HS384/未知crit/类型、旧格式、过大/畸形、换密钥、重复登录保留课程、401挑战，以及配置初始化幂等/符号链接拒绝/GLM配置保持。初次定向25 passed（1.20秒），测试签名长度警告已加长测试密钥修正。

最终bash scripts/check.sh退出0：**89 passed，15.44秒**；Ruff、迁移/ORM漂移、笔记及AI回答安全、PDF双页实际渲染、TypeScript/Vite通过。日志/tmp/hustudy-auth-02.log；1条Starlette/anyio弃用警告及主包522.19KB提示保留。Safari登录/失效完整交互本切片未执行，不冒记为浏览器验收。依赖按MIT核实并保留[许可证](../../licenses/PyJWT-MIT.txt)。

标准JWT格式缺口已补实现；A02完整浏览器删除、会话恢复/人工审阅仍待验收。API升级说明见[contracts](../../contracts.md)，不据此标全部队长职责完成。
