import {useEffect,useState} from "react";
import {api,type MistakeSources as Sources} from "../../api/client";
import {Icon} from "../../components/Icon";

export function MistakeSources({token,id,onSource,onCourse}:{token:string;id:string;onSource:(version:string,chunk:string)=>void;onCourse:(courseId:string,section:"materials"|"notes")=>void}){
  const [data,setData]=useState<Sources|null>(null),[failed,setFailed]=useState(false),[retry,setRetry]=useState(0);
  useEffect(()=>{
    let active=true;setData(null);setFailed(false);
    void api.mistakeSources(token,id).then(result=>{if(active)setData(result);}).catch(()=>{if(active)setFailed(true);});
    return()=>{active=false;};
  },[token,id,retry]);
  return <section className="mistake-source-panel" aria-label="错题回源"><div className="panel-title"><div><p className="eyebrow">BACK TO THE SOURCE</p><h3>找到卡住的地方，回原文再看一遍</h3></div><Icon name="link"/></div>
    {failed?<div role="alert">来源暂时无法读取<button className="secondary" onClick={()=>setRetry(value=>value+1)}>重试错题来源</button></div>:!data?<p role="status">正在核对原始资料…</p>:<>
      {data.items.length?<div className="mistake-source-links">{data.items.map(source=><button key={`${source.version_id}-${source.chunk_id}`} className="secondary" disabled={source.availability!=="active"} onClick={()=>onSource(source.version_id,source.chunk_id)}><Icon name="file"/><span><strong>{source.title}</strong><small>{source.availability==="active"?source.locator||"打开原始资料版本":"来源已失效，历史作答保留"}</small></span><Icon name="arrow" size={15}/></button>)}</div>:<p className="hint">这道历史题未保存资料引用。可以回课程资料或笔记查找相关概念。</p>}
      <div className="learning-links"><button className="secondary" onClick={()=>onCourse(data.course_id,"materials")}><Icon name="file" size={16}/>回本课程资料</button><button className="secondary" onClick={()=>onCourse(data.course_id,"notes")}><Icon name="notes" size={16}/>整理复盘笔记</button></div>
    </>}
  </section>;
}
