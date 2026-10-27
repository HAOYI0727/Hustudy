import {useEffect,useRef,useState} from 'react';
import {api,ApiError,type StoredPackagePreview} from '../../api/client';
import {sessionPartition} from '../../api/query';
import {readPendingPackage} from './packagePending';

type Props={token:string;owner:string;protectedId?:string;disabled:boolean;onRemoved:(id:string)=>void;onError:(error:unknown)=>void;onBusyChange:(busy:boolean)=>void};
export function PackagePreviewManager({token,owner,protectedId,disabled,onRemoved,onError,onBusyChange}:Props) {
  const [expanded,setExpanded]=useState(false),[rows,setRows]=useState<StoredPackagePreview[]|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[requested,setRequested]=useState('');
  const active=useRef<{controller:AbortController;timer:number}|null>(null),serial=useRef(0),busyRef=useRef(false);
  const callbacks=useRef({onRemoved,onError,onBusyChange});callbacks.current={onRemoved,onError,onBusyChange};
  const protectedRef=useRef(protectedId);protectedRef.current=protectedId;
  const stop=()=>{serial.current++;if(active.current){active.current.controller.abort();window.clearTimeout(active.current.timer);active.current=null;}busyRef.current=false;callbacks.current.onBusyChange(false);};
  useEffect(()=>{
    const unauthorized=(event:Event)=>{if((event as CustomEvent).detail!==sessionPartition(token))return;stop();setExpanded(false);setRows(null);setBusy(false);};
    window.addEventListener('hustudy:unauthorized',unauthorized);
    return()=>{window.removeEventListener('hustudy:unauthorized',unauthorized);stop();};
  },[token,owner]);
  const begin=()=>{stop();const controller=new AbortController(),id=serial.current;active.current={controller,timer:window.setTimeout(()=>controller.abort(),120000)};busyRef.current=true;setBusy(true);callbacks.current.onBusyChange(true);setError('');return {id,signal:controller.signal};};
  const finish=(id:number)=>{if(id!==serial.current)return;if(active.current)window.clearTimeout(active.current.timer);active.current=null;busyRef.current=false;setBusy(false);callbacks.current.onBusyChange(false);};
  const failure=(reason:unknown)=>{setError(reason instanceof Error?reason.message:'预览管理暂不可用，请重试。');if(reason instanceof ApiError&&reason.status===401)callbacks.current.onError(reason);};
  const load=async()=>{
    if(disabled||busyRef.current)return;const task=begin();setRequested('');
    try{const next=await api.packagePreviews(token,task.signal);if(task.id===serial.current)setRows(next);}
    catch(reason){if(task.id===serial.current)failure(reason);}finally{finish(task.id);}
  };
  const remove=async(id:string)=>{
    if(disabled||busyRef.current)return;
    if(id===protectedRef.current||id===readPendingPackage(owner)?.preview_id){setRequested('');setError('这份预览用于待核对的导入请求，请先核对结果。');return;}
    const task=begin();
    try{try{await api.removePackagePreview(token,id,task.signal);}catch(reason){if(!(reason instanceof ApiError&&reason.status===404))throw reason;}if(task.id!==serial.current)return;setRows(previous=>previous?.filter(row=>row.id!==id)||[]);setRequested('');callbacks.current.onRemoved(id);}
    catch(reason){if(task.id===serial.current)failure(reason);}finally{finish(task.id);}
  };
  return <section className="package-preview-manager" aria-label="已上传预览管理">
    <button type="button" className="text-button" aria-expanded={expanded} disabled={disabled||busy} onClick={()=>{if(expanded){setExpanded(false);setRequested('');}else{setExpanded(true);void load();}}}>管理已上传的预览</button>
    {expanded&&<><p className="hint">预览文件最多保留24小时，同一账户最多10份。删除预览不会删除已导入的课程或笔记；未确认的文件需要重新上传。</p>
      <button type="button" className="secondary" disabled={disabled||busy} onClick={()=>void load()}>刷新预览列表</button>
      {busy&&<p role="status">正在处理文件预览…</p>}{error&&<p role="alert">{error}</p>}
      {rows!==null&&!rows.length&&<p className="hint">没有保留的文件预览。</p>}
      {rows!==null&&rows.length>0&&<ul className="package-preview-list" aria-label="已上传预览列表">{rows.map(row=><li key={row.id}>
        <p>上传于 {new Date(row.created_at).toLocaleString('zh-CN')} · {(row.size_bytes/1024/1024).toFixed(2)} MiB</p>
        <p className="hint">保留至 {new Date(row.expires_at).toLocaleString('zh-CN')}</p><code>预览标识：{row.id}</code><code>SHA-256：{row.sha256}</code>
        {row.id===protectedId?<p className="hint">待核对的导入正在使用此预览，暂不可删除。</p>:requested===row.id?<div className="package-actions"><span>确认移除这份预览文件？</span><button type="button" className="secondary" disabled={disabled||busy} onClick={()=>void remove(row.id)}>确认删除预览</button><button type="button" className="text-button" disabled={busy} onClick={()=>setRequested('')}>取消删除预览</button></div>:<button type="button" className="text-button" aria-label={`删除预览：${row.id}`} disabled={disabled||busy} onClick={()=>setRequested(row.id)}>删除预览</button>}
      </li>)}</ul>}
    </>}
  </section>;
}
