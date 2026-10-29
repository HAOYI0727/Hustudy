import example from "./bankExample.md?raw";
import {BankMath} from "./BankMath";

export function BankFormatExample({token}:{token:string}){
 const download=()=>{const url=URL.createObjectURL(new Blob([example],{type:"text/markdown;charset=utf-8"}));const a=document.createElement("a");a.href=url;a.download="Hustudy-题库完整样例.md";a.click();window.setTimeout(()=>URL.revokeObjectURL(url),1000);};
 return <section className="bank-format-example" aria-label="严格Markdown完整样例"><p className="hint">自制完整样例包含选择题、解答题、公共条件、表格、行内与独立公式、上下标、逻辑符号、代码和未知答案。年份使用“### 年份”后单独一行填写1900–2200的整数（如2023），分值使用“### 分值”后单独一行填写1–500整数（如10），不要带“年/分”单位；空字段表示未知。省略年份则沿用导入时的试卷年份。原文有值会自动填入，可在题目上方修改。下载后保留字段结构；不会自动导入。</p><button type="button" className="secondary" onClick={download}>下载完整Markdown样例</button><details><summary>查看完整Markdown源码</summary><pre>{example}</pre></details><details><summary>预览样例公式与表格</summary><BankMath token={token} text={example}/></details></section>;
}
