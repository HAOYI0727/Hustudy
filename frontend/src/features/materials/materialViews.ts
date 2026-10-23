export type MaterialViewFilters={q:string;category:string;tag:string;state:"all"|"ready"|"processing"|"failed";sort:"recent"|"name"|"size"};
export type MaterialView={id:string;name:string;filters:MaterialViewFilters};
const uuid=(s:unknown):s is string=>typeof s==="string"&&/^[\da-f]{8}-(?:[\da-f]{4}-){3}[\da-f]{12}$/i.test(s);
const key=(user:string,course:string)=>`hustudy-material-views:v1:${user}:${course}`;
const bytes=(s:string)=>new TextEncoder().encode(s).length;
function filters(value:unknown):value is MaterialViewFilters{
 if(!value||typeof value!=="object")return false;const f=value as Record<string,unknown>;
 return Object.keys(f).length===5&&["q","category","tag"].every((field,i)=>typeof f[field]==="string"&&Array.from(f[field] as string).length<=[200,64,32][i])&&["all","ready","processing","failed"].includes(String(f.state))&&["recent","name","size"].includes(String(f.sort));
}
function valid(value:unknown):value is MaterialView[]{
 if(!Array.isArray(value)||value.length>8)return false;
 return value.every(v=>v&&Object.keys(v).length===3&&uuid(v.id)&&typeof v.name==="string"&&v.name===v.name.trim()&&Array.from(v.name).length>=1&&Array.from(v.name).length<=32&&filters(v.filters))&&new Set(value.map(v=>v.id)).size===value.length&&new Set(value.map(v=>v.name)).size===value.length;
}
export function materialViews(user:string,course:string):{items:MaterialView[];error:string}{
 if(!uuid(user)||!uuid(course))return {items:[],error:"请先核对当前账户与课程。"};
 try{const raw=localStorage.getItem(key(user,course));if(!raw)return {items:[],error:""};if(bytes(raw)>32768)throw new Error("budget");const value=JSON.parse(raw);if(value?.version!==1||Object.keys(value).length!==2||!valid(value.items))throw new Error("invalid");return {items:value.items,error:""};}
 catch{return {items:[],error:"本机常用视图不可读取（内容损坏、空间或权限问题）；仍可正常筛选资料。"};}
}
export function saveMaterialViews(user:string,course:string,items:MaterialView[]):string{
 if(!uuid(user)||!uuid(course)||!valid(items))return "视图设置不合法：最多8份，名称须唯一且为1–32字。";
 const raw=JSON.stringify({version:1,items});if(bytes(raw)>32768)return "本机常用视图超过32 KiB，请减少名称或筛选内容。";
 try{localStorage.setItem(key(user,course),raw);return "";}catch{return "本机常用视图未能写入，请检查浏览器存储空间与权限；筛选仍可使用。";}
}
