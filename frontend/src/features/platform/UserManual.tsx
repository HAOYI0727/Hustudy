import {useEffect,useRef,useState} from "react";
import {WorkspaceDialog} from "../../components/WorkspaceDialog";
import {Icon} from "../../components/Icon";
import {AIAnswerPreview} from "../ai/AIAnswerPreview";
import {manualChapters,readManual,type ManualChapter} from "./manual";
import manualUrl from "../../../../user.md?url&no-inline";
import materialUrl from "../../../../fixtures/learning_loop_material.md?url&no-inline";
import questionsUrl from "../../../../fixtures/learning_loop_questions.md?url&no-inline";
import demoUrl from "../../../../fixtures/materialhub_demo.md?url&no-inline";
import "./user-manual.css";

export function UserManual(){
  const [open,setOpen]=useState(false),[retry,setRetry]=useState(0);
  const [chapters,setChapters]=useState<ManualChapter[]>([]),[selected,setSelected]=useState(""),[query,setQuery]=useState("");
  const [state,setState]=useState<"idle"|"loading"|"ready"|"failed">("idle"),[error,setError]=useState("");
  const content=useRef<HTMLElement>(null);
  useEffect(()=>{
    if(!open)return;
    let live=true;const controller=new AbortController();setState("loading");setError("");
    void readManual(manualUrl,controller.signal).then(text=>{
      if(!live)return;const rows=manualChapters(text);setChapters(rows);setSelected(rows[0].id);setQuery("");setState("ready");
    }).catch(reason=>{if(live){setState("failed");setError(reason instanceof TypeError?"网络或网站暂不可达，请恢复连接后明确重试。":reason instanceof Error?reason.message:"手册暂不可读，请重试。");}});
    return()=>{live=false;controller.abort();};
  },[open,retry]);
  const keyword=query.trim().toLocaleLowerCase();
  const visible=chapters.filter(chapter=>(chapter.title+"\n"+chapter.markdown).toLocaleLowerCase().includes(keyword));
  const current=chapters.find(chapter=>chapter.id===selected);
  return <><section className="panel user-manual-entry" aria-label="完整手册与闭环示例"><div><p className="eyebrow">READ · TRY · CONTINUE</p><h3><Icon name="file"/>完整使用手册与示例</h3><p>按课程、阅读、笔记、题库与复习查找操作；用自制示例走完学习闭环。</p></div>
    <div className="manual-actions"><button className="primary" onClick={()=>setOpen(true)}>阅读完整使用手册</button><a className="secondary" href={manualUrl} download="Hustudy使用手册.md"><Icon name="download" size={16}/>下载完整手册</a></div>
    <div className="manual-samples" aria-label="下载学习示例"><a href={materialUrl} download="learning_loop_material.md">下载传输层资料示例</a><a href={questionsUrl} download="learning_loop_questions.md">下载配套题库示例</a><a href={demoUrl} download="materialhub_demo.md">下载固定报告演示资料</a></div><p className="hint">下载不会导入或创建学习数据。前两份用于同一课程的阅读→笔记→练习→错题回源；固定报告演示仅支持第三份操作系统材料。</p>
  </section>
  <WorkspaceDialog open={open} title="Hustudy完整使用手册" onClose={()=>setOpen(false)} className="user-manual-dialog">
    {state==="loading"?<p role="status">正在读取完整使用手册…</p>:state==="failed"?<div className="inline-retry" role="alert">{error}<button className="secondary" onClick={()=>setRetry(value=>value+1)}>重试读取手册</button></div>:state==="ready"&&<div className="manual-layout"><aside className="manual-directory" aria-label="手册章节目录"><label>查找章节与示例<input aria-label="查找手册章节" maxLength={160} value={query} onChange={event=>setQuery(event.target.value)} placeholder="例如：PPT、公式、备份、冲突"/></label><p className="hint" role="status">匹配{visible.length} / {chapters.length}章；搜索只筛选目录，当前阅读保留。</p>{query&&<button className="text-button" onClick={()=>setQuery("")}>清除手册查找</button>}
      <nav aria-label="选择手册章节">{visible.map(chapter=><button className={selected===chapter.id?"is-selected":""} aria-current={selected===chapter.id?"page":undefined} key={chapter.id} onClick={()=>{setSelected(chapter.id);content.current?.scrollTo({top:0});requestAnimationFrame(()=>{content.current?.focus({preventScroll:true});content.current?.scrollTo({top:0});});}}>{chapter.title}</button>)}</nav>{!visible.length&&<p className="hint">没有匹配章节，可换一个词或清除查找。</p>}</aside>
      <article ref={content} className="manual-content" tabIndex={-1} aria-label="手册章节正文">{current&&<AIAnswerPreview content={current.markdown}/>}</article>
    </div>}
  </WorkspaceDialog></>;
}
