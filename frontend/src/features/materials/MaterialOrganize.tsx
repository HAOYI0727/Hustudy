import {useEffect,useRef,useState} from "react";
import {api,ApiError,type DocumentMetadata,type DocumentOrganizeChange} from "../../api/client";
import {WorkspaceDialog} from "../../components/WorkspaceDialog";
import {Icon} from "../../components/Icon";
import {sessionPartition} from "../../api/query";
import {materialTags,organizedTags,organizeError} from "./organizeMetadata";

type Props={token:string;courseId:string;items:DocumentMetadata[];visible:DocumentMetadata[];selecting:boolean;disabled:boolean;metadataDirty:boolean;categories:string[];onSelecting:(value:boolean)=>void;onSelection:(items:DocumentMetadata[])=>void;onBusy:(value:boolean)=>void;onComplete:(items:DocumentMetadata[],changed:number)=>Promise<void>;onError:(error:unknown)=>void;onExport?:()=>void};
export function MaterialOrganize({token,courseId,items,visible,selecting,disabled,metadataDirty,categories,onSelecting,onSelection,onBusy,onComplete,onError,onExport}:Props){
  const [open,setOpen]=useState(false),[busy,setBusy]=useState(false),[categoryMode,setCategoryMode]=useState(false),[category,setCategory]=useState("");
  const [tagsMode,setTagsMode]=useState<DocumentOrganizeChange["tags_mode"]>("keep"),[tags,setTags]=useState("");
  const [problem,setProblem]=useState(""),[needsRefresh,setNeedsRefresh]=useState(false),[notice,setNotice]=useState("");
  const running=useRef(false);
  const dirty=categoryMode||tagsMode!=="keep";
  const change:DocumentOrganizeChange={...(categoryMode?{category:category.trim()||"未分类"}:{}),tags_mode:tagsMode,tags:["keep","clear"].includes(tagsMode)?[]:materialTags(tags)};
  const error=organizeError(items,change);
  useEffect(()=>{
    const unauthorized=(event:Event)=>{
      if((event as CustomEvent).detail!==sessionPartition(token))return;
      // Native dialogs are above the HTML reauthentication portal: yield the top layer.
      setOpen(false);setNeedsRefresh(true);setProblem("登录已过期，选择和输入仍保留。恢复后重新打开并读取所选资料，再核对保存。");
    };
    window.addEventListener("hustudy:unauthorized",unauthorized);
    return()=>window.removeEventListener("hustudy:unauthorized",unauthorized);
  },[token]);
  useEffect(()=>{
    const guard=(event:Event)=>{if(event.defaultPrevented)return;if(running.current||(open&&dirty&&!window.confirm("批量整理尚未保存，放弃修改并离开？")))event.preventDefault();};
    const unload=(event:BeforeUnloadEvent)=>{if(running.current||open&&dirty){event.preventDefault();event.returnValue="";}};
    window.addEventListener("hustudy:before-navigate",guard);window.addEventListener("hustudy:before-material-change",guard);window.addEventListener("beforeunload",unload);
    return()=>{window.removeEventListener("hustudy:before-navigate",guard);window.removeEventListener("hustudy:before-material-change",guard);window.removeEventListener("beforeunload",unload);};
  },[open,dirty]);
  const close=()=>{if(!running.current&&(!dirty||window.confirm("批量整理尚未保存，保留选择并关闭？")))setOpen(false);};
  const refresh=async()=>{
    if(running.current)return;running.current=true;setBusy(true);onBusy(true);setNotice("");
    try{
      // Do not silently remove inaccessible selections or apply edits during refresh.
      const rows=await Promise.all(items.map(item=>api.document(token,item.id)));
      if(rows.some(row=>row.course_id!==courseId))throw new Error("所选资料已不属于当前课程，请取消选择后重新核对");
      onSelection(rows);setNeedsRefresh(false);setProblem("");setNotice("已读取全部所选资料的最新信息，操作输入保留。请核对预览后再次保存。");
    }catch(error){setProblem("无法读取全部所选资料；选择和输入已保留，可返回资料库核对或取消选择。");onError(error);}
    finally{running.current=false;setBusy(false);onBusy(false);}
  };
  const selectPage=()=>{
    const all=visible.every(row=>items.some(item=>item.id===row.id));
    const next=all?items.filter(item=>!visible.some(row=>row.id===item.id)):[...items,...visible.filter(row=>!items.some(item=>item.id===row.id))];
    if(next.length>100){onError(new Error("每批最多选择100份资料，请先整理当前选择"));return;}
    onSelection(next);
  };
  return <section className="material-batch-tools" aria-label="资料批量整理">
    {!selecting?<><button className="secondary" disabled={disabled} onClick={()=>onSelecting(true)}><Icon name="list" size={16}/>批量整理分类与标签</button><p className="hint">勾选后可整理分类、标签，或导出所选资料。</p></>:<>
      <div className="material-selection-heading"><strong>已选 {items.length} 份</strong><span className="hint">跨页保留 · 最多100份</span></div>
      <div className="material-selection-actions"><button className="secondary" disabled={disabled||!visible.length} onClick={selectPage}>{visible.length&&visible.every(row=>items.some(item=>item.id===row.id))?"取消本页选择":"选择本页"}</button><button className="primary" disabled={disabled||!items.length||metadataDirty} onClick={()=>{setProblem("");setNotice("");setOpen(true);}}>整理已选</button>{onExport&&<button className="secondary" disabled={disabled||!items.length} onClick={onExport}><Icon name="download" size={15}/>导出已选</button>}<button className="text-button" disabled={disabled} onClick={()=>{onSelection([]);onSelecting(false);}}>结束选择</button></div>
      {metadataDirty&&<p className="hint">请先保存或撤销当前资料的整理，再批量操作。</p>}
    </>}
    <WorkspaceDialog open={open} title="整理所选资料" busy={busy} className="material-organize-dialog" onClose={close}>
      <div className="material-organize-intro"><span className="stage-symbol"><Icon name="folder" size={24}/></span><div><h3>让一组课件，找到共同的位置</h3><p>仅整理已选的 {items.length} 份资料。原文、版本、笔记引用保持关联。</p></div></div>
      <form onSubmit={async event=>{
        event.preventDefault();if(running.current||error||needsRefresh)return;running.current=true;setBusy(true);onBusy(true);setProblem("");setNotice("");
        try{
          const result=await api.organizeDocuments(token,courseId,items,change);
          onSelection([]);setOpen(false);setCategoryMode(false);setCategory("");setTagsMode("keep");setTags("");
          await onComplete(result.items,result.changed);
        }catch(reason){setProblem(reason instanceof Error?reason.message:"保存失败，输入已保留");if(reason instanceof ApiError&&[0,401,404,409].includes(reason.status)||reason instanceof ApiError&&reason.status>=500)setNeedsRefresh(true);onError(reason);}
        finally{running.current=false;setBusy(false);onBusy(false);}
      }}>
        <div className="material-organize-fields"><fieldset disabled={busy}><legend>分类</legend><label className="material-check-label"><input type="checkbox" checked={categoryMode} onChange={event=>setCategoryMode(event.target.checked)}/>统一设置分类</label>{categoryMode&&<label>目标分类<input aria-label="批量目标分类" list="batch-material-categories" maxLength={40} placeholder="留空归为未分类" value={category} onChange={event=>setCategory(event.target.value)}/><datalist id="batch-material-categories">{categories.map(value=><option key={value}>{value}</option>)}</datalist></label>}</fieldset>
        <fieldset disabled={busy}><legend>标签</legend><label>批量标签操作<select aria-label="批量标签操作" value={tagsMode} onChange={event=>setTagsMode(event.target.value as DocumentOrganizeChange["tags_mode"])}><option value="keep">保留原标签</option><option value="add">添加标签</option><option value="remove">移除指定标签</option><option value="replace">替换全部标签</option><option value="clear">清空全部标签</option></select></label>{!["keep","clear"].includes(tagsMode)&&<label>需要整理的标签<input aria-label="批量资料标签" value={tags} onChange={event=>setTags(event.target.value)} placeholder="例如：期末，重点"/></label>}<p className="hint">逗号分隔，精确去重；每份资料最终最多12个标签。</p></fieldset></div>
        <details className="material-selection-preview" open><summary>核对所选资料与整理结果 · {items.length} 份</summary><ul>{items.map(item=><li key={item.id}><strong title={item.name}>{item.name}</strong><span>{change.category||item.category}</span><small>{organizedTags(item.tags,change).join(" · ")||"无标签"}</small></li>)}</ul></details>
        {notice&&<p role="status" className="material-batch-notice">{notice}</p>}{problem&&<p role="alert" className="material-batch-problem">{problem}</p>}
        {needsRefresh&&<button type="button" className="secondary" disabled={busy} onClick={()=>void refresh()}><Icon name="refresh" size={16}/>重新读取所选资料</button>}
        {dirty&&error&&<p role="alert" className="material-batch-problem">{error}</p>}
        <div className="material-organize-footer"><p>所有资料核对通过后整批保存；存在冲突时不会部分修改。</p><button className="primary" disabled={busy||!!error||needsRefresh}><Icon name="check" size={16}/>{busy?"正在处理…":`确认整理 ${items.length} 份资料`}</button><button type="button" className="secondary" disabled={busy} onClick={close}>返回资料库</button></div>
      </form>
    </WorkspaceDialog>
  </section>;
}
