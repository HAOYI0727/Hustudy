import {useEffect,useState} from "react";
import {api,BankPaperMeta} from "../../api/client";

export function BankIdentityReview({token,courseId,papers,busy,run,reload,onNotice}:{token:string;courseId:string;papers:BankPaperMeta[];busy:boolean;run:(work:()=>Promise<void>)=>void;reload:()=>Promise<void>;onNotice:(text:string)=>void}){
 const [selected,setSelected]=useState<string[]>([]),[source,setSource]=useState("");
 useEffect(()=>{setSelected([]);setSource("");},[token,courseId]);
 const chosen=papers.filter(p=>selected.includes(p.id));
 const perform=(action:"source"|"confirm"|"revoke"|"exercise")=>run(async()=>{
  if(!window.dispatchEvent(new Event("hustudy:bank-before-confirm",{cancelable:true})))throw new Error("请先保存未保存的题目或元数据，再进行批量身份审核");
  if(action==="confirm"&&!window.confirm(`确认所选${chosen.length}份材料属于历年考试试题？请先核对来源；这不代表平台独立核实官方真实性，也不会替你审核题目或知识点映射。`))return;
  const items=chosen.map(p=>({paper_id:p.id,expected_revision:p.metadata.revision||1,...(action==="source"?{provenance:source.trim()}:{exam_identity:{kind:action==="exercise"?"exercise":"past_exam",confirmed:action==="confirm"}})}));
  await api.bankMetadataBatch(token,courseId,items);if(action==="source")setSource("");await reload();
  onNotice(action==="source"?"所选来源说明已保存；请再次核对并确认真题身份":"批量身份决定已保存；旧预览会重新检查依据，历史作答保留");
 });
 return <section className="panel" aria-label="真题身份批量审核"><h4>真题身份与来源 · 可批量处理</h4><p className="hint">题目核验与真题身份分别确认。仅本人确认的历年真题，在题目、知识点映射和课件引用均有效时，才可供学习报告使用。</p><fieldset disabled={busy}><div className="bank-actions"><button className="secondary" onClick={()=>setSelected(papers.slice(0,100).map(p=>p.id))}>选择全部题库（最多100份）</button><button className="secondary" onClick={()=>setSelected([])}>清空题库选择</button><span>已选择 {chosen.length} 份</span></div>{papers.map(p=><label className="bank-check" key={p.id}><input type="checkbox" aria-label={`选择身份审核 ${p.title}`} checked={selected.includes(p.id)} onChange={e=>setSelected(ids=>e.target.checked?[...ids,p.id]:ids.filter(id=>id!==p.id))}/><span>{p.title} · {p.metadata.exam_identity?.confirmed?"本人已确认真题":p.metadata.exam_identity?.kind==="exercise"?"普通练习":"真题身份未确认"} · {p.status==="CONFIRMED"?"题目已核验":"题目待核验"} · 来源：{p.metadata.provenance||"未填写"}</span></label>)}<label>所选题库的共同来源说明<input maxLength={500} value={source} onChange={e=>setSource(e.target.value)} placeholder="仅当所选材料确实来自同一来源时批量填写"/></label><div className="bank-actions"><button className="secondary" disabled={!chosen.length||chosen.length>100||!source.trim()} onClick={()=>perform("source")}>批量保存来源说明</button><button className="primary" disabled={!chosen.length||chosen.length>100||Boolean(source.trim())} onClick={()=>perform("confirm")}>批量确认历年真题身份</button><button className="secondary" disabled={!chosen.length||chosen.length>100||Boolean(source.trim())} onClick={()=>perform("revoke")}>批量撤销真题身份</button><button className="secondary" disabled={!chosen.length||chosen.length>100||Boolean(source.trim())} onClick={()=>perform("exercise")}>设为普通练习题库</button></div><p className="hint">来源说明修改后需重新确认；并发冲突整批不修改，请刷新后核对。题目批量核验、保存及标签处理仍在下方题目工具栏。</p></fieldset></section>;
}
