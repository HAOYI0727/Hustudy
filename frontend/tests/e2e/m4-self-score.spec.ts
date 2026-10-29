import {test,expect} from '@playwright/test';
const base='http://127.0.0.1:8056/api/v1';
for(const mixed of [false,true])test(`分值自评及汇总${mixed?'含未知不显示总分':'显示总分'}`,async({page,request})=>{
 const auth=await(await request.post(base+'/auth/register',{data:{username:'score_'+crypto.randomUUID().replaceAll('-',''),password:'Synthetic-password-2026'}})).json(),headers={Authorization:'Bearer '+auth.access_token};
 const course=await(await request.post(base+'/courses',{headers,data:{name:'分数验证'}})).json();
 const source=await(await request.post(`${base}/courses/${course.id}/question-bank/import`,{headers,data:{title:'分数卷',content:`1. 已知分值题。\n分值：10\n2. 另一题。${mixed?'':'\n分值：5'}`}})).json();
 await request.post(`${base}/past-papers/${source.id}/confirm`,{headers});
 const paper=await(await request.post(`${base}/courses/${course.id}/question-bank/papers/${source.id}/practice`,{headers,data:{request_id:crypto.randomUUID(),duration_minutes:30}})).json();
 await request.post(`${base}/exam-papers/${paper.id}/review`,{headers});const attempt=await(await request.post(`${base}/exam-papers/${paper.id}/attempts`,{headers})).json();await request.post(`${base}/attempts/${attempt.id}/submit`,{headers});
 await page.addInitScript(({auth,course,attempt})=>{localStorage.setItem('hustudy_token',auth.access_token);localStorage.setItem('hustudy_user',auth.user.username);localStorage.setItem(`hustudy-bank-attempt:${course.id}`,attempt.id);},{auth,course,attempt});
 await page.goto(`/exam?course=${course.id}`);await page.getByRole('button',{name:'题库练习与作答',exact:true}).click();
 const first=page.locator('.bank-practice .question-card').filter({hasText:'已知分值题。'});await expect(first.getByRole('button',{name:'我答对了',exact:true})).toHaveCount(0);await first.getByLabel('本题得分',{exact:true}).fill('6');await first.getByRole('button',{name:'保存本题得分',exact:true}).click();await expect(first.getByText('本题得分：6 / 10分',{exact:true})).toBeVisible();
 const second=page.locator('.bank-practice .question-card').filter({hasText:'另一题。'});if(mixed)await second.getByRole('button',{name:'我答对了',exact:true}).click();else{await second.getByLabel('本题得分',{exact:true}).fill('3');await second.getByRole('button',{name:'保存本题得分',exact:true}).click();}
 const summary=page.getByRole('region',{name:'练习得分',exact:true});await expect(summary).toContainText(mixed?'练习得分：6分':'练习得分：9分');if(mixed)await expect(summary).not.toContainText('总分');else await expect(summary).toContainText('总分 15分');await expect(summary).not.toContainText('尚有题目待自评');
});
