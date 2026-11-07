# 环境与复现说明

现行安装、macOS/Linux及Windows启动、账户模型、可选Office/OCR和生产部署说明统一维护在[根README](../README.md#3-环境与快速复现)，完整测试入口见[手册第24章](../user.md#24-维护者启动与验收附录)。本文件保留兼容入口，不再复制时间线配置。

- 后端：Python3.11/3.12，开发默认托管worker；前端：Node24.x及npm。
- 原格式PPTX/DOCX/PDF无需LibreOffice；兼容PDF才需要转换器及启用配置。
- 真实AI在网页API接入中按当前账户配置，不沿用旧机器共享Key。
- 自动测试隔离8056/5178与临时数据，运行结果默认位于根.artifacts。
- 旧环境说明已在项目外整理备份保留，不能将历史Windows路径或旧三终端流程当作当前通用命令。
