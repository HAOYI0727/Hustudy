import type {AIAnswer, StudyReport} from "../../api/client";
import {useEffect,useState} from "react";
import {readingPages,readingPageLabel,matchingReadingTopics} from "./readingSummary";

export function ReadingCoverage({answer,versionId}:{answer:AIAnswer;versionId:string}){
  const coverage=answer.result.coverage;
  const current=coverage?.versions?.find(row=>row.version_id===versionId);
  return <section className="reading-summary-coverage" aria-label="课件总结覆盖范围"><strong>{answer.result.partial?"当前仅有部分总结":coverage?.truncated?"本次文本未完整覆盖":"本次总结范围"}</strong>
    {current?<p>当前版本已纳入{current.selected_chunks}/{current.total_chunks}段可用文字，{current.sent_chars}/{current.total_chars}字符。{current.truncated?"仍有未纳入文字，请核对发送范围。":"已纳入可提取文字，不代表图片、动画或每个知识点均已完整讲解。"}</p>:<p>此结果未记录可核对的发送覆盖范围，不能据此认定整份PPT已完整总结。</p>}
    {coverage?.notice&&<p className="hint">{coverage.notice}</p>}
    {answer.result.study_report_sections?.length?<p className="hint">长课件按批独立生成，以下分段展示；尚未进行跨批融合或去重。</p>:null}
  </section>;
}

export function ReadingTopicMap({report,versionId,currentPage,onSource,onRead,onDraft,disabled=false}:{report:StudyReport;versionId:string;currentPage?:number|null;onSource:(version:string,chunk:string)=>void;onRead?:(id:string)=>void;onDraft?:(id:string)=>void;disabled?:boolean}){
  const [query,setQuery]=useState(""),[followPage,setFollowPage]=useState(false),[requested,setRequested]=useState({scope:"",page:0});
  useEffect(()=>{if(followPage)setRequested({scope:"",page:0});},[followPage,currentPage]);
  const matches=followPage&&!currentPage?[]:matchingReadingTopics(report.topics,versionId,query,followPage?currentPage||null:null);
  const scope=JSON.stringify([query,followPage,followPage?currentPage:null]);
  const pages=Math.max(1,Math.ceil(matches.length/8));
  const page=Math.min(pages-1,requested.scope===scope?requested.page:0);
  const visible=matches.slice(page*8,(page+1)*8);
  return <section className="reading-topic-map" aria-label="知识点与PPT页码"><h4>知识点 · 页码导览</h4><p className="hint">页码取自本知识点的有效原文引用，表示可回查依据；间隔页不会补齐，也不等于整页内容已全部归纳。</p>
    <div className="reading-topic-filters"><label>查找知识点<input aria-label="搜索课件知识点" maxLength={160} value={query} onChange={event=>{setQuery(event.target.value);setRequested({scope:"",page:0});}} placeholder="名称、讲解、分组或易错点"/></label><label className="reading-page-follow"><input type="checkbox" aria-label="跟随当前阅读页筛选知识点" checked={followPage} onChange={event=>{setFollowPage(event.target.checked);setRequested({scope:"",page:0});}}/>跟随当前阅读页{currentPage?` · 第${currentPage}页`:" · 暂无可核对页码"}</label></div>
    <p className="hint" role="status">目录匹配{matches.length} / {report.topics.length}个知识点。筛选只影响目录，当前讲解和笔记草稿保留。</p>
    {(query||followPage)&&<button className="text-button" onClick={()=>{setQuery("");setFollowPage(false);setRequested({scope:"",page:0});}}>清除知识点筛选</button>}
    {!matches.length&&<p className="reading-topic-empty">{followPage&&!currentPage?"当前视图无法唯一对应来源页，请取消页码筛选或切到可定位的PPT页。":"没有匹配的知识点引用；可清除筛选或检查原文，不能据此判断该页没有知识点。"}</p>}
    <ol>{visible.map(topic=>{const pages=readingPages(topic.citations,versionId);return <li key={topic.topic_id}><div><span className="reading-topic-pages">{readingPageLabel(pages.map(row=>row.page))}</span><strong>{topic.name}</strong></div>
      {topic.concept_group&&<small>{topic.concept_group} · AI建议分组</small>}
      <div className="reading-topic-actions">{onRead&&<button className="secondary" aria-label={`查看讲解：${topic.name}`} onClick={()=>onRead(topic.topic_id)}>查看讲解</button>}{pages.map(({page,source})=><button type="button" className="secondary" key={page} onClick={()=>onSource(source.version_id,source.chunk_id)} aria-label={`${topic.name}：回第${page}页`}>第{page}页</button>)}{onDraft&&<button className="secondary" disabled={disabled} aria-label={`摘记：${topic.name}`} onClick={()=>onDraft(topic.topic_id)}>写知识点笔记</button>}</div>
    </li>;})}</ol>
    <nav className="reading-topic-pagination" aria-label="知识点目录分页"><button className="secondary" disabled={page===0} onClick={()=>setRequested({scope,page:page-1})}>上一页知识点</button><span>{page+1} / {pages}页</span><button className="secondary" disabled={page+1>=pages} onClick={()=>setRequested({scope,page:page+1})}>下一页知识点</button></nav>
  </section>;
}
