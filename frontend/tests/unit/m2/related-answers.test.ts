import {createElement} from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,test} from 'vitest';
import {RelatedAnswers} from '../../../src/features/ai/RelatedAnswers';

test('相近问答明确展示原问题和摘要，不自动采用或声称语义相同',()=>{
  const html=renderToStaticMarkup(createElement(RelatedAnswers,{
    token:'synthetic',queryId:'preview',currentQuestion:'仅依据资料解释ACID',disabled:false,
    candidates:[{id:'saved',query:'依据资料解释ACID',answer_preview:'<script>alert(1)</script>',model:'synthetic',created_at:'2026-11-01T00:00:00Z'}],
    onBusyChange:()=>{},onAdopt:()=>{throw new Error('Cannot auto-adopt');},
  }));
  expect(html).toContain('本次问题');expect(html).toContain('原问题');
  expect(html).toContain('可能与本次问题要求不同');expect(html).toContain('查看原答案');
  expect(html).not.toContain('<script>');expect(html).not.toContain('确认使用这条历史答案');
});

test('报告候选明确显示原学习目标，先查看原报告且不自动采用',()=>{
  const html=renderToStaticMarkup(createElement(RelatedAnswers,{
    token:'synthetic',queryId:'report-preview',currentQuestion:'仅整理苹果加法报告',kind:'study_report',disabled:false,
    candidates:[{id:'saved-report',query:'整理苹果加法报告',answer_preview:'原报告摘要',model:'synthetic',created_at:'2026-11-01T00:00:00Z'}],
    onBusyChange:()=>{},onAdopt:()=>{throw new Error('Cannot auto-adopt');},
  }));
  expect(html).toContain('相近历史报告');expect(html).toContain('本次学习目标');expect(html).toContain('原学习目标');
  expect(html).toContain('可能与本次学习目标要求不同');expect(html).toContain('查看原报告');
  expect(html).not.toContain('确认使用这份历史报告');expect(html).not.toContain('本次问题');
});
