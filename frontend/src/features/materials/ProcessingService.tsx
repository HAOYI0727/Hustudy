import {useEffect,useState} from "react";
import {api,ApiError,type ProcessingServiceStatus} from "../../api/client";
import {Icon} from "../../components/Icon";
import "./processing-service.css";

export function ProcessingService({token,pending}:{token:string;pending:boolean}){
 const [data,setData]=useState<ProcessingServiceStatus|null>(null),[error,setError]=useState(""),[loading,setLoading]=useState(true),[retry,setRetry]=useState(0);
 useEffect(()=>{
  let live=true,timer:ReturnType<typeof setTimeout>|undefined;const controller=new AbortController();
  const read=async()=>{
   if(document.hidden){timer=setTimeout(()=>void read(),3000);return;}
   setLoading(true);
   try{const value=await api.processingStatus(token,controller.signal);if(!live)return;setData(value);setError("");if(pending)timer=setTimeout(()=>void read(),3000);}
   catch(reason){if(live){setData(null);setError(reason instanceof ApiError&&reason.status===401?"请先恢复登录，原上传记录保留。":"暂时无法确认处理服务状态；已保存原件保留，请恢复连接后刷新。");}}
   finally{if(live)setLoading(false);}
  };
  // StrictMode's discarded mount must not issue a duplicate request.
  queueMicrotask(()=>{if(live)void read();});
  return()=>{live=false;controller.abort();clearTimeout(timer);};
 },[token,pending,retry]);
 if(!error&&(!data||data.state==="ready"))return null;
 return <section className="processing-service" data-state={error?"unknown":data?.state||"checking"} aria-label="资料处理服务" aria-live="polite"><div><Icon name="info" size={15}/><span>{error||data?.message}</span></div><button type="button" className="text-button" disabled={loading} onClick={()=>setRetry(value=>value+1)}>{loading?"确认中…":"重试"}</button></section>;
}
