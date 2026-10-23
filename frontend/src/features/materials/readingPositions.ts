/** Browser preferences only: no content, credentials or answers are persisted. */
export type ReadingPosition = {courseId:string;documentId:string;versionId:string;chunkId:string;page:number;view:"text"|"native"|"pdf";name:string;updatedAt:string};
const key=(account:string)=>`hustudy-reading:v1:${encodeURIComponent(account)}`;
const uuid=(value:unknown):value is string=>typeof value==="string"&&/^[\da-f]{8}-(?:[\da-f]{4}-){3}[\da-f]{12}$/i.test(value);
export function readingPositions(account:string,courseId?:string):ReadingPosition[]{
  if(!account)return [];
  try{
    const stored:unknown=JSON.parse(localStorage.getItem(key(account))||"[]");
    if(!Array.isArray(stored))return [];
    return stored.filter((row):row is ReadingPosition=>!!row&&uuid(row.courseId)&&uuid(row.documentId)&&uuid(row.versionId)&&(!row.chunkId||uuid(row.chunkId))&&["text","native","pdf"].includes(row.view)&&Number.isInteger(row.page)&&row.page>0&&row.page<=100000&&typeof row.name==="string"&&row.name.length<=240&&typeof row.updatedAt==="string"&&Number.isFinite(Date.parse(row.updatedAt))&&Date.parse(row.updatedAt)>Date.now()-180*86400000)
      .filter(row=>!courseId||row.courseId===courseId).sort((a,b)=>b.updatedAt.localeCompare(a.updatedAt)).slice(0,60);
  }catch{return [];}
}
export function rememberReading(account:string,value:Omit<ReadingPosition,"updatedAt">){
  if(!account)return;
  try{
    const item={...value,name:value.name.slice(0,240),updatedAt:new Date().toISOString()};
    const rows=[item,...readingPositions(account).filter(row=>row.versionId!==item.versionId)].slice(0,60);
    localStorage.setItem(key(account),JSON.stringify(rows));
  }catch{/* Quota/private mode cannot block reading. */}
}
export function forgetReading(account:string,versionId:string){
  try{localStorage.setItem(key(account),JSON.stringify(readingPositions(account).filter(row=>row.versionId!==versionId)));}catch{/* Optional preference storage. */}
}
