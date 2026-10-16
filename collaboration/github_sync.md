# GitHub 提交与同步指南

2026-10-16，DOC-PROGRESS-SYNC-01；Codex辅助zhy。本文是操作指引，未执行提交、推送、PR或分支创建。

## 当前仓库核对

- 当前分支`main`，本地HEAD为`67a76a9 init`；有大量尚未提交的实现、测试、文档与自制样例，不只是本轮文档修改。
- SSH远程已配置：`origin = git@github.com:HAOYI0727/Hustudy.git`，无需重复添加。
- 本地分支记录为`main`与`origin/main`；远端实时状态须执行`git fetch origin`后核对，未联网确认更多分支。
- `.env`、`data/`运行数据、依赖、构建产物、测试临时输出和生成的Office runtime已按规则忽略。`data/.gitkeep`与`.env.example`是预期保留的骨架/配置样例。
- `frontend/tsconfig.tsbuildinfo`已被Git跟踪；即使以后加忽略规则也不会自动停止跟踪。本次取消暂存其生成差异，后续如需彻底停止跟踪，应另做明确的仓库维护提交。
- 当前已有两份个人报告删除：`hustudy/Hustudy_AI协作与人工核实记录.md`、`hustudy/Hustudy_课程实验提交包说明.md`。文档同步没有恢复或重新删除；提交前核对是否保留这些既有删除。

## 提交当前阶段快照

在仓库根目录执行。下列`git add -A`会暂存所有现有改动（含新增文件与删除），适用于一并同步当前阶段实现；不能把它描述成仅修改README的提交。

```bash
git fetch origin
git switch -c feature/platform-materialhub
git add -A
git restore --staged -- frontend/tsconfig.tsbuildinfo
git diff --cached --check -- . ':!docs/licenses/**' ':!frontend/public/third-party-notices.txt' ':!fixtures/*.pdf'
git diff --cached --stat
git status --short
```

确认暂存范围，尤其是两份个人报告删除与新增自制资料/截图。保留`.env.example`，不将真实`.env`或用户资料强制加入。若某项删除不在本次提交范围，用`git restore --staged -- <对应路径>`只取消暂存，工作区删除状态保留。

现有实现的测试证据为10-15后端116项、10-16前端14Vitest/42项双引擎与类型/构建通过，见[测试报告](../docs/test_report.md)。本轮仅文档校正，没有重跑业务测试；暂存后如继续改代码，按[工作流程](workflow.md)补相应验证。

确认后提交并推送功能分支：

```bash
git commit -m "feat(platform): integrate tested shared platform and MaterialHub"
git push -u origin feature/platform-materialhub
```

`frontend/tsconfig.tsbuildinfo`仍显示工作区修改是预期结果；不要为获得干净状态覆盖它或覆盖其他未提交内容。以后在该分支新增修改时使用普通`git push`，不要重复创建分支或强制推送。

## PR、合并与验证

1. 在GitHub仓库创建`feature/platform-materialhub → develop`的PR，填写需求/任务ID、迁移0001–0012、实际测试日期/命令、未完成P0、证据与handoff链接。
2. 若远端尚无`develop`，由队长先从远端`main`建立集成分支，再提交PR；不将未评审代码直接推到`main`。这一分支准备工作尚未执行。
3. 成员本人复验并记录签收，队长集成到`develop`；满足演示/发布条件后再按流程合并`main`。
4. 推送后可用`git rev-parse HEAD`与`git ls-remote origin refs/heads/feature/platform-materialhub`比较提交ID；一致才记录该分支已同步。将实际commit/PR链接补回个人进度及[handoff](handoff.md)，不能预填已合并。

GitHub源码同步不部署网站，也不替代课程要求的Gitee/Wiki和真实用户反馈记录。

提交复核补充：上游许可证、聚合第三方声明和PDF样例的xref结构保留原始空白，不为了Git空白提示改写；check仅排除上述声明文件，其余新增源码/文档仍检查。
