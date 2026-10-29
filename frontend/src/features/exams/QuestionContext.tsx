import {Question} from "../../api/client";
import {BankMath} from "./BankMath";
import {BankFigure} from "./BankImages";

/** The full frozen problem is visible directly; answers are never part of it. */
export function QuestionContext({question,token,courseId="",wholePaper=false}:{question:Question;token:string;courseId?:string;wholePaper?:boolean}){
 const full=question.whole_stem;
 const legacy=question.context_stem;
 if(!full&&!legacy)return <>{question.display_group&&question.display_group.order.length>1&&<p className="hint">当前记录只保存了本小问，完整大题题干未录入；请先在题库补全公共条件。</p>}<BankMath text={question.stem} token={token}/>{question.illustrations?.map((image,i)=><BankFigure key={i} image={image} token={token} courseId={courseId}/>)}</>;
 return <section className="bank-full-context" aria-label="整道题目">
   <h4>整道题目</h4>
   {full?<><BankMath text={full} token={token}/>{question.whole_illustrations?.map((image,i)=><BankFigure key={i} image={image} token={token} courseId={courseId}/>)}</>:<>
     <p className="hint">历史作答保留的题干与本题如下；缺失的原文不会自动补写。</p>
     <BankMath text={legacy!} token={token}/>{question.context_illustrations?.map((image,i)=><BankFigure key={i} image={image} token={token} courseId={courseId}/>) }
     <h4>原作答小题</h4><BankMath text={question.stem} token={token}/>{question.illustrations?.map((image,i)=><BankFigure key={i} image={image} token={token} courseId={courseId}/>) }
   </>}
   <p className="hint">{wholePaper?"请按下方各小问分别作答；完整大题仅在此展示一次。":`本次作答：${question.source_number?`原题 ${question.source_number}`:"抽中的小题"}。其他小问供理解整道题，不计入本次作答。`}</p>
 </section>;
}
