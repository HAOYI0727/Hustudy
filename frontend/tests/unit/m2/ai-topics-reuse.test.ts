import {createElement} from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,test} from 'vitest';
import type {AIAnswer} from '../../../src/api/client';
import {QuestionDraftView} from '../../../src/features/ai/QuestionDraftView';
import {ReusableResult} from '../../../src/features/ai/ReusableResult';
import {AIResultStatus} from '../../../src/features/ai/AIResultStatus';

test('题目逐题显示所关联的知识点，而不是全部所选目标',()=>{
  const answer:AIAnswer={id:'r',course_id:'c',query:'出题',status:'grounded',model_mode:'real',result:{
    exam_context:{topics:[{id:'t1',name:'函数作为参数'},{id:'t2',name:'函数作为结果'}],references:[]},
    question_drafts:[{question_id:'q1',chapter_id:'v',type:'boolean',stem:'参数问题',options:[],answer:true,rubric:[],points:5,explanation:'说明',topic_ids:['t1'],difficulty_label:'basic',mode:'historical',original_past_question_ids:[],material_citations:[],generation_status:'draft'},
    {question_id:'q2',chapter_id:'v',type:'boolean',stem:'结果问题',options:[],answer:false,rubric:[],points:5,explanation:'说明',topic_ids:['t2'],difficulty_label:'basic',mode:'historical',original_past_question_ids:[],material_citations:[],generation_status:'draft'}]
  }};
  const html=renderToStaticMarkup(createElement(QuestionDraftView,{answer,onSource:()=>{}}));
  expect(html).toContain('考查知识点：函数作为参数');
  expect(html).toContain('考查知识点：函数作为结果');
  expect(html).not.toContain('考查知识点：函数作为参数、函数作为结果');
});

test('复用提示说明无需调用，并保留用户重新生成的选择',()=>{
  const answer:AIAnswer={id:'r',course_id:'c',query:'原问题',status:'grounded',model_mode:'real',result:{model:'glm-5.3-flash'}};
  const html=renderToStaticMarkup(createElement(ReusableResult,{answer,disabled:true,onReuse:()=>{}}));
  expect(html).toContain('使用已有结果（不调用AI）');
  expect(html).toContain('确认后重新生成');
  expect(html).toContain('disabled');
  expect(renderToStaticMarkup(createElement(AIResultStatus,{status:'provider_error',errorCode:'INVALID_TOPICS'}))).toContain('知识点关联不符');
});
