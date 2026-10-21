import {Icon} from "../../components/Icon";
import {FormEvent,useState} from "react";
import {api} from "../../api/client";
import {PageTitle} from "../../components/workspace";
import {BankPractice,BankProps} from "./BankPractice";
import {BankManager} from "./BankManager";
import {BankAnalysis} from "./BankAnalysis";
import "./bank.css";

export function ExamPilot(props:BankProps){
 const [topicFilter,setTopicFilter]=useState("");
 const [tab,setTab]=useState("bank");
 return <div className="page"><PageTitle eyebrow="EXAM PILOT" title="自己的题库，按知识点练习" text="上传、识别并校正题库，确认后随机抽取练习；选择题有标准答案时自动批改，解答题提交后自行核对。"/><div className="bank-tabs">{[["bank","上传与校正题库"],["analysis","考点、统计与蓝图"],["practice","随机练习与作答"]].map(([id,label])=><button key={id} className={tab===id?"primary":"secondary"} onClick={()=>{const event=new Event("hustudy:before-navigate",{cancelable:true});if(window.dispatchEvent(event))setTab(id);}}>{label}</button>)}</div>{tab==="bank"?<BankManager {...props} topicFilter={topicFilter} onTopicFilter={setTopicFilter}/>:tab==="analysis"?<BankAnalysis {...props} onTopicOpen={id=>{if(window.dispatchEvent(new Event("hustudy:before-navigate",{cancelable:true}))){setTopicFilter(id);setTab("bank");}}} onReady={p=>{localStorage.removeItem(`hustudy-bank-attempt:${props.courseId}`);localStorage.setItem(`hustudy-bank-paper:${props.courseId}`,p.id);setTab("practice");}}/>:<BankPractice {...props}/>}</div>;
}

export {Review} from "./Review";

export function FeedbackPage(props:{token:string;onNotice:(s:string)=>void;onError:(e:unknown)=>void}){
 return <div className="page"><PageTitle eyebrow="FEEDBACK" title="使用反馈" text="遇到问题或有改进建议，在这里单独记录。"/><section className="panel"><Feedback {...props}/></section></div>;
}

export function Feedback({ token, onNotice, onError }: { token: string; onNotice: (s: string) => void; onError: (e: unknown) => void }) {
 const [content,setContent]=useState(""),[kind,setKind]=useState("product"),[rating,setRating]=useState(""),[busy,setBusy]=useState(false);
 const submit=async(event:FormEvent)=>{event.preventDefault();if(busy)return;setBusy(true);try{await api.feedback(token,{kind,content,rating:rating?Number(rating):undefined});setContent("");onNotice("反馈已保存");}catch(e){onError(e);}finally{setBusy(false);}};
 return <form onSubmit={submit}><h4><Icon name="edit" size={16}/>留下反馈</h4><label>问题类型<select value={kind} onChange={e=>setKind(e.target.value)}><option value="product">使用建议</option><option value="bug">功能问题</option><option value="content">题目与资料问题</option></select></label><label>评分（可选）<select value={rating} onChange={e=>setRating(e.target.value)}><option value="">暂不评分</option>{[1,2,3,4,5].map(n=><option key={n} value={n}>{n}分</option>)}</select></label><textarea rows={3} value={content} onChange={e=>setContent(e.target.value)} placeholder="哪一步最有帮助？哪里需要改进？" required/><button className="secondary" disabled={busy}>{busy?"保存中…":"提交反馈"}</button></form>;
}
