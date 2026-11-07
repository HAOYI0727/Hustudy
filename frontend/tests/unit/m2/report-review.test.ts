import {describe,expect,it} from 'vitest';
import {createElement} from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {StudyReportView} from '../../../src/features/ai/StudyReportView';
import type {StudyReport} from '../../../src/api/client';
import {beginReportReview,beginTopicReview,reviewedReportMarkdown,reviewError} from '../../../src/features/ai/report-review';

const report:StudyReport={summary:'概念总结',learning_goals:['理解概念'],prerequisites:[],learning_sequence:['先阅读再练习'],topics:[{
  topic_id:'topic-1',name:'进程与线程',explanation:'概念解释',misconceptions:['不要混淆'],labels:[{kind:'key',origin:'ai_suggestion',reason:'原始理由'}],
  concept_group:'基础概念',related_concepts:[],breakthrough_steps:['先比较两种职责'],
  citations:[{version_id:'v1',chunk_id:'c1',quote:'第一行\n第二行',availability:'active',locator:{type:'heading',value:'基本概念'}}]
}],examples:[{question:'例题',answer:'例题解答',citations:[]}],self_checks:[{question:'自测',answer:'自测解答',citations:[]}],review_suggestions:['合上原文再解释']};

describe('FR-38 reviewed label note snapshots',()=>{
  it('extracts only the chosen topic and exact unique evidence without changing the original report',()=>{
    const input=structuredClone(report);
    input.topics.push({...structuredClone(input.topics[0]),topic_id:'topic-2',name:'另一知识点',explanation:'其他正文'});
    input.topics[0].citations.push(structuredClone(input.topics[0].citations[0]));
    const review=beginTopicReview(input,'topic-1');
    expect(review.report.citations).toHaveLength(1);
    expect(review.report.topics).toHaveLength(1);
    const markdown=reviewedReportMarkdown(review);
    for(const content of ['知识点摘记','概念解释','> 第一行','原始理由','不包含原报告其他知识点'])expect(markdown).toContain(content);
    for(const content of ['其他正文','概念总结','例题解答','自测解答','先阅读再练习','合上原文再解释'])expect(markdown).not.toContain(content);
    review.labels[0][0].reason='只改摘记';review.report.citations![0].quote='修改摘记';
    expect(input.topics[0].citations[0].quote).toBe('第一行\n第二行');
    expect(input.topics[0].labels[0].reason).toBe('原始理由');
    expect(input.topics).toHaveLength(2);
  });
  it('refuses ambiguous topics, missing or revoked evidence and over-budget notes',()=>{
    expect(()=>beginTopicReview(report,'missing')).toThrow('唯一定位');
    expect(()=>beginTopicReview({...report,topics:[report.topics[0],report.topics[0]]},'topic-1')).toThrow('唯一定位');
    const input=structuredClone(report);
    input.topics[0].citations=[];
    expect(()=>beginTopicReview(input,'topic-1')).toThrow('没有可验证引用');
    input.topics[0].citations=[{...report.topics[0].citations[0],availability:'unavailable'}];
    expect(()=>beginTopicReview(input,'topic-1')).toThrow('失效');
    input.topics[0].citations=Array.from({length:51},(_,i)=>({...report.topics[0].citations[0],chunk_id:'c'+i}));
    expect(()=>beginTopicReview(input,'topic-1')).toThrow('50');
    input.topics[0].citations.pop();
    expect(beginTopicReview(input,'topic-1').report.citations).toHaveLength(50);
  });
  it('shows locally grounded basic checks and preserves the replacement notice in notes',()=>{
    const notice='模型自测缺少依据，已舍弃并补充基础自测';
    const input={...report,validation_notices:[notice],self_checks:[{...report.self_checks[0],generation_origin:'rule_generated' as const}]};
    const html=renderToStaticMarkup(createElement(StudyReportView,{report:input,onSource:()=>{}}));
    expect(html).toContain('基础自测 · 根据已校验知识点或例题生成');
    expect(html).toContain(notice);
    expect(reviewedReportMarkdown(beginReportReview(input))).toContain(notice);
  });
  it('preserves server relation cleanup notice when creating a reviewed note',()=>{
    const input={...report,validation_notices:['已移除1条无效概念关系']};
    const review=beginReportReview(input);
    expect(reviewedReportMarkdown(review)).toContain('> 已移除1条无效概念关系');
    expect(input.validation_notices).toEqual(['已移除1条无效概念关系']);
  });
  it('keeps original suggestions, full teaching content and evidence when labels change',()=>{
    const review=beginReportReview(report);
    review.labels[0]=[{kind:'difficult',reason:'  我的理解仍需练习  '}];
    const markdown=reviewedReportMarkdown(review);
    expect(report.topics[0].labels[0]).toEqual({kind:'key',origin:'ai_suggestion',reason:'原始理由'});
    expect(markdown).toContain('重点（AI建议）：原始理由');
    expect(markdown).toContain('难点：我的理解仍需练习');
    for(const text of ['不代表教师要求','概念解释','先阅读再练习','基础概念','先比较两种职责','合上原文再解释','例题解答','自测解答','> 第一行','> 第二行'])expect(markdown).toContain(text);
    review.report.topics[0].citations[0].quote='changed';
    expect(report.topics[0].citations[0].quote).toBe('第一行\n第二行');
  });
  it('rejects empty reasons and duplicate kinds without silently dropping edits',()=>{
    const review=beginReportReview(report);
    review.labels[0][0].reason='  ';
    expect(reviewError(review)).toContain('理由');
    expect(()=>reviewedReportMarkdown(review)).toThrow();
    review.labels[0]=[{kind:'exam',reason:'原因1'},{kind:'exam',reason:'原因2'}];
    expect(reviewError(review)).toContain('不能重复');
  });
  it('allows removing all suggestions without rewriting the original AI labels',()=>{
    const review=beginReportReview(report);
    review.labels[0]=[];
    expect(reviewError(review)).toBe('');
    expect(reviewedReportMarkdown(review)).toContain('未保留标签。');
    expect(review.report.topics[0].labels).toHaveLength(1);
  });
});
