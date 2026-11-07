import {test,expect} from 'vitest';
import {recommendedTopics} from '../../../src/features/exams/recommendedTopics';
const topics=[{id:'a',name:'已有',aliases:[],revision:1},{id:'b',name:'另一个',aliases:[],revision:1}];
const index={version:'bank-topic-ai-v3',existing:[{topic_id:'b',name:'另一个',method:'ai',reason:'语义匹配'}],candidates:['新备选']};
test('已有AI推荐默认合并勾选，备选不创建，未知ID不选',()=>{
 expect(recommendedTopics(['a'],index,topics)).toEqual({ids:['a','b'],overflow:false});
 expect(recommendedTopics([],index,[]).ids).toEqual([]);
});
test('人工保存的取消保留，超限不覆盖当前选择',()=>{
 expect(recommendedTopics([],{...index,selection_reviewed:true},topics).ids).toEqual([]);
 const current=Array.from({length:5},(_,i)=>String(i));
 expect(recommendedTopics(current,index,topics)).toEqual({ids:current,overflow:true});
});
