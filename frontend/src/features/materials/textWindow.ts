import type {Chunk} from "../../api/client";

export function matchingText(chunks:Chunk[],query:string){
 const key=query.trim().toLocaleLowerCase();
 return key?chunks.filter(chunk=>(chunk.text+" "+chunk.locator_value).toLocaleLowerCase().includes(key)):chunks;
}
export function textWindow(total:number,requested:number,size:number){
 const length=Math.max(1,Math.trunc(size)||1),pages=Math.max(1,Math.ceil(total/length));
 const page=Math.min(pages-1,Math.max(0,Number.isFinite(requested)?Math.trunc(requested):0));
 return {page,pages,start:page*length,end:Math.min(total,(page+1)*length)};
}
export function pageForChunk(chunks:Pick<Chunk,"id">[],id:string,size:number){return Math.floor(Math.max(0,chunks.findIndex(chunk=>chunk.id===id))/Math.max(1,size));}
