import {useEffect,useRef,useState} from "react";
import {api, type NoteOptionPage, type AISupplementSelection, type AISource} from "../../api/client";

type Props={token:string;courseId:string;value:AISupplementSelection;onChange:(value:AISupplementSelection)=>void;disabled:boolean};

export function SupplementInputs({token,courseId,value,onChange,disabled}:Props){
  const [page,setPage]=useState<NoteOptionPage|null>(null),[q,setQ]=useState(""),[error,setError]=useState(""),[loading,setLoading]=useState(false),[note,setNote]=useState<{title:string;content:string}|null>(null);
  const serial=useRef(0);
  useEffect(()=>()=>{serial.current++;},[]);
  useEffect(()=>{serial.current++;setPage(null);setNote(null);setError("");},[courseId,token]);
  const request=async(action:()=>Promise<void>)=>{const current=++serial.current;setLoading(true);setError("");try{await action();}catch(e){if(current===serial.current)setError(e instanceof Error?e.message:"读取补充资料失败，请重试");}finally{if(current===serial.current)setLoading(false);}};
  const load=async(offset=0)=>{const current=serial.current+1;await request(async()=>{const result=await api.noteOptions(token,courseId,q,offset,20);if(current===serial.current)setPage(result);});};
  return <details className="ai-privacy-card"><summary>补充笔记 · 可选</summary>
    <p className="hint">个人笔记仅补充理解，不替代课件原文。AI生成的笔记也须先由你检查；未选择时不会发送笔记正文。</p>
    <fieldset disabled={disabled||loading}><legend>选择补充笔记（最多5篇、正文合计12000字符）</legend>
      <label>查找笔记<input value={q} onChange={e=>setQ(e.target.value)} maxLength={200}/></label><button type="button" className="secondary" onClick={()=>void load()}>查找课程笔记</button>
      {page&&<><div className="ai-scope-options">{page.items.map(item=><div key={item.id}><label><input type="checkbox" checked={value.note_ids.includes(item.id)} disabled={!value.note_ids.includes(item.id)&&value.note_ids.length>=5} onChange={e=>onChange({...value,note_ids:e.target.checked?[...value.note_ids,item.id]:value.note_ids.filter(id=>id!==item.id),notes_confirmed:false})}/>{item.title}</label><button type="button" className="secondary" onClick={()=>void request(async()=>{const current=serial.current;const body=await api.note(token,item.id);if(current===serial.current)setNote(body);})}>核对正文</button></div>)}</div>
      {!page.items.length&&<p>没有匹配的笔记。</p>}<p>共{page.total}篇</p><button type="button" className="secondary" disabled={!page.offset} onClick={()=>void load(Math.max(0,page.offset-20))}>上一页</button><button type="button" className="secondary" disabled={page.offset+page.items.length>=page.total} onClick={()=>void load(page.offset+20)}>下一页</button></>}
      {note&&<details open><summary>{note.title} · 个人笔记正文</summary><pre style={{whiteSpace:"pre-wrap",maxHeight:240,overflow:"auto"}}>{note.content}</pre></details>}
      <p>已选{value.note_ids.length}篇 <button type="button" className="secondary" disabled={!value.note_ids.length} onClick={()=>onChange({...value,note_ids:[],notes_confirmed:false})}>清空笔记选择</button></p>
      {value.note_ids.length>0&&<label className="ai-consent"><input type="checkbox" checked={value.notes_confirmed} onChange={e=>onChange({...value,notes_confirmed:e.target.checked})}/>我已核对选中笔记，包含AI草稿的内容也已检查，同意将其作为个人补充资料。</label>}
    </fieldset>
    {loading&&<p role="status">正在读取补充资料…</p>}{error&&<p role="alert">{error}</p>}
  </details>;
}

export function SupplementPreview({value}:{value?:AISource["m2_supplement"]}){
  if(!value||(!value.notes.length&&!value.teacher_marks.length&&!value.exam_evidence.length))return null;
  return <div className="ai-privacy-card"><strong>本次补充笔记与自动检测依据</strong><p className="hint">笔记正文将发送至模型；教师强调和真题依据由服务端核对，不作为额外模型输入，也不向模型发送题目答案。</p>
    {value.notes.map(n=><details key={n.id}><summary>个人补充笔记：{n.title} · 修订{n.revision}</summary><pre style={{whiteSpace:"pre-wrap",maxHeight:240,overflow:"auto"}}>{n.content}</pre></details>)}
    {value.teacher_marks.map((m,i)=><p key={i}>教师强调（阅读标记）：{m.reason} · {m.quote}</p>)}
    {value.exam_evidence.map((e,i)=><p key={i}>已确认真题：{e.paper_title} · {e.year??"年份未知"} · {e.topic_name}</p>)}

  </div>;
}
