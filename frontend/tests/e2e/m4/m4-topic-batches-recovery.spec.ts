import {test,expect} from '@playwright/test';
const base='http://127.0.0.1:8056/api/v1';
test('70题归类跨分页完整预览，失败识别可见恢复入口',async({page,request})=>{
 const auth=await(await request.post(base+'/auth/register',{data:{username:'batch_'+crypto.randomUUID().replaceAll('-',''),password:'Synthetic-password-2026'}})).json();
 const headers={Authorization:'Bearer '+auth.access_token};
 const course=await(await request.post(base+'/courses',{headers,data:{name:'自动分批验收'}})).json();
 const connection=await(await request.get(base+'/api-connection',{headers})).json();
 expect((await request.put(base+'/api-connection',{headers,data:{revision:connection.revision,model:'glm-5.3-flash',key:'synthetic-key-only-for-test'}})).ok()).toBeTruthy();
 const content=Array.from({length:70},(_,i)=>`${i+1}. 完整题目${i+1}。\n答案：不应发送的参考答案`).join('\n');
 const source=await(await request.post(`${base}/courses/${course.id}/question-bank/import`,{headers,data:{title:'70题自动分批',content}})).json();
 await page.addInitScript(a=>{localStorage.setItem('hustudy_token',a.access_token);localStorage.setItem('hustudy_user',a.user.username);},auth);
 await page.goto(`/exam?course=${course.id}`);
 await expect(page.getByRole('heading',{name:'题目校正 · 共70题'})).toBeVisible();
 await expect(page.getByText('每批最多32题',{exact:false})).toHaveCount(0);
 await page.getByRole('button',{name:'AI归类本卷待归类题目',exact:true}).click();
 const preview=page.locator('.bank-topic-ai .bank-ai-consent');
 await expect(preview).toContainText('预计3批调用');
 await expect(preview).toContainText('本批70道题');
 await expect(preview).toContainText('完整题目70');
 await expect(preview).not.toContainText('不应发送的参考答案');
 await preview.getByRole('button',{name:'暂不发送'}).click();
 await page.route('**/question-bank/papers',async route=>{
  const response=await route.fetch();const data=await response.json();
  for(const paper of data)if(paper.id===source.id){paper.question_count=0;paper.recognition={status:'FAILED',error:'同卷题号重复且未标续题，请核对原页',completed_pages:9,total_pages:9,engine:'ai'};}
  await route.fulfill({response,json:data});
 });
 await page.reload();
 await expect(page.getByRole('alert').filter({hasText:'识别未完成'})).toContainText('已保存9/9页');
 await expect(page.getByRole('button',{name:'恢复已识别结果',exact:true})).toBeVisible();
});
