import {test,expect} from '@playwright/test';
const base='http://127.0.0.1:8056/api/v1';
test('标签归类限制展示、批量核验、考点跳转、练习搜索与错题标签筛选',async({page,request})=>{
 const auth=await(await request.post(base+'/auth/register',{data:{username:'ux_'+crypto.randomUUID().replaceAll('-',''),password:'Test-password-2026'}})).json();const headers={Authorization:'Bearer '+auth.access_token};
 const course=await(await request.post(base+'/courses',{headers,data:{name:'标签体验'}})).json();
 const p=await(await request.post(`${base}/courses/${course.id}/question-bank/import`,{headers,data:{title:'标签题库',content:'1. 解释缓存。\n知识标签：缓存\n2. 解释总线。\n知识标签：总线'}})).json();
 for(let i=0;i<24;i++)await request.post(`${base}/courses/${course.id}/topics`,{headers,data:{name:`无关标签${i}`}});
 await page.addInitScript(a=>{localStorage.setItem('hustudy_token',a.access_token);localStorage.setItem('hustudy_user',a.user.username);},auth);
 await page.goto(`/exam?course=${course.id}`);
 const first=page.locator('.bank-question-editor').first();if(await first.getAttribute('open')===null)await first.locator(':scope > summary').click();
 await expect(first.locator('.bank-topic-option')).toHaveCount(1);
 await first.getByLabel('搜索其他知识标签').fill('无关标签23');await expect(first.locator('.bank-topic-option')).toHaveCount(2);
 await page.getByLabel('全选本页').check();await page.getByRole('button',{name:'核验所选（2）',exact:true}).click();await expect(page.getByText('所选题目已核验，题库审核状态已同步',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'考点、统计与蓝图',exact:true}).click();
 await page.getByRole('button',{name:'缓存 · 1题',exact:true}).click();await page.getByRole('button',{name:'在上传与校正中查看'}).click();await expect(page.getByRole('heading',{name:'题目校正 · 共1题'})).toBeVisible();await expect(first).toContainText('解释缓存。');
 await page.getByRole('button',{name:'题库练习与作答',exact:true}).click();await expect(page.getByText('未选标签：从当前课程全部已确认题目中随机抽取。',{exact:true})).toBeVisible();await expect(page.getByRole('button',{name:'随机抽取题库练习',exact:true})).toBeEnabled();await expect(page.getByRole('button',{name:'＋ 缓存',exact:true})).toHaveCount(0);
 await page.getByLabel('搜索知识标签',{exact:true}).fill('缓存');await page.getByRole('button',{name:'＋ 缓存',exact:true}).click();await expect(page.getByRole('button',{name:'缓存 ×',exact:true})).toBeVisible();
 // Create an objectively wrong submitted attempt through the same public APIs.
 const choice=await(await request.post(`${base}/courses/${course.id}/question-bank/import`,{headers,data:{title:'错题样例',content:'1. 哪个是缓存？\nA.甲 B.乙 C.丙 D.丁\n答案：A\n知识标签：缓存'}})).json();
 expect((await request.post(`${base}/past-papers/${choice.id}/confirm`,{headers})).ok()).toBeTruthy();
 const paper=await(await request.post(`${base}/courses/${course.id}/question-bank/draw`,{headers,data:{request_id:crypto.randomUUID(),topic_ids:choice.questions[0].bank_data.topic_ids,count:1,question_type:'single_choice'}})).json();
 await request.post(`${base}/exam-papers/${paper.id}/review`,{headers});const attempt=await(await request.post(`${base}/exam-papers/${paper.id}/attempts`,{headers})).json();await request.post(`${base}/attempts/${attempt.id}/submit`,{headers});
 await page.goto('/review');await expect(page.locator('.mistake-card').getByRole('button',{name:'缓存',exact:true})).toBeVisible();
 await page.getByLabel('按知识标签查找错题').fill('缓存');await page.getByRole('button',{name:'＋ 缓存',exact:true}).click();await expect(page.locator('.mistake-card')).toHaveCount(1);
 await page.setViewportSize({width:390,height:900});await page.screenshot({path:'../.artifacts/e2e/topic-ux-review-mobile.png',fullPage:true});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();
});
