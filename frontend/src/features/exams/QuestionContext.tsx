import {useId,useRef} from "react";
import {Question} from "../../api/client";
import {BankMath} from "./BankMath";
import {BankFigure} from "./BankImages";
export function QuestionContext({question,token,courseId=""}:{question:Question;token:string;courseId?:string}){
 const dialog=useRef<HTMLDialogElement>(null),trigger=useRef<HTMLButtonElement>(null),title=useId();
 const hasContext=Boolean(question.context_stem||question.context_illustrations?.length);
 if(!hasContext&&!(question.display_group&&question.display_group.order.length>1))return null;
 const context=<>{question.context_stem&&<BankMath text={question.context_stem} token={token}/>} {question.context_illustrations?.map((image,i)=><BankFigure key={i} image={image} token={token} courseId={courseId}/>)}</>;
 return <>
  <section className="bank-full-context" aria-label="完整大题题干上下文">
   <div className="bank-context-heading"><h4>{hasContext?"大题完整题干上下文":"大题子问"}</h4><button type="button" className="secondary" ref={trigger} onClick={()=>dialog.current?.showModal()}>查看整道题</button></div>
   {hasContext&&<><p className="hint">下列原题内容用于补全公共条件与图表。本次只需回答下方选中的子问。</p>{context}<h4>本次作答子问 ↓</h4></>}
  </section>
  <dialog className="bank-whole-question" ref={dialog} aria-labelledby={title} onClose={()=>trigger.current?.focus()}>
   <div className="bank-context-heading"><h3 id={title}>整道题</h3><button type="button" className="secondary" autoFocus onClick={()=>dialog.current?.close()}>关闭整道题</button></div>
   <p className="hint">仅供查看原题条件和其他子问；本次仍只作答抽中的子问，不显示参考解答。</p>
   {hasContext?context:<p role="status">这份历史练习未保存完整大题上下文，目前仅能查看已保存的子问。请重新抽题；若题库原文也有缺失，请先补全题干。</p>}
   <h4 className="bank-context-current">本次作答子问</h4><BankMath text={question.stem} token={token}/>
   {question.options?.map((option,i)=><div key={i}><strong>{String.fromCharCode(65+i)}. </strong><BankMath text={option} token={token}/></div>)}
   {question.illustrations?.map((image,i)=><BankFigure key={i} image={image} token={token} courseId={courseId}/>)}
  </dialog>
 </>;
}
