import {createElement} from "react";
import {renderToStaticMarkup} from "react-dom/server";
import {describe,it,expect} from "vitest";
import {ReportLabelSource,labelSourceText} from "../../../src/features/ai/ReportLabelSource";
import {SupplementPreview,SupplementInputs} from "../../../src/features/ai/SupplementInputs";
import {beginReportReview,reviewedReportMarkdown,reviewError} from "../../../src/features/ai/report-review";
import type {ReportLabel,StudyReport,AISupplement} from "../../../src/api/client";

describe("M2 supplemental provenance",()=>{
  it('limits optional controls to notes and never asks for teacher or exam sources',()=>{
    const html=renderToStaticMarkup(createElement(SupplementInputs,{token:'test',courseId:'c',value:{note_ids:[],notes_confirmed:false},onChange:()=>{},disabled:false}));
    expect(html).toContain('补充笔记 · 可选');
    for(const text of ['记录教师强调','对应资料','查找已核验题库','真题依据（可选）'])expect(html).not.toContain(text);
  });
  it.each([['ai_suggestion','AI建议'],['teacher_mark','教师强调'],['observed_exam','已确认真题']] as const)('shows %s from the actual origin', (origin,name)=>{
    const label:ReportLabel={kind:'exam',origin,reason:'有依据的说明'};
    expect(renderToStaticMarkup(createElement(ReportLabelSource,{label}))).toContain(name);
    expect(labelSourceText({...label,availability:'unavailable'})).toContain('依据已失效');
  });
  it('preserves independent origins and evidence in note exports while editing unique kinds',()=>{
    const report:StudyReport={summary:'总结',learning_goals:['学习'],prerequisites:[],learning_sequence:['读原文'],examples:[],self_checks:[],topics:[{topic_id:'one',name:'知识点',explanation:'讲解',misconceptions:[],citations:[],labels:[
      {kind:'exam',origin:'teacher_mark',reason:'老师课堂强调',evidence:[{quote:'课件原文'}]},
      {kind:'exam',origin:'observed_exam',reason:'已确认题目',evidence:[{paper_title:'2024试卷',question_id:'q1',year:2024}]}]}]};
    const review=beginReportReview(report);
    expect(reviewError(review)).toBe('');expect(review.labels[0]).toHaveLength(1);
    const markdown=reviewedReportMarkdown(review);
    for(const text of ['教师强调','已确认真题','课件原文','2024试卷','q1'])expect(markdown).toContain(text);
    expect(report.topics[0].labels).toHaveLength(2);
  });
  it('previews selected note content as escaped text and explains unsupported exam scope',()=>{
    const value:AISupplement={notes:[{id:'n1',title:'我的笔记',revision:2,content:'<img src="https://example.test/private" onerror="evil()">'}],teacher_marks:[],exam_evidence:[],exam_paper_ids:['p1']};
    const html=renderToStaticMarkup(createElement(SupplementPreview,{value}));
    expect(html).toContain('我的笔记');expect(html).not.toContain('所选真题');
    expect(html).not.toContain('<img');expect(html).toContain('&lt;img');
  });
});
