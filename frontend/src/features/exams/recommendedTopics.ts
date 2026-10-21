import type {BankTopicIndex,Topic} from "../../api/client";
export function recommendedTopics(current:string[],index:BankTopicIndex|undefined,topics:Topic[]){
 if(index?.selection_reviewed||!index?.version?.startsWith("bank-topic-ai-"))return {ids:current,overflow:false};
 const valid=new Set(topics.map(t=>t.id));
 const ids=[...new Set([...current,...(index.existing||[]).filter(r=>r.method==="ai"&&valid.has(r.topic_id)).map(r=>r.topic_id)])];
 return {ids:ids.length<=5?ids:current,overflow:ids.length>5};
}
