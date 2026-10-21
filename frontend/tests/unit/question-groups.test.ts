import {test,expect} from 'vitest';
import {questionGroups,practiceQuestionGroups} from '../../src/features/exams/questionGroups';

test('大题按来源和显式题号分组，子题自然排序且不丢类型答案',()=>{
 const item=(id:string,paper:string,order:number[],type:string)=>({id,type,answer:id,display_group:{key:`${paper}:${order[0]}`,label:`第${order[0]}大题`,order}});
 const questions=[item('a10','p',[1,10],'solution'),item('a2','p',[1,2],'fill_blank'),item('b','other',[1,1],'single_choice'),item('a1','p',[1,1],'single_choice')];
 const groups=questionGroups(questions);
 expect(groups.map(g=>g.items.map(q=>q.id))).toEqual([['a1','a2','a10'],['b']]);
 expect(groups[0].items.map(q=>q.type)).toEqual(['single_choice','fill_blank','solution']);
 expect(groups[0].items.map(q=>q.answer)).toEqual(['a1','a2','a10']);
 expect(questions.map(q=>q.id)).toEqual(['a10','a2','b','a1']);
});
test('历史无分组快照不猜合并，不改变顺序',()=>{
 expect(questionGroups([{id:'b'},{id:'a'}]).map(g=>g.items[0].id)).toEqual(['b','a']);
});

test('随机练习按冻结题号顺序展示，仅合并相邻同大题子问',()=>{
 const item=(id:string,group:number,sub:number)=>({id,display_group:{key:`paper:${group}`,label:`第${group}大题`,order:[group,sub]}});
 const questions=[item('a10',1,10),item('b3',2,3),item('a2',1,2),item('a1',1,1),{id:'legacy'}];
 const groups=practiceQuestionGroups(questions);
 expect(groups.map(g=>g.items.map(q=>q.id))).toEqual([['a10'],['b3'],['a2','a1'],['legacy']]);
 expect(groups.flatMap(g=>g.items)).toEqual(questions);
 expect(new Set(groups.map(g=>g.key)).size).toBe(groups.length);
});
