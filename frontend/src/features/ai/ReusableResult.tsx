import {AIAnswer} from "../../api/client";

export function ReusableResult({answer,disabled,onReuse}:{answer:AIAnswer;disabled:boolean;onReuse:()=>void}) {
  return <section className="ai-privacy-card" aria-label="可复用的生成结果">
    <strong>已有相同资料和设置的成功结果</strong>
    <p>问题、资料片段、模型和生成设置均匹配。直接使用无需调用AI；也可以在下方确认后重新生成。</p>
    <p className="hint">{answer.query} · {answer.result.model}</p>
    <button type="button" className="primary" disabled={disabled} onClick={onReuse}>使用已有结果（不调用AI）</button>
  </section>;
}
