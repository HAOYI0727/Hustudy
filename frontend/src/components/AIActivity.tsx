import "./ai-activity.css";
export function AIActivity({active=false,queued=false,label="题目识别"}:{active?:boolean;queued?:boolean;label?:string}){
 return <div className={`ai-activity ${active?"is-active":""}`}>
  {active&&<div role="status" aria-live="polite" className="ai-waiting"><span className="ai-activity-spinner" aria-hidden="true"/><div><strong>{queued?"AI任务已排队":"正在等待AI返回结果"}</strong><p>{label}进行中，完成后会自动更新；请勿重复提交。</p></div></div>}
  <p className="ai-caution">AI也会犯错，请仔细甄别</p>
 </div>;
}
