/** Local reading shortcuts. The original text is always read through authorized M1 APIs. */
export type ReadingBookmark = {
  id:string; documentId:string; versionId:string; chunkId:string; versionNo:number;
  documentName:string; locatorType:string; locatorValue:string; label:string; updatedAt:string;
};
export type BookmarkTarget = Omit<ReadingBookmark,"id"|"label"|"updatedAt">;
const uuid = (value:unknown):value is string => typeof value==="string" && /^[\da-f]{8}-(?:[\da-f]{4}-){3}[\da-f]{12}$/i.test(value);
const key = (owner:string,course:string) => `hustudy-bookmarks:v1:${owner}:${course}`;
const fields = ["id","documentId","versionId","chunkId","versionNo","documentName","locatorType","locatorValue","label","updatedAt"];
const short = (value:unknown,max:number):value is string => typeof value==="string" && !!value.trim() && value.length<=max;
/** Keep UTF-16 length compatible with maxlength while retaining whole Unicode characters. */
export function shortReadingLabel(value:string,max:number):string {let result="";for(const character of value){if(result.length+character.length>max)break;result+=character;}return result;}
function valid(value:unknown):value is ReadingBookmark {
  if(!value || typeof value!=="object" || Array.isArray(value))return false;
  const row=value as ReadingBookmark;
  return Object.keys(row).length===fields.length && Object.keys(row).every(k=>fields.includes(k)) &&
    [row.id,row.documentId,row.versionId,row.chunkId].every(uuid) && Number.isInteger(row.versionNo) && row.versionNo>0 &&
    short(row.documentName,240) && short(row.locatorType,40) && short(row.locatorValue,240) && short(row.label,80) &&
    typeof row.updatedAt==="string" && Number.isFinite(Date.parse(row.updatedAt)) && new Date(row.updatedAt).toISOString()===row.updatedAt;
}
export function readingBookmarks(owner:string,course:string):{items:ReadingBookmark[];error:string} {
  if(!uuid(owner)||!uuid(course))return {items:[],error:"请先确认当前账户与课程"};
  try {
    const raw=localStorage.getItem(key(owner,course));
    if(raw===null)return {items:[],error:""};
    if(new Blob([raw]).size>128*1024)throw new Error("size");
    const parsed:unknown=JSON.parse(raw);
    if(!parsed || typeof parsed!=="object" || Array.isArray(parsed))throw new Error("schema");
    const data=parsed as {version:number;items:unknown[]};
    if(Object.keys(data).length!==2 || data.version!==1 || !Array.isArray(data.items) || data.items.length>100 || !data.items.every(valid))throw new Error("schema");
    const items=data.items as ReadingBookmark[];
    if(new Set(items.map(r=>r.id)).size!==items.length || new Set(items.map(r=>r.versionId+":"+r.chunkId)).size!==items.length)throw new Error("duplicates");
    return {items:[...items].sort((a,b)=>b.updatedAt.localeCompare(a.updatedAt)||a.id.localeCompare(b.id)),error:""};
  } catch {return {items:[],error:"本机书签暂不可读，已保留原存储。请检查浏览器存储后重试。"};}
}
/** Re-read immediately before each edit, so another window's unrelated edits are retained. */
export function editReadingBookmark(owner:string,course:string,action:
  {kind:"save";target:BookmarkTarget;label:string} | {kind:"rename";id:string;label:string} | {kind:"remove";id:string}
):{items:ReadingBookmark[];error:string} {
  const current=readingBookmarks(owner,course);
  if(current.error)return current;
  let items=current.items;
  if(action.kind==="remove")items=items.filter(row=>row.id!==action.id);
  else {
    const label=action.label.trim();
    if(!short(label,80))return {...current,error:"书签名称需为1–80字"};
    const original=action.kind==="save" ? items.find(row=>row.versionId===action.target.versionId&&row.chunkId===action.target.chunkId) : items.find(row=>row.id===action.id);
    if(action.kind==="rename"&&!original)return {...current,error:"这条书签已被其他窗口移除，请刷新列表"};
    const next:ReadingBookmark=action.kind==="save" ? {...action.target,id:original?.id||crypto.randomUUID(),label,updatedAt:new Date().toISOString()} : {...original!,label,updatedAt:new Date().toISOString()};
    if(!valid(next))return {...current,error:"来源信息无效，书签未保存"};
    items=[next,...items.filter(row=>row.id!==next.id)];
  }
  if(items.length>100)return {...current,error:"每门课程最多100条书签，请先移除不再需要的书签"};
  const encoded=JSON.stringify({version:1,items});
  if(new Blob([encoded]).size>128*1024)return {...current,error:"书签已达到本机存储大小上限"};
  try {localStorage.setItem(key(owner,course),encoded);return {items,error:""};}
  catch {return {...current,error:"未能写入本机书签，请检查浏览器存储空间后重试"};}
}
