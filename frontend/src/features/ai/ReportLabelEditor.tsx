import {labelSourceText} from "./ReportLabelSource";
import {labelNames, ReportReview, ReviewLabel, reviewError} from "./report-review";

type Props={value:ReportReview;onChange:(value:ReportReview)=>void;onContinue:()=>void;onCancel:()=>void};

export function ReportLabelEditor({value,onChange,onContinue,onCancel}:Props) {
  const replace=(index:number,labels:ReviewLabel[])=>onChange({...value,labels:value.labels.map((rows,i)=>i===index?labels:rows)});
  const error=reviewError(value);
  return <div className="report-label-editor">
    <p className="eyebrow">1 / 2 · 审阅学习标签</p>
    <h3>整理重点、难点与考点建议</h3>
    <p className="hint">修改只用于这份笔记草稿。原始AI建议和引用会保留，标签整理不代表教师或真题确认。</p>
    {value.report.topics.map((topic,index)=><fieldset key={topic.topic_id}>
      <legend>{topic.name}</legend><p>{topic.explanation}</p>
      <details><summary>核对原始AI建议与依据</summary>
        {topic.labels.map((label,i)=><p key={i}>{labelNames[label.kind]} · {labelSourceText(label)}：{label.reason}</p>)}
        {topic.citations.map((citation,i)=><blockquote key={i}>{citation.quote}</blockquote>)}
      </details>
      {value.labels[index].map((label,i)=><div className="report-label-row" key={i}>
        <label>标签类型<select aria-label={`${topic.name} 标签${i+1}类型`} value={label.kind} onChange={e=>replace(index,value.labels[index].map((row,j)=>j===i?{...row,kind:e.target.value as ReviewLabel["kind"]}:row))}>
          {Object.entries(labelNames).map(([kind,name])=><option key={kind} value={kind} disabled={value.labels[index].some((row,j)=>j!==i&&row.kind===kind)}>{name}</option>)}
        </select></label>
        <label>保留或修改的理由<textarea rows={3} maxLength={1000} aria-label={`${topic.name} 标签${i+1}理由`} value={label.reason} onChange={e=>replace(index,value.labels[index].map((row,j)=>j===i?{...row,reason:e.target.value}:row))}/></label>
        <button className="secondary" type="button" aria-label={`删除${topic.name}标签${i+1}`} onClick={()=>replace(index,value.labels[index].filter((_,j)=>j!==i))}>删除标签</button>
      </div>)}
      {!value.labels[index].length&&<p className="hint">尚未保留标签，可新增，也可直接继续。</p>}
      <button className="secondary" type="button" disabled={value.labels[index].length>=3} onClick={()=>{
        const kind=(Object.keys(labelNames) as ReviewLabel["kind"][]).find(kind=>!value.labels[index].some(row=>row.kind===kind));
        if(kind)replace(index,[...value.labels[index],{kind,reason:""}]);
      }}>新增标签</button>
    </fieldset>)}
    {error&&<p role="status" className="hint">{error}</p>}
    <div className="editor-footer"><button className="secondary" onClick={onCancel}>取消</button><button className="primary" disabled={Boolean(error)} onClick={onContinue}>继续编辑笔记正文</button></div>
  </div>;
}
