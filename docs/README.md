# Hustudy 文档目录

更新：2026-11-07。根目录四份文档分别承担[项目复现](../README.md)、[完整操作手册](../user.md)、[设计主方案](../main_idea.md)、[四人协作进度](../Hustudy_team_collaboration.md)。它们描述当前行为；本目录保存接口与实施证据，带日期的报告仅代表当时范围。

## 四名成员

| 目录 | 对应模块 | 内部组织 |
| --- | --- | --- |
| [zhy](zhy/README.md) | 队长、共享层+M1 MaterialHub | shared_platform共享机制；materialhub资料；integration跨模块；history历史与协作归档 |
| [gcx](gcx/README.md) | M2 AI Study | design方案/schema；acceptance验收与评估；history阶段实现/交接；evidence与既有验收样例 |
| [fzk](fzk/README.md) | M3 NoteGraph | acceptance验收/审计；evidence正式保留证据；根features/optimizations功能与优化 |
| [xtc](xtc/README.md) | M4 ExamPilot | formats严格格式；implementation原docs/m4说明与验收；history日期记录；根features/optimizations |

旧docs/m4已经并入xtc/implementation，不再另设第五个业务模块目录。成员目录保留原文、真实日期和验收状态，不能根据迁移目录认定个人贡献或签收。

## 公共必要文档

- [contracts.md](contracts.md)：共享数据、状态和跨模块契约。
- [api.md](api.md)：API与错误说明。
- [decisions.md](decisions.md)：技术决策。
- [progress.md](progress.md)：公共进度历史。
- [traceability.md](traceability.md)：需求与测试追踪。
- [test_report.md](test_report.md)：带日期测试记录，不作当前全量保证。
- [third_party.md](third_party.md)与[licenses](licenses)：第三方声明与完整许可。licenses是必须保留的公共合规材料，不是第五位成员。
- [setup_guide.md](setup_guide.md)、[user_guide.md](user_guide.md)：跳转到唯一现行复现和手册入口，避免重复维护过期版本。
- [四方面验收准备](final_acceptance_2026_10_30.md)：历史准备记录，最终结果以实际重跑/人工确认核对。
- [本轮目录整理](zhy/shared_platform/repository_organization_2026_11_07.md)：迁移、数据保留、路径和测试说明。

未来实验与进度按成员目录新增，接口变更只维护公共契约，不再建立同一模块的平行目录。运行截图、trace和临时模型结果默认放根.artifacts，不写入正式docs/evidence；需要正式保存时挑选、脱敏并注明范围。
