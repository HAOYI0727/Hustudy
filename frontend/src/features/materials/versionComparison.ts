import type {Chunk} from "../../api/client";
export type ComparisonRow = {key:string;status:"same"|"changed"|"left"|"right";left?:Chunk;right?:Chunk;ambiguous:boolean};
export type VersionComparison = {rows:ComparisonRow[];excludedLeft:number;excludedRight:number;ambiguous:number;differentLocators:boolean};
const locator = (chunk:Chunk) => JSON.stringify([chunk.locator_type,chunk.locator_value]);
/** Exact, unique locators only. No fuzzy/semantic matching and no HTML rendering. */
export function compareVersionText(left:Chunk[],right:Chunk[]):VersionComparison {
  const a=left.filter(c=>!c.source_kind||c.source_kind==="extracted"),b=right.filter(c=>!c.source_kind||c.source_kind==="extracted");
  const counts=(rows:Chunk[])=>{const result=new Map<string,number>();for(const row of rows){const k=locator(row);result.set(k,(result.get(k)||0)+1);}return result;};
  const ac=counts(a),bc=counts(b),rightByKey=new Map(b.map(c=>[locator(c),c])),matched=new Set<string>();
  const rows:ComparisonRow[]=a.map(chunk=>{
    const k=locator(chunk),ambiguous=(ac.get(k)||0)>1||(bc.get(k)||0)>1;
    const pair=!ambiguous?rightByKey.get(k):undefined;
    if(pair)matched.add(pair.id);
    return {key:"left:"+chunk.id,left:chunk,right:pair,status:pair?(chunk.text===pair.text?"same":"changed"):"left",ambiguous};
  });
  for(const chunk of b)if(!matched.has(chunk.id))rows.push({key:"right:"+chunk.id,right:chunk,status:"right",ambiguous:(ac.get(locator(chunk))||0)>1||(bc.get(locator(chunk))||0)>1});
  const types=new Set(a.map(c=>c.locator_type));
  return {rows,excludedLeft:left.length-a.length,excludedRight:right.length-b.length,ambiguous:rows.filter(r=>r.ambiguous).length,differentLocators:!!a.length&&!!b.length&&!b.some(c=>types.has(c.locator_type))};
}
export function filterComparison(rows:ComparisonRow[],mode:"changed"|"all",query:string):ComparisonRow[] {
  const q=query.trim().toLocaleLowerCase();
  return rows.filter(r=>(mode==="all"||r.status!=="same")&&[r.left?.locator_value,r.right?.locator_value,r.left?.text,r.right?.text].some(s=>s?.toLocaleLowerCase().includes(q)));
}
