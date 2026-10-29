import type {PastQuestion,Topic} from "../../api/client";
import {topicDescendants} from "./TopicSearch";
export type TopicQuestion=Pick<PastQuestion,"id"|"stem"|"question_type"|"topic_id">&{fingerprint?:string;bank_data:PastQuestion["bank_data"]};
const normal=(value:string)=>value.normalize("NFKC").replace(/\r\n?/g,"\n").trim();
export function questionDisplayKey(q:TopicQuestion){
 if(q.fingerprint)return q.fingerprint;
 return normal(q.stem);
}
function questionTopicIds(q:TopicQuestion){return (q.bank_data.topic_ids||[q.topic_id]).filter((id):id is string=>Boolean(id));}
export function directTopicQuestions<T extends TopicQuestion>(topics:Topic[],questions:T[],id:string){
 const descendants=topicDescendants(topics,[id]);descendants.delete(id);
 const below=new Set(questions.filter(q=>questionTopicIds(q).some(t=>descendants.has(t))).map(questionDisplayKey));
 const seen=new Set<string>();
 return questions.filter(q=>{const key=questionDisplayKey(q);if(!questionTopicIds(q).includes(id)||below.has(key)||seen.has(key))return false;seen.add(key);return true;});
}
export function subtreeQuestionCount(topics:Topic[],questions:TopicQuestion[],id:string){const scope=topicDescendants(topics,[id]);return new Set(questions.filter(q=>questionTopicIds(q).some(t=>scope.has(t))).map(questionDisplayKey)).size;}
