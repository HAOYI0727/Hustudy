# Repositories

所有业务查询在 repository 层显式接收 `user_id`，避免跨用户读取。成员 A 先建立共享查询基类，再由各模块扩展。
