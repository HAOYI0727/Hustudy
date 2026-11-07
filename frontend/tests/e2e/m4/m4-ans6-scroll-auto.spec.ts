import {existsSync} from "node:fs";
import {test,expect} from '@playwright/test';
import {resolve} from 'node:path';
const base='http://127.0.0.1:8056/api/v1';
async function setup(page:any,request:any){
 const auth=await(await request.post(base+'/auth/register',{data:{username:'auto_'+crypto.randomUUID().replaceAll('-',''),password:'Synthetic-password-2026'}})).json();
 const headers={Authorization:'Bearer '+auth.access_token};
 const course=await(await request.post(base+'/courses',{headers,data:{name:'自动归类与演示'}})).json();
 await page.addInitScript(a=>{localStorage.setItem('hustudy_token',a.access_token);localStorage.setItem('hustudy_user',a.user.username);},auth);
 return {headers,course};
}
test('ans6完整演示稿17题、公式表格、切换审核不强制滚顶',async({page,request})=>{
 test.skip(!existsSync(resolve('../.artifacts/e2e/ans6-完整演示题库.md')),'Private generated ans6 sample remains local');
 const {course}=await setup(page,request);await page.goto(`/exam?course=${course.id}`);
 await page.getByLabel('上传本地题库（Markdown / ZIP）').setInputFiles(resolve('../.artifacts/e2e/ans6-完整演示题库.md'));
 await page.getByRole('button',{name:'上传选中文件并开始导入',exact:true}).click();
 await expect(page.getByRole('heading',{name:'题目校正 · 共17题'})).toBeVisible({timeout:30000});
 await expect(page.locator('.bank-question-editor')).toHaveCount(17);
 const first=page.locator('.bank-question-editor').first();await expect(first.locator('.bank-question-values').getByLabel('题目年份',{exact:true})).toHaveValue('2023');await expect(first.locator('.bank-question-values').getByLabel('原题分值（未知留空，不自动分摊父题分值）',{exact:true})).toHaveValue('5');await expect(first.locator('.bank-markdown-source input[aria-label="题目年份"]')).toHaveCount(0);expect(await first.locator('.bank-markdown-source').getAttribute('open')).toBeNull();
 await page.getByRole('button',{name:'考点、统计与蓝图',exact:true}).click();
 await expect(page.getByRole('region',{name:'考点目录',exact:true})).toBeVisible();
 await page.evaluate(()=>{document.querySelector('.bank-tabs')!.scrollIntoView({block:'center'});});
 const before=await page.evaluate(()=>window.scrollY);expect(before).toBeGreaterThan(0);
 await page.evaluate(()=>{const original=window.scrollTo.bind(window);(window as any).__scrollCalls=[];window.scrollTo=((...args:any[])=>{(window as any).__scrollCalls.push(args);return (original as any)(...args);}) as typeof window.scrollTo;});
 await page.getByRole('button',{name:'上传与校正题库',exact:true}).click();
 await expect(page.getByRole('heading',{name:'题目校正 · 共17题'})).toBeVisible();
 expect(await page.evaluate(()=>(window as any).__scrollCalls.length)).toBe(0);
 expect(await page.evaluate(()=>window.scrollY)).toBeGreaterThan(0);
});
for(const fail of [false,true])test(`未归类自动采用${fail?'失败保留':'成功移除'}（模拟Provider结果）`,async({page,request})=>{
 const {headers,course}=await setup(page,request);
 const paper=await(await request.post(`${base}/courses/${course.id}/question-bank/import`,{headers,data:{title:'自动分类',content:'1. 什么是拥塞控制？'}})).json();
 const q=paper.questions[0];const topic=await(await request.post(`${base}/courses/${course.id}/topics`,{headers,data:{name:'拥塞控制'}})).json();
 await page.route('**/question-bank/ai-capabilities',r=>r.fulfill({json:{configured:true,model:'deepseek-flash',vendor:'deepseek',endpoint:'https://api.deepseek.com/chat/completions',vision_configured:true}}));
 let classified=false,submitted=false;
 const state={preview_id:'auto-job',paper_id:paper.id,model:'deepseek-flash',endpoint:'https://api.deepseek.com/chat/completions',expires_at:'2099-01-01'};
 await page.route('**/past-questions/*/auto-classify',async r=>{submitted=true;expect(r.request().postDataJSON()).toEqual({revision:q.revision,confirm_remote_send:true});await r.fulfill({status:202,json:{...state,status:'QUEUED'}});});
 await page.route('**/past-papers/*/topic-ai-preview',r=>{if(!submitted)return r.fulfill({json:{paper_id:paper.id,status:'NONE',model:'deepseek-flash'}});classified=!fail;return r.fulfill({json:{...state,status:fail?'FAILED':'SUCCEEDED',error:fail?'模拟无法判断':null}});});
 await page.route('**/question-directory?*',async r=>{const response=await r.fetch();const data=await response.json();if(classified)for(const item of data.items)if(item.id===q.id){item.bank_data.topic_ids=[topic.id];item.topic_id=topic.id;item.revision++;}await r.fulfill({response,json:data});});
 await page.goto(`/exam?course=${course.id}`);await page.getByRole('button',{name:'考点、统计与蓝图',exact:true}).click();
 await page.getByRole('button',{name:/未归类/}).click();
 await expect(page.locator('.bank-directory-question')).toHaveCount(1);
 await page.getByRole('button',{name:'AI自动归类题号1',exact:true}).click();
 if(fail){await expect(page.getByRole('alert').filter({hasText:'模拟无法判断'})).toBeVisible();await expect(page.locator('.bank-directory-question')).toHaveCount(1);}
 else{await expect(page.locator('.bank-directory-question')).toHaveCount(0,{timeout:15000});await expect(page.getByText('AI已自动归类，题目已从未归类列表移除',{exact:true})).toBeVisible();}
});
