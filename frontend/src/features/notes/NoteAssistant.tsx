import {useEffect,useRef,useState} from 'react';
import {api,type NoteSummary,type NoteAssistantInput,type NoteAssistantPreview,type NoteAssistantResult} from '../../api/client';
import {sessionPartition} from '../../api/query';
import {NotePreview} from '../../components/knowledge';
import {ModelControl} from '../platform/ModelConnections';
import './note-assistant.css';

export type AssistantSource={session:number;title:string;content:string;start:number;end:number;noteId?:string;revision?:number;courseId:string};
export type AssistantApply='append'|'selection'|'replace';
export function NoteAssistant({token,source,notes,onApply,onError}:{token:string;source:AssistantSource;notes:NoteSummary[];onApply:(text:string,mode:AssistantApply)=>string;onError:(error:unknown)=>void}){
  const [task,setTask]=useState<NoteAssistantInput['task']>('summary'),[scope,setScope]=useState<'full'|'selection'>(source.end>source.start?'selection':'full');
  const [instruction,setInstruction]=useState(''),[preview,setPreview]=useState<NoteAssistantPreview|null>(null),[result,setResult]=useState<NoteAssistantResult|null>(null),[consent,setConsent]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const controller=useRef<AbortController|null>(null),serial=useRef(0);
  const invalidate=()=>{serial.current++;controller.current?.abort();setPreview(null);setResult(null);setConsent(false);setBusy(false);setError('');};
  useEffect(()=>{const changed=(event:Event)=>{if((event as CustomEvent).detail===sessionPartition(token))invalidate();};window.addEventListener('hustudy:model-changed',changed);return()=>{serial.current++;controller.current?.abort();window.removeEventListener('hustudy:model-changed',changed);};},[token]);
  const text=scope==='selection'?source.content.slice(source.start,source.end):source.content;
  const input:NoteAssistantInput={course_id:source.courseId,...(source.noteId?{note_id:source.noteId,revision:source.revision}:{}),task,scope,text,instruction};
  const execute=async(generate=false)=>{
    const current=++serial.current;controller.current?.abort();const abort=new AbortController();controller.current=abort;setBusy(true);setError('');
    try{if(generate&&preview){const answer=await api.generateNoteAssistant(token,input,preview.preview_token,abort.signal);if(current===serial.current)setResult(answer);}
      else{const next=await api.previewNoteAssistant(token,input,abort.signal);if(current===serial.current){setPreview(next);setResult(null);setConsent(false);}}}
    catch(e){if(current===serial.current&&!abort.signal.aborted){setError(e instanceof Error?e.message:'笔记AI处理未完成');onError(e);}}
    finally{if(current===serial.current)setBusy(false);}
  };
  const adopt=(mode:AssistantApply)=>{if(!result)return;if(mode==='replace'&&!window.confirm('用已核对的AI结果替换当前全文？可以撤销，保存沿当前手动或自动方式处理。'))return;const problem=onApply(result.markdown,mode);if(problem)setError(problem);};
  return <section className="note-assistant" aria-label="笔记AI助手">
    <ModelControl token={token} onError={onError} disabled={busy}/>
    <p className="hint">当前笔记：{source.title||'未命名笔记'}。AI结果先预览，由你选择采纳；采纳后按当前保存方式处理。</p>
    <fieldset disabled={busy}><div className="note-assistant-fields"><label>处理任务<select aria-label="笔记AI任务" value={task} onChange={e=>{invalidate();setTask(e.target.value as NoteAssistantInput['task']);}}><option value="summary">总结要点</option><option value="explain">解释内容与选文</option><option value="organize">整理Markdown结构</option><option value="review">生成复习问题与参考答案</option><option value="custom">自定义处理</option></select></label>
    <label>发送范围<select aria-label="笔记AI发送范围" value={scope} onChange={e=>{invalidate();setScope(e.target.value as 'full'|'selection');}}><option value="full">当前笔记全文</option><option value="selection" disabled={source.end<=source.start}>打开助手前选中的文字</option></select></label></div>
    <label>补充要求<textarea aria-label="笔记AI补充要求" maxLength={2000} rows={3} value={instruction} placeholder="例如：保留公式，按概念、例子、易错点组织" onChange={e=>{invalidate();setInstruction(e.target.value);}}/></label>
    <p className="hint">本次 {text.length} / 24000 字符。只发送文本，不上传图片原件或其他笔记；长笔记可先选中一段处理。</p>
    <button className="secondary" disabled={!text.trim()||text.length>24000||(task==='custom'&&!instruction.trim())} onClick={()=>void execute()}>预览发送内容</button></fieldset>
    {error&&<p role="alert">{error}</p>}{busy&&<p role="status">正在处理；关闭窗口会停止本页等待。</p>}
    {preview&&<section className="note-assistant-preview" aria-label="笔记AI发送预览"><h4>{preview.task} · {preview.model}</h4><p className="hint">{preview.endpoint}</p><details><summary>查看本次完整发送文本（{preview.characters}字符）</summary><pre>{preview.text}</pre>{preview.instruction&&<p>补充要求：{preview.instruction}</p>}</details><p className="hint">{preview.notice} 可能消耗服务商额度。</p>
      <label className="note-assistant-consent"><input type="checkbox" aria-label="同意发送笔记文本" disabled={busy||!!result} checked={consent} onChange={e=>setConsent(e.target.checked)}/>我已核对范围和模型，同意本次发送上述文本。</label>
      {!result&&<button className="primary" disabled={busy||!consent} onClick={()=>void execute(true)}>确认发送并生成</button>}</section>}
    {result&&<section className="note-assistant-result" aria-label="笔记AI建议"><h4>AI建议 · {result.model}</h4><p className="hint">请核对事实、公式和引用；尚未写入笔记，复习问题不是真题。</p><NotePreview content={result.markdown} token={token} notes={notes} onNote={()=>{}}/>
      <details><summary>查看Markdown源码</summary><pre>{result.markdown}</pre></details><div className="note-assistant-actions"><button className="primary" onClick={()=>adopt('append')}>追加到笔记末尾</button>{source.end>source.start&&<button className="secondary" onClick={()=>adopt('selection')}>替换原选中文字</button>}<button className="secondary" onClick={()=>adopt('replace')}>替换全文…</button></div></section>}
  </section>;
}
