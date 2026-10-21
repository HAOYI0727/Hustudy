export type DisplayGroup={key:string;label:string;order:number[]};
// Practice numbering follows the frozen random order. Only adjacent siblings share a header.
export function practiceQuestionGroups<T extends {id:string;display_group?:DisplayGroup|null}>(questions:T[]){
 const groups:{key:string;label:string;source:string;items:T[]}[]=[];
 for(const q of questions){
  const source=q.display_group?.key||`question:${q.id}`,last=groups[groups.length-1];
  if(last?.source===source)last.items.push(q);
  else groups.push({key:`${source}:${groups.length}`,source,label:q.display_group?.label||"",items:[q]});
 }
 return groups;
}
export function questionGroups<T extends {id:string;display_group?:DisplayGroup|null}>(questions:T[]){
 const groups=new Map<string,{key:string;label:string;items:T[];order:number[];paper:string;index:number}>();
 const papers=new Map<string,number>();
 for(const q of questions){
  const info=q.display_group,key=info?.key||`question:${q.id}`;
  const paper=info?info.key.slice(0,info.key.lastIndexOf(":")):key;
  if(!papers.has(paper))papers.set(paper,papers.size);
  if(!groups.has(key))groups.set(key,{key,label:info?.label||"",items:[],order:info?.order.slice(0,1)||[],paper,index:groups.size});
  groups.get(key)!.items.push(q);
 }
 const compare=(a:number[],b:number[])=>{for(let n=0;n<Math.max(a.length,b.length);n++){const diff=(a[n]??-1)-(b[n]??-1);if(diff)return diff;}return 0;};
 return [...groups.values()].sort((a,b)=>papers.get(a.paper)!-papers.get(b.paper)!||compare(a.order,b.order)||a.index-b.index).map(g=>({...g,items:[...g.items].sort((a,b)=>compare(a.display_group?.order||[],b.display_group?.order||[]))}));
}
