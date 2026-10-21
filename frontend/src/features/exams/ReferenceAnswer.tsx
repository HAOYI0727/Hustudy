import {Question} from "../../api/client";
import {BankMath} from "./BankMath";

export function ReferenceAnswer({question:q,token}:{question:Question;token:string}){
 const solution=["solution","short_answer"].includes(q.type);
 const answer=q.type==="fill_blank"&&q.blank_answers?.length?q.blank_answers.join("；"):q.answer==null?"":String(q.answer);
 const explanation=q.explanation?.trim()||q.rubric?.join("\n\n")||"";
 return <section className="bank-reference" aria-label="参考答案与解答">
  <h4>{solution?"参考解答":"参考答案"}</h4><BankMath text={answer.trim()||"原题未提供参考答案。"} token={token}/>
  <h4>{solution?"解析":"参考解答"}</h4><BankMath text={explanation||"原题未提供参考解答。"} token={token}/>
 </section>;
}
