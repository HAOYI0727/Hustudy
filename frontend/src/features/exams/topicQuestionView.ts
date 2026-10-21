import type {PastQuestion,Topic} from "../../api/client";
import {topicDescendants} from "./TopicSearch";
const normal=(value:string)=>value.normalize("NFKC").replace(/\r\n?/g,"\n").trim();
export function questionDisplayKey(q:PastQuestion){
 const data=q.bank_data;
 const images=data.illustrations?.length?data.illustrations:data.source_images||[];
 return JSON.stringify([q.question_type,normal(q.stem),(data.options||[]).map(normal),images.map(v=>[v.asset_id,v.box||[0,0,1,1]])]);
}
function questionTopicIds(q:PastQuestion){return (q.bank_data.topic_ids||[q.topic_id]).filter((id):id is string=>Boolean(id));}
export function directTopicQuestions(topics:Topic[],questions:PastQuestion[],id:string){
 const descendants=topicDescendants(topics,[id]);descendants.delete(id);
 const below=new Set(questions.filter(q=>questionTopicIds(q).some(t=>descendants.has(t))).map(questionDisplayKey));
 const seen=new Set<string>();
 return questions.filter(q=>{const key=questionDisplayKey(q);if(!questionTopicIds(q).includes(id)||below.has(key)||seen.has(key))return false;seen.add(key);return true;});
}
export function subtreeQuestionCount(topics:Topic[],questions:PastQuestion[],id:string){const scope=topicDescendants(topics,[id]);return new Set(questions.filter(q=>questionTopicIds(q).some(t=>scope.has(t))).map(questionDisplayKey)).size;}
