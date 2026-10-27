/** Bounded local recovery copies. Never contains credentials or dispatches a request. */
export type NoteDraft={title:string;content:string;tags:string[];folder_id?:string|null};
export type RecoveryCitation={version_id:string;chunk_id:string;quote:string};
export type PendingNote=NoteDraft&{course_id:string;request_id:string;citations?:RecoveryCitation[]};
export type NoteRecovery={id:string;userId:string;courseId:string;noteId:string|null;noteCourseId:string|null;baseRevision:number|null;base?:NoteDraft|null;draft:NoteDraft;tagInput:string;pending:PendingNote|null;citations?:RecoveryCitation[];updatedAt:string};
const prefix=(userId:string)=>`hustudy-note-recovery:v1:${userId}:`;
const key=(row:Pick<NoteRecovery,"userId"|"courseId"|"id">)=>`${prefix(row.userId)}${row.courseId}:${row.id}`;
const uuid=(value:unknown):value is string=>typeof value==="string"&&/^[\da-f]{8}-(?:[\da-f]{4}-){3}[\da-f]{12}$/i.test(value);
const bytes=(value:string)=>new TextEncoder().encode(value).length;
const maxItem=1024*1024,maxTotal=3*1024*1024,retention=30*86400000;
function validDraft(value:any):value is NoteDraft{return value&&typeof value.title==="string"&&Array.from(value.title).length<=240&&typeof value.content==="string"&&Array.isArray(value.tags)&&value.tags.length<=12&&value.tags.every((tag:unknown)=>typeof tag==="string"&&Array.from(tag).length<=32)&&(value.folder_id===undefined||value.folder_id===null||uuid(value.folder_id));}
const validCitations=(value:any)=>value===undefined||Array.isArray(value)&&value.length<=50&&value.every(item=>item&&uuid(item.version_id)&&uuid(item.chunk_id)&&typeof item.quote==="string"&&item.quote.length>0&&item.quote.length<=20000);
function valid(value:any,userId:string):value is NoteRecovery{
  if(value?.base!==undefined&&value.base!==null&&(!validDraft(value.base)||!uuid(value.noteId)||!Number.isInteger(value.baseRevision)||value.baseRevision<1))return false;
  return value&&uuid(value.id)&&value.userId===userId&&uuid(value.courseId)&&(value.noteId===null||uuid(value.noteId))&&(value.noteCourseId===null||uuid(value.noteCourseId))&&(value.baseRevision===null||Number.isInteger(value.baseRevision)&&value.baseRevision>=1)&&validDraft(value.draft)&&validCitations(value.citations)&&typeof value.tagInput==="string"&&value.tagInput.length<=2000&&typeof value.updatedAt==="string"&&Number.isFinite(Date.parse(value.updatedAt))&&Date.parse(value.updatedAt)>Date.now()-retention&&Date.parse(value.updatedAt)<=Date.now()+300000&&(value.pending===null||validDraft(value.pending)&&uuid(value.pending.request_id)&&value.pending.course_id===value.courseId&&validCitations(value.pending.citations));
}
export function recoveryCopies(userId:string,courseId?:string):{items:NoteRecovery[];available:boolean}{
  if(!uuid(userId))return {items:[],available:false};
  try{
    const items:NoteRecovery[]=[];
    for(let i=0;i<localStorage.length;i++){
      const entry=localStorage.key(i);if(!entry?.startsWith(prefix(userId)))continue;
      const raw=localStorage.getItem(entry)||"";if(bytes(raw)>maxItem)continue;
      try{const value:unknown=JSON.parse(raw);if(valid(value,userId)&&key(value)===entry&&(!courseId||value.courseId===courseId))items.push(value);}catch{/* Ignore malformed records without exposing them as notes. */}
    }
    return {items:items.sort((a,b)=>b.updatedAt.localeCompare(a.updatedAt)),available:true};
  }catch{return {items:[],available:false};}
}
export function saveRecovery(row:NoteRecovery):string{
  try{
    if(!valid(row,row.userId))return "恢复副本字段不合法，请立即保存或复制正文。";
    const serialized=JSON.stringify(row),size=bytes(serialized);
    if(size>maxItem)return "这份草稿超过本机恢复副本1 MiB上限，请立即保存或导出正文。";
    const index=recoveryCopies(row.userId);if(!index.available)return "浏览器存储不可用，未能保存恢复副本，请立即保存或复制正文。";
    const others=index.items.filter(item=>key(item)!==key(row));
    if(others.length>=20||others.reduce((sum,item)=>sum+bytes(JSON.stringify(item)),size)>maxTotal)return "本机恢复副本已达20份或3 MiB，请先清理不需要的副本；当前内容仍需保存。";
    // Only this account's expired, validly namespaced records are cleaned.
    const expired:string[]=[];
    for(let i=0;i<localStorage.length;i++){const entry=localStorage.key(i);if(!entry?.startsWith(prefix(row.userId)))continue;try{const value=JSON.parse(localStorage.getItem(entry)||"null");if(value?.userId===row.userId&&typeof value.updatedAt==="string"&&Date.parse(value.updatedAt)<=Date.now()-retention)expired.push(entry);}catch{/* Keep malformed records for explicit browser cleanup. */}}
    expired.forEach(entry=>localStorage.removeItem(entry));
    localStorage.setItem(key(row),serialized);return "";
  }catch{return "本机恢复副本写入失败（存储空间或权限不足），请立即保存或复制正文。";}
}
export function removeRecovery(row:Pick<NoteRecovery,"userId"|"courseId"|"id">){try{localStorage.removeItem(key(row));return true;}catch{return false;}}
