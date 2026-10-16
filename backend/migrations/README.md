# Alembic migrations

成员 A 统一维护迁移。应用启动使用 Alembic upgrade head，已移除运行时 create_all。

- 0001：冻结初版表结构；只接受结构匹配的无版本历史库，保留已有数据和 UUID。
- 0002：不可变版本元数据、任务尝试次数/租约、FTS5 表。
- 0003：同资料版本号唯一约束、历史切片重新索引、补排历史文档预览任务。
- 0004：资料分类与 JSON 标签。
- 0005：图片版本/预览页来源；SQLite 在真实事务内重建图片表，临时保留/恢复原 AssetReference，外键始终开启；故障回滚测试与旧引用 UUID 保留测试通过。

- 0006：独立 ManualTranscript、当前页确认唯一约束、Chunk/Citation 来源类型；旧 UUID 不变。
- 0007：图片展示名（按原始文件名回填）、JSON 标签、整理 revision；仅追加列，不重建已有图片/引用表。
- 0008：MaterialExport与课程/任务外键，原表/用户内容不重建；MATERIAL_EXPORT任务由资料worker处理。该资料包不等于完整账户备份。

已有 SQLite 数据库升级前通过 SQLite backup API 生成 `.pre-migration-<UTC时间>.bak`。升级失败时先保留数据库及备份并人工排查，不支持自动降级。备份只涵盖数据库，不是含附件的个人知识库备份。

验证：`PYTHONPATH=backend .venv/bin/python scripts/verify_migrations.py` 在临时库升级至 head 并检查 ORM 漂移；`backend/tests/test_migrations.py` 验证历史库数据/引用身份保留。FTS5 虚拟表及其 shadow tables 由迁移管理，从自动生成对比中排除。
