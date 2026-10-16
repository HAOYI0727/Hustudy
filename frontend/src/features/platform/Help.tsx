import { Icon } from "../../components/Icon";

export function Help({ onNavigate }: { onNavigate: (section: "materials" | "notes" | "ai" | "exam" | "review") => void }) {
  const steps = [
    { id: "materials" as const, title: "导入与阅读", text: "上传课件，整理分类和标签，通过目录与原文查找阅读，再连接笔记。", icon: "file" as const },
    { id: "notes" as const, title: "整理自己的理解", text: "选择学习模板，记录概念与例子，用双链连接相关笔记。", icon: "notes" as const },
    { id: "ai" as const, title: "提问并核对来源", text: "在课程内提问，核对回答证据，再决定是否保存为笔记草稿。", icon: "ai" as const },
    { id: "exam" as const, title: "审阅后开始练习", text: "整理真题、配置题数与分值；模拟卷先审阅，确认后再作答。", icon: "exam" as const },
    { id: "review" as const, title: "回到薄弱的地方", text: "查看已提交练习产生的错题，完成待复习任务。", icon: "review" as const },
  ];
  return <div className="page"><section className="search-hero"><p className="eyebrow">YOUR LEARNING COMPANION</p><h2>从一份课件，到真正理解。</h2><p>按你的节奏开始，也可以直接进入需要的工具。</p><span className="help-mode"><Icon name="ai" size={15}/>AI模式按次选择</span></section>
    <div className="learning-guide">{steps.map((step, index) => <button key={step.id} onClick={() => onNavigate(step.id)}><span className="guide-number">0{index + 1}</span><span className="guide-symbol"><Icon name={step.icon} size={26}/></span><strong>{step.title}</strong><p>{step.text}</p><small>开始这一步 →</small></button>)}</div>
    <div className="help-columns"><section className="panel"><h3>使用前，了解这些</h3><details open><summary>演示模型能做什么？</summary><p>演示模式展示原文摘录；真实课程问答可选择智谱GLM，先预览片段并逐次确认发送。演示检索不代表理解了任意上传资料。请核对原文；模拟题不预测教师考试。</p></details><details><summary>为什么课件显示为文本？</summary><p>PDF 可打开原页；PPTX 和 DOCX 可直接打开原格式预览，也可使用 LibreOffice 转换的兼容 PDF。原格式或转换失败时，仍可阅读已提取的结构化文本。DOCX 引用按正文块定位，预览页码不等同于 Word 原文页码。扫描件可查看原页，在原始 PDF 中手工补录文字；保存草稿后核对并确认，才能检索和引用。OCR 尚未实现。</p></details><details><summary>怎样保护未保存的笔记？</summary><p>填写标题后，停止编辑约两秒会自动保存。离开前请查看保存状态；冲突时保留本地草稿，核对服务端版本后再处理。</p></details><details><summary>如何导出和备份？</summary><p>已保存笔记可在笔记工作台导出 Markdown。资料阅读中的课程资料包可导出各版本原件、文本、确认补录和图片/来源清单。“备份与恢复”页面可生成完整账户ZIP，并校验后恢复到新数据库的空账户；源对象仍在同库会因UUID冲突拒绝。笔记附件ZIP仍待完善，课程资料包不能恢复导入。</p></details></section>
    <section className="panel capability-panel"><p className="eyebrow">AVAILABLE TODAY</p><h3>当前可用的学习工具</h3><ul><li>资料分类、标签、版本、PPT/Word/PDF 预览与人工补录</li><li>按分类、标签和版本范围查找课程原文</li><li>笔记模板、自动保存、Markdown 预览与双链</li><li>图片整理与查找、当前页截图、回源、笔记嵌入与课程资料包导出</li><li>演示检索、确认发送的智谱课程问答、模拟练习与错题复习</li></ul><div className="capability-next"><strong>后续完善</strong><p>笔记附件ZIP、真实章节报告与真题统计。语义检索、OCR 和间隔复习属于后续增强。</p></div><button className="secondary" onClick={() => onNavigate("review")}>遇到问题？提交反馈 →</button></section></div>
  </div>;
}
