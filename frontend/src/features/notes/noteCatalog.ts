import {api,type NoteSummary} from "../../api/client";
/** The complete title/revision index supports UUID links and whole-course tools. Bodies stay lazy. */
export async function loadNoteCatalog(token:string):Promise<NoteSummary[]>{
  const notes=new Map<string,NoteSummary>();let total:number|undefined;
  for(let offset=0;offset<(total??1);offset+=200){
    const page=await api.noteCatalog(token,offset);
    if(page.total>20000)throw new Error("笔记索引超过20000篇，请先整理资料范围；没有截断目录。");
    if(total!==undefined&&page.total!==total)throw new Error("目录在读取期间发生变化，请刷新笔记列表。");
    total=page.total;page.items.forEach(note=>notes.set(note.id,note));
  }
  if(notes.size!==total)throw new Error("目录分页在读取期间变化，请刷新笔记列表。");
  return [...notes.values()].sort((a,b)=>b.updated_at.localeCompare(a.updated_at)||a.id.localeCompare(b.id));
}
