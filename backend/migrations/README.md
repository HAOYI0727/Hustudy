# Alembic migrations

成员 A 统一维护迁移。当前应用启动会用 `Base.metadata.create_all` 建立 Phase 0 表，正式集成前应生成并提交第一版 Alembic revision，再移除开发期自动建表。
