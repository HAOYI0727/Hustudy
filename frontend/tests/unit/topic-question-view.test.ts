import {describe,it,expect} from 'vitest';
import {directTopicQuestions,subtreeQuestionCount,questionDisplayKey} from '../../src/features/exams/topicQuestionView';
import type {PastQuestion,Topic} from '../../src/api/client';
const topics=[{id:'r',parent_id:null},{id:'c',parent_id:'r'},{id:'g',parent_id:'c'},{id:'s',parent_id:'r'}] as Topic[];
const q=(id:string,ids:string[],stem='同题',extra:object={})=>({id,stem,question_type:'solution',bank_data:{topic_ids:ids,...extra}} as PastQuestion);
describe('考点目录同题优先最深层',()=>{
 it('同ID多级归类及不同ID同题都不在祖先重复',()=>{const qs=[q('1',['r']),q('2',['r','c','g']),q('3',['r'],'父独有')];expect(directTopicQuestions(topics,qs,'r').map(v=>v.id)).toEqual(['3']);expect(directTopicQuestions(topics,qs,'c')).toEqual([]);expect(directTopicQuestions(topics,qs,'g').map(v=>v.id)).toEqual(['2']);expect(subtreeQuestionCount(topics,qs,'r')).toBe(2);});
 it('兄弟标签相同题可各自展示，取消分级后父级恢复显示',()=>{const qs=[q('1',['r']),q('2',['c']),q('3',['s'])];expect(directTopicQuestions(topics,qs,'c')).toHaveLength(1);expect(directTopicQuestions(topics,qs,'s')).toHaveLength(1);const detached=topics.map(t=>t.id==='c'||t.id==='s'?{...t,parent_id:null}:t);expect(directTopicQuestions(detached,qs,'r')).toHaveLength(1);});
 it('不同选项、插图或代码空格不误合并',()=>{expect(questionDisplayKey(q('1',[],'相同',{options:['甲']}))).not.toBe(questionDisplayKey(q('2',[],'相同',{options:['乙']})));expect(questionDisplayKey(q('1',[],'相同',{illustrations:[{asset_id:'a'}]}))).not.toBe(questionDisplayKey(q('2',[],'相同',{illustrations:[{asset_id:'b'}]})));expect(questionDisplayKey(q('1',[],'    x'))).toBe(questionDisplayKey(q('2',[],'x')));expect(questionDisplayKey(q('1',[],'a  b'))).not.toBe(questionDisplayKey(q('2',[],'a b')));});
});
