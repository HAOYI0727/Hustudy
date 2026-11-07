import {test,expect} from '@playwright/test';
import {readFileSync} from 'node:fs';import {join} from 'node:path';
const base='http://127.0.0.1:8056/api/v1';
test('真实ZIP转写的35道大题存储后渲染253公式和31张表格',async({page,request})=>{
 test.skip(!process.env.HUSTUDY_TEST_BANK_TRANSCRIPTS,'Private model outputs require explicitly provided directory');test.setTimeout(120000);
 const a=await(await request.post(base+'/auth/register',{data:{username:'real_md_'+crypto.randomUUID().replaceAll('-',''),password:'Test-password-2026'}})).json();const headers={Authorization:'Bearer '+a.access_token};const c=await(await request.post(base+'/courses',{headers,data:{name:'真实转写Markdown验收'}})).json();
 for(const year of ['2021','2022','2023','2024','2025']){
  const qs=JSON.parse(readFileSync(join(process.env.HUSTUDY_TEST_BANK_TRANSCRIPTS!,year+'-试卷','questions.json'),'utf8'));
  const p=await(await request.post(`${base}/courses/${c.id}/question-bank/import`,{headers,data:{title:year+'试卷转写',content:qs.map((q:any,i:number)=>`${i+1}. ${year}原题${q.number}`).join('\n')}})).json();expect(p.questions).toHaveLength(qs.length);
  for(let i=0;i<qs.length;i++){const r=await request.patch(`${base}/past-questions/${p.questions[i].id}`,{headers,data:{revision:p.questions[i].revision,stem:qs[i].stem,question_type:qs[i].kind,options:qs[i].options,answer:null,topic_ids:[],explanation:''}});expect(r.ok()).toBeTruthy();expect((await r.json()).stem).toBe(qs[i].stem);}
 }
 await page.addInitScript((a:any)=>{localStorage.setItem('hustudy_token',a.access_token);localStorage.setItem('hustudy_user',a.user.username);},a);await page.goto(`/exam?course=${c.id}`);
 await expect(page.getByRole('heading',{name:'题目校正 · 共35题',exact:true})).toBeVisible();await expect(page.locator('.bank-question-editor .bank-math .katex')).toHaveCount(253);await expect(page.locator('.bank-question-editor .bank-math table')).toHaveCount(31);await expect(page.locator('.math-error')).toHaveCount(0);
 await page.setViewportSize({width:390,height:900});await page.locator('.bank-question-editor .bank-math table').first().scrollIntoViewIfNeeded();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();await page.screenshot({path:'../.artifacts/e2e/m4-real-markdown-tables-mobile.png'});
});
