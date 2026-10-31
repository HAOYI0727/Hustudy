import {test,expect} from '@playwright/test';
const base='http://127.0.0.1:8056/api/v1';
test('已完成且无自动判分的解答题可自评，刷新保留且错题只记录一次',async({page,request})=>{
 const auth=await(await request.post(base+'/auth/register',{data:{username:'self_'+crypto.randomUUID().replaceAll('-',''),password:'Test-password-2026'}})).json();const headers={Authorization:'Bearer '+auth.access_token};
 const c=await(await request.post(base+'/courses',{headers,data:{name:'自主判断'}})).json();
 const p=await(await request.post(`${base}/courses/${c.id}/question-bank/import`,{headers,data:{title:'无答案题库',content:'1. 简述缓存。'}})).json();expect((await request.post(`${base}/past-papers/${p.id}/confirm`,{headers})).ok()).toBeTruthy();
 const paper=await(await request.post(`${base}/courses/${c.id}/question-bank/draw`,{headers,data:{request_id:crypto.randomUUID(),count:1,topic_ids:[]}})).json();await request.post(`${base}/exam-papers/${paper.id}/review`,{headers});const a=await(await request.post(`${base}/exam-papers/${paper.id}/attempts`,{headers})).json();await request.put(`${base}/attempts/${a.id}/answers/${paper.questions[0].id}`,{headers,data:{answer:'自己的解答'}});await request.post(`${base}/attempts/${a.id}/submit`,{headers});
 await page.addInitScript(({auth,c,a})=>{localStorage.setItem('hustudy_token',auth.access_token);localStorage.setItem('hustudy_user',auth.user.username);localStorage.setItem(`hustudy-bank-attempt:${c.id}`,a.id);},{auth,c,a});
 await page.goto(`/exam?course=${c.id}`);await page.getByRole('button',{name:'题库练习与作答',exact:true}).click();await expect(page.getByRole('button',{name:'我答错了',exact:true})).toBeVisible();await page.getByRole('button',{name:'我答错了',exact:true}).click();await expect(page.getByText('自评错误',{exact:true})).toBeVisible();await expect(page.getByRole('button',{name:'我答对了',exact:true})).toBeDisabled();
 await page.reload();await page.getByRole('button',{name:'题库练习与作答',exact:true}).click();await expect(page.getByText('自评错误',{exact:true})).toBeVisible();expect(await(await request.get(base+'/mistakes',{headers})).json()).toHaveLength(1);
 await page.setViewportSize({width:390,height:900});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();await page.screenshot({path:'local_only/self-review-mobile.png',fullPage:true});
});


test('缺标准答案的选择题和含空位解答题可核验练习并人工判断',async({page,request})=>{
 const auth=await(await request.post(base+'/auth/register',{data:{username:'unknown_'+crypto.randomUUID().replaceAll('-',''),password:'Test-password-2026'}})).json();const headers={Authorization:'Bearer '+auth.access_token};const c=await(await request.post(base+'/courses',{headers,data:{name:'无标准答案'}})).json();
 await request.post(`${base}/courses/${c.id}/question-bank/import`,{headers,data:{title:'只有题目',content:'1. 选一项。\nA.甲 B.乙 C.丙 D.丁\n2. 补全____。'}});
 await page.addInitScript(a=>{localStorage.setItem('hustudy_token',a.access_token);localStorage.setItem('hustudy_user',a.user.username);},auth);await page.goto(`/exam?course=${c.id}`);
 const fill=page.locator('.bank-question-editor').nth(1);if(await fill.getAttribute('open')===null)await fill.locator(':scope > summary').click();await fill.getByText('编辑Markdown源码与答案',{exact:true}).click();await expect(fill.getByLabel('题型',{exact:true})).toHaveValue('solution');await fill.getByRole('button',{name:'保存本题校正',exact:true}).click();await expect(page.getByText('已保存校正，请核验修改后的题目',{exact:true})).toBeVisible();
 await page.getByLabel('全选本页').check();await page.getByRole('button',{name:'核验所选（2）',exact:true}).click();await expect(page.locator('.bank-paper-review .bank-badge')).toHaveText('已确认');await page.getByRole('button',{name:'题库练习与作答',exact:true}).click();await page.getByLabel('题数',{exact:true}).fill('2');await page.getByRole('button',{name:'随机抽取题库练习',exact:true}).click();await page.getByRole('button',{name:'已核对题干，确认练习'}).click();await page.getByRole('button',{name:'开始作答',exact:true}).click();
 await page.getByLabel('解答内容').fill('我的答案');await page.getByRole('button',{name:'保存本题答案'}).click();await page.locator('.option').first().click();await page.getByRole('button',{name:'交卷并查看答案'}).click();await expect(page.getByRole('button',{name:'我答对了',exact:true})).toHaveCount(2);
 await page.getByRole('button',{name:'我答错了',exact:true}).first().click();await page.getByRole('button',{name:'我答对了',exact:true}).last().click();expect(await(await request.get(base+'/mistakes',{headers})).json()).toHaveLength(1);
});
