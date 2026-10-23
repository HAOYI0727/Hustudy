# Workers

M1/M2/M3/M4共用持久任务worker；HTTP只保存原件/入队，耗时工作不在上传请求执行。常驻模式使用独立兼容预览执行道，核心解析/索引无需等待Office转换；既有租约/取消/次数预算保持。

开发API默认管理worker生命周期和退出重启；外部worker已持锁时不重复创建，API关闭仅终止自己创建的子进程。`HUSTUDY_WORKER_AUTOSTART=false`可关闭，production默认外部管理。`python -m app.workers.materials`独立运行，常驻重复实例退出73；`--once`保留显式单次处理，不用于部署守护。`.runtime`仅本机心跳/OS锁，不入业务schema或账户备份；GET状态需要登录且不返回PID/路径。

部署及测试边界见[可靠性与部署](../../../docs/zhy/shared_platform/worker_deployment.md)。
