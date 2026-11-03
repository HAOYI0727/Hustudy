import {NotePreview} from "../../components/knowledge";
export function BankMath({text,token}:{text:string;token:string}){return <div className="bank-math"><NotePreview singleTilde={false} content={text} token={token} notes={[]} onNote={()=>{}}/></div>;}
