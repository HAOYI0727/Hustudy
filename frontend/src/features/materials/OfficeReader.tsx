import { FormEvent,useEffect,useRef,useState } from 'react';
import {api} from '../../api/client';
import {Icon} from '../../components/Icon';
import {officeFrameDocument} from './office/frame';

type Props={onPageChange?:(page:number)=>void;token:string;versionId:string;kind:'pptx'|'docx';name:string;initialPage?:number;compatibilityReady:boolean;onCompatibility:()=>void;onDownload:()=>void};
export default function OfficeReader({token,versionId,kind,name,initialPage=1,compatibilityReady,onCompatibility,onDownload,onPageChange}:Props) {
  const [srcDoc,setSrcDoc]=useState(''),[attempt,setAttempt]=useState(0);
  const [ready,setReady]=useState(false),[pending,setPending]=useState(true),[error,setError]=useState('');
  const [degraded,setDegraded]=useState(false),[presenting,setPresenting]=useState(false);
  const [page,setPage]=useState(initialPage),[input,setInput]=useState(String(initialPage)),[count,setCount]=useState(0),[zoom,setZoom]=useState(100);
  const frame=useRef<HTMLIFrameElement>(null),channel=useRef(''),terminated=useRef(false);
  const watchdog=useRef<ReturnType<typeof setTimeout>|undefined>(undefined);
  const typeLabel=kind==='pptx'?'PPT':'Word',pageLabel=kind==='pptx'?'幻灯片':'阅读页';
  const pageCallback=useRef(onPageChange);pageCallback.current=onPageChange;
  useEffect(()=>{if(ready&&!pending)pageCallback.current?.(page);},[ready,pending,page]);
  const fail=()=>{terminated.current=true;setError('原格式预览未能完成。可以重试、下载原件，或使用兼容 PDF 预览。');setPending(false);setReady(false);setSrcDoc('');};
  useEffect(()=>{
    let live=true,opened=false;const controller=new AbortController();
    const id=crypto.randomUUID();channel.current=id;terminated.current=false;
    setReady(false);setPending(true);setError('');setDegraded(false);setSrcDoc('');setCount(0);setZoom(100);setPage(initialPage);setInput(String(initialPage));
    let bytes:ArrayBuffer|undefined;
    const stopTimer=()=>{clearTimeout(watchdog.current);};
    const timeout=()=>{if(live){opened=true;fail();}};
    watchdog.current=setTimeout(timeout,25000);
    const receive=(event:MessageEvent)=>{
      const data=event.data;
      if(!live||terminated.current||event.source!==frame.current?.contentWindow||event.origin!=='null'||!data||data.channel!==id)return;
      if(data.type==='boot'&&!opened&&bytes){opened=true;const buffer=bytes;bytes=undefined;frame.current!.contentWindow!.postMessage({channel:id,type:'open',kind,page:initialPage,buffer},'*',[buffer]);}
      if(data.type==='state'&&Number.isInteger(data.count)&&data.count>0&&data.count<=2000&&Number.isInteger(data.page)&&data.page>0&&data.page<=data.count){stopTimer();setCount(data.count);setPage(data.page);setInput(String(data.page));setReady(true);setPending(false);}
      if(data.type==='error'){stopTimer();fail();}
      if(data.type==='degraded')setDegraded(true);
      if(data.type==='escape')setPresenting(false);
    };
    window.addEventListener('message',receive);
    void Promise.all([api.original(token,versionId,controller.signal).then(blob=>blob.arrayBuffer()),fetch(`${import.meta.env.BASE_URL}native-office/runtime.js`,{cache:'no-store',signal:controller.signal}).then(response=>{if(!response.ok)throw new Error('Preview runtime unavailable');return response.text();})])
      .then(([buffer,runtime])=>{if(!live||opened)return;bytes=buffer;setSrcDoc(officeFrameDocument(runtime,id,crypto.randomUUID()));})
      .catch(()=>{if(live){stopTimer();fail();}});
    return()=>{live=false;controller.abort();bytes=undefined;stopTimer();window.removeEventListener('message',receive);};
  },[token,versionId,kind,attempt,initialPage]);
  const navigate=(target:number,nextZoom=zoom)=>{
    if(!ready||pending)return;
    const next=Math.max(1,Math.min(count,target));setPending(true);setZoom(nextZoom);
    clearTimeout(watchdog.current);watchdog.current=setTimeout(fail,25000);
    frame.current?.contentWindow?.postMessage({channel:channel.current,type:'navigate',page:next,zoom:nextZoom},'*');
  };
  useEffect(()=>{
    const key=(event:KeyboardEvent)=>{
      if(event.key==='Escape')setPresenting(false);
      if(!presenting||!ready||pending||(event.target instanceof HTMLElement&&event.target.matches('input,textarea,select')))return;
      if(event.key==='ArrowRight'||event.key==='PageDown'){event.preventDefault();navigate(page+1);}
      if(event.key==='ArrowLeft'||event.key==='PageUp'){event.preventDefault();navigate(page-1);}
    };
    window.addEventListener('keydown',key);return()=>window.removeEventListener('keydown',key);
  },[presenting,ready,pending,page,zoom,count]);
  const jump=(event:FormEvent)=>{event.preventDefault();const value=Number(input);if(Number.isInteger(value)&&value>=1&&value<=count)navigate(value);else setInput(String(page));};
  return <section className={'native-office-reader'+(presenting?' native-presentation':'')} data-format={kind} aria-label={`${typeLabel} 原格式阅读`} aria-busy={pending}>
    <div className="native-office-heading"><span className={`format-badge format-${kind}`}>{kind.toUpperCase()}</span><div><strong>{name}</strong><small>直接解析原文件 · 本地预览</small></div>{kind==='pptx'&&<button className="secondary" aria-pressed={presenting} onClick={()=>setPresenting(value=>!value)}><Icon name={presenting?'collapse':'expand'} size={16}/>{presenting?'退出演示':'演示模式'}</button>}</div>
    <div className="pdf-reader-toolbar"><div className="pdf-page-controls"><button className="icon-button secondary" aria-label={`上一${pageLabel}`} disabled={!ready||pending||page<=1} onClick={()=>navigate(page-1)}><Icon name="arrow" className="reverse-arrow"/></button><form onSubmit={jump}><label htmlFor="office-page-number">{pageLabel}</label><input id="office-page-number" aria-label={`${typeLabel}${pageLabel}序号`} type="number" min={1} max={count||1} disabled={!ready||pending} value={input} onChange={event=>setInput(event.target.value)} onBlur={jump}/><span>/ {count||'…'}</span></form><button className="icon-button secondary" aria-label={`下一${pageLabel}`} disabled={!ready||pending||page>=count} onClick={()=>navigate(page+1)}><Icon name="arrow"/></button></div>
      <select aria-label={`${typeLabel}预览缩放`} value={zoom} disabled={!ready||pending} onChange={event=>navigate(page,Number(event.target.value))}>{[50,75,100,125,150,200].map(value=><option key={value} value={value}>{value===100?'适合窗口':value+'%'}</option>)}</select><button className="secondary" onClick={onDownload}><Icon name="download" size={16}/>下载原件</button></div>
    {pending&&<p className="material-loading" role="status"><Icon name="refresh" className="is-spinning"/>正在打开{typeLabel}原格式…</p>}
    {error&&<div className="pdf-error" role="alert">{error}<button className="secondary" onClick={()=>setAttempt(value=>value+1)}>重试原格式预览</button>{compatibilityReady&&<button className="secondary" onClick={onCompatibility}>使用兼容 PDF 预览</button>}</div>}
    {srcDoc&&<iframe ref={frame} className={'office-preview-frame'+(!ready?' office-loading':'')} title={`${typeLabel}原文件预览`} sandbox="allow-scripts" referrerPolicy="no-referrer" srcDoc={srcDoc}/>}
    <p className="hint native-office-boundary">{kind==='pptx'?'按原幻灯片顺序阅读，包含隐藏页；可用左右方向键演示。动画、部分图表和字体可能与 PowerPoint 不同。':'保留正文、表格和样式；阅读分页由浏览器排版，不是 Word 原始页码，引用仍以正文块定位。'}{degraded?' 部分内容未完整渲染，可切换兼容预览核对。':''} 截图与正式原文引用请返回兼容预览或文本视图。</p>
  </section>;
}
