import {useEffect,useRef,useState} from "react";
import {api} from "../../api/client";
import {sessionPartition} from "../../api/query";
import {Icon} from "../../components/Icon";
import {WorkspaceDialog} from "../../components/WorkspaceDialog";
import {editReadingBookmark,readingBookmarks,shortReadingLabel,type ReadingBookmark,type BookmarkTarget} from "./readingBookmarks";
type Props={token:string;courseId:string;target?:BookmarkTarget;serial:number;disabled:boolean;onOpen:(bookmark:ReadingBookmark)=>Promise<boolean>;onError:(error:unknown)=>void};
export function ReadingBookmarks({token,courseId,target,serial,disabled,onOpen,onError}:Props){
  const [owner,setOwner]=useState(""),[items,setItems]=useState<ReadingBookmark[]>([]),[open,setOpen]=useState(false),[error,setError]=useState("");
  const [name,setName]=useState(""),[savingTarget,setSavingTarget]=useState<BookmarkTarget>(),[editId,setEditId]=useState(""),[editName,setEditName]=useState("");
  const [query,setQuery]=useState(""),[offset,setOffset]=useState(0),[busy,setBusy]=useState(false),[notice,setNotice]=useState("");
  const live=useRef(true),seen=useRef(0),labelRef=useRef<HTMLInputElement>(null);
  const destination=useRef("");
  const refresh=(id=owner)=>{if(!id)return;const result=readingBookmarks(id,courseId);setItems(result.items);setError(result.error);};
  useEffect(()=>{let active=true;live.current=true;setOwner("");setItems([]);setOpen(false);setSavingTarget(undefined);setError("");
    void api.me(token).then(user=>{if(active){setOwner(user.id);refresh(user.id);}}).catch(error=>{if(active)onError(error);});
    return()=>{active=false;live.current=false;};
  },[token,courseId]);
  useEffect(()=>{const sync=()=>refresh();window.addEventListener("storage",sync);return()=>window.removeEventListener("storage",sync);},[owner,courseId]);
  useEffect(()=>{
    const unauthorized=(event:Event)=>{if((event as CustomEvent).detail===sessionPartition(token)){setOpen(false);setError("登录已过期，书签仍保留；恢复登录后请重新打开原文。");}};
    window.addEventListener("hustudy:unauthorized",unauthorized);return()=>window.removeEventListener("hustudy:unauthorized",unauthorized);
  },[token]);
  useEffect(()=>{
    if(!serial||seen.current===serial||!target||!owner)return;
    seen.current=serial;
    const result=readingBookmarks(owner,courseId);setItems(result.items);setError(result.error);
    const prior=result.items.find(row=>row.versionId===target.versionId&&row.chunkId===target.chunkId);
    setSavingTarget(target);setName(prior?.label||shortReadingLabel(`${target.documentName} · ${target.locatorValue}`,80));
    setNotice("");setEditId("");setOpen(true);
  },[serial,target,owner,courseId]);
  useEffect(()=>{if(open&&savingTarget)labelRef.current?.focus();},[open,savingTarget]);
  const commit=(action:Parameters<typeof editReadingBookmark>[2])=>{
    const result=editReadingBookmark(owner,courseId,action);setItems(result.items);setError(result.error);setNotice("");return !result.error;
  };
  const shown=items.filter(row=>[row.label,row.documentName,row.locatorValue].some(s=>s.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase())));
  const pageOffset=shown.length?Math.min(offset,Math.floor((shown.length-1)/8)*8):0;
  return <>
    <button className="secondary" disabled={disabled||!owner} onClick={()=>{refresh();setSavingTarget(undefined);setEditId("");setNotice("");setOpen(true);}}><Icon name="bookmark" size={16}/>阅读书签{items.length?` · ${items.length}`:""}</button>
    <WorkspaceDialog open={open} title="阅读书签" className="reading-bookmarks-dialog" busy={busy} onClose={()=>setOpen(false)} restoreFocus={()=>{const id=destination.current;destination.current="";const source=id?document.getElementById(id):null;if(!source)return false;source.focus({preventScroll:true});source.scrollIntoView({block:"center"});return true;}}>
      <div className="reading-tool-intro"><span className="reading-tool-symbol"><Icon name="bookmark" size={24}/></span><div><h3>把值得重读的地方，留在手边</h3><p>仅保存在当前浏览器，按账户和课程分开。清除浏览器数据会移除书签，重要理解请保存为笔记。</p></div></div>
      {error&&<p className="reading-tool-error" role="alert">{error} <button className="text-button" onClick={()=>refresh()}>重试读取书签</button></p>}
      {notice&&<p className="reading-tool-notice" role="status">{notice}</p>}
      {savingTarget&&<form className="bookmark-save" onSubmit={event=>{event.preventDefault();if(commit({kind:"save",target:savingTarget,label:name})){setSavingTarget(undefined);setQuery("");setOffset(0);setNotice("书签已保存，下次会回到这个版本的原文片段");}}}>
        <p>{savingTarget.documentName} · v{savingTarget.versionNo} · {savingTarget.locatorValue}</p>
        <label>书签名称<input ref={labelRef} required maxLength={80} value={name} onChange={event=>setName(event.target.value)}/></label>
        <div><button className="primary" disabled={!owner||busy||!name.trim()}>保存书签</button><button type="button" className="secondary" onClick={()=>setSavingTarget(undefined)}>取消添加</button></div>
      </form>}
      <div className="bookmark-search"><label className="input-with-icon"><Icon name="search" size={16}/><input aria-label="搜索阅读书签" placeholder="查找书签、资料或定位…" value={query} onChange={event=>{setQuery(event.target.value);setOffset(0);}}/></label><button className="icon-button secondary" aria-label="刷新阅读书签" onClick={()=>refresh()}><Icon name="refresh" size={16}/></button></div>
      <div className="reading-bookmark-list" aria-label="已保存的阅读书签">{shown.slice(pageOffset,pageOffset+8).map(row=><article key={row.id}>
        {editId===row.id?<form className="bookmark-rename" onSubmit={event=>{event.preventDefault();if(commit({kind:"rename",id:row.id,label:editName})){setEditId("");setNotice("书签名称已更新");}}}><input aria-label="修改书签名称" required maxLength={80} value={editName} onChange={event=>setEditName(event.target.value)}/><button className="primary" disabled={busy||!editName.trim()}>保存名称</button><button type="button" className="secondary" disabled={busy} onClick={()=>setEditId("")}>取消</button></form>:<><div className="bookmark-identity"><Icon name="bookmark" size={18}/><div><strong>{row.label}</strong><p>{row.documentName} · v{row.versionNo} · {row.locatorValue}</p></div></div><div className="bookmark-actions"><button className="secondary" disabled={busy} onClick={()=>{setBusy(true);setError("");void onOpen(row).then(opened=>{if(live.current&&opened){destination.current="chunk-"+row.chunkId;setOpen(false);}}).catch(error=>{if(live.current)setError(error instanceof Error?error.message:"来源暂不可用，书签仍保留");}).finally(()=>{if(live.current)setBusy(false);});}}>回到原文 <Icon name="arrow" size={15}/></button><button className="text-button" disabled={busy} onClick={()=>{setEditId(row.id);setEditName(row.label);}}>改名</button><button className="text-button danger" disabled={busy} onClick={()=>{if(window.confirm(`移除书签“${row.label}”？原资料与笔记保留。`)&&commit({kind:"remove",id:row.id}))setNotice("书签已移除");}}>移除</button></div></>}
      </article>)}</div>
      {!shown.length&&!error&&<div className="reading-tool-empty"><Icon name="bookmark" size={28}/><strong>{items.length?"没有匹配的书签":"从一个值得重读的片段开始"}</strong><p>{items.length?"试试资料名称或更短的关键词。":"在原文片段下点击“添加书签”，留下准确的历史位置。"}</p></div>}
      <nav className="catalogue-pages" aria-label="阅读书签分页"><button className="secondary" disabled={busy||!pageOffset} onClick={()=>setOffset(pageOffset-8)}>上一页</button><span role="status">{Math.floor(pageOffset/8)+1} / {Math.max(1,Math.ceil(shown.length/8))} 页 · {shown.length} 条</span><button className="secondary" disabled={busy||pageOffset+8>=shown.length} onClick={()=>setOffset(pageOffset+8)}>下一页</button></nav>
    </WorkspaceDialog>
  </>;
}
