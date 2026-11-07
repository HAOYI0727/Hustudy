# 前端测试目录

unit与e2e下统一分shared、m1、m2、m3、m4、integration，含义与后端一致。Vitest和Playwright递归发现，无需手动枚举每个文件。

```bash
npm run test --prefix frontend
npm run test --prefix frontend -- tests/unit/m1
npm run test:e2e --prefix frontend -- --list
npm run test:e2e --prefix frontend -- m1/
npm run test:e2e --prefix frontend -- shared/user-manual.spec.ts integration/manual-learning-loop.spec.ts
```

Playwright使用临时8056/5178服务，默认两个浏览器项目、不复用日常服务。私有样本只在显式环境变量开启时使用；.artifacts/inputs中的样本选择器不入库，自制fixtures必须保留并纳入源码。

自动失败截图/trace：根.artifacts/playwright/test-results；显式采集的实验截图/指标：根.artifacts/e2e。旧local/local_only不再作为输出目录。不要让常规测试在docs或成员evidence目录产生新截图；正式证据由本人审阅筛选后保留。
