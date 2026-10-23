export type ManualChapter={id:string;title:string;markdown:string};
export const MANUAL_MAX_BYTES=512*1024;

export function manualChapters(markdown:string):ManualChapter[]{
  const chapters:ManualChapter[]=[];
  let current:ManualChapter|undefined;
  let fence:{character:string;length:number}|undefined;
  for(const line of markdown.replace(/\r\n?/g,"\n").split("\n")){
    const marker=/^ {0,3}(`{3,}|~{3,})(.*)$/.exec(line);
    if(marker){
      if(!fence)fence={character:marker[1][0],length:marker[1].length};
      else if(marker[1][0]===fence.character&&marker[1].length>=fence.length&&!marker[2].trim())fence=undefined;
    }else if(!fence){
      const heading=/^##\s+(.+?)(?:\s+#+)?\s*$/.exec(line);
      if(heading){current={id:"manual-chapter-"+(chapters.length+1),title:heading[1],markdown:""};chapters.push(current);}
    }
    if(current)current.markdown+=(current.markdown?"\n":"")+line;
  }
  return chapters;
}

export async function readManual(url:string,signal:AbortSignal):Promise<string>{
  const response=await fetch(url,{signal,cache:"no-cache"});
  if(!response.ok)throw new Error("完整使用手册暂时无法读取，请重试或下载后阅读。");
  const type=response.headers.get("Content-Type")||"";
  if(!/^(text\/(markdown|plain)|application\/octet-stream)(;|$)/i.test(type))throw new Error("手册文件格式不正确，请刷新网站版本后重试。");
  if(Number(response.headers.get("Content-Length"))>MANUAL_MAX_BYTES)throw new Error("手册超过读取预算，请下载后阅读。");
  const text=await response.text();
  if(new TextEncoder().encode(text).length>MANUAL_MAX_BYTES||!/^# Hustudy\b/m.test(text)||!manualChapters(text).length)throw new Error("手册内容不完整，请重试或下载后阅读。");
  return text;
}
