import {test,expect} from '@playwright/test';
const base='http://127.0.0.1:8056/api/v1';
async function setup(page:any,request:any){
 const auth=await(await request.post(base+'/auth/register',{data:{username:'display_'+crypto.randomUUID().replaceAll('-',''),password:'Test-password-2026'}})).json();
 const headers={Authorization:'Bearer '+auth.access_token};
 const course=await(await request.post(base+'/courses',{headers,data:{name:'展示验收'}})).json();
 await page.addInitScript((a:any)=>{localStorage.setItem('hustudy_token',a.access_token);localStorage.setItem('hustudy_user',a.user.username);},auth);
 return {headers,course};
}

test('混合子题按大题展示且独立判分，提交后直接显示Markdown参考解答，标签控件对齐',async({page,request})=>{
 const {headers,course}=await setup(page,request);
 const root=await(await request.post(`${base}/courses/${course.id}/topics`,{headers,data:{name:'计算机'}})).json();
 const p=await(await request.post(`${base}/courses/${course.id}/question-bank/import`,{headers,data:{title:'原卷',content:'1. 一组独立子问。',default_topic_ids:[root.id]}})).json();
 const parts=['选一项。\nA.甲 B.乙 C.丙 D.丁\n答案：A\n解析：这是选择参考解答。','补全____。\n答案：缓存\n解析：这是填空参考解答。','说明数据。\n答案：公式 $x^2$。\n\n| 名称 | 数值 |\n| --- | --- |\n| x | 2 |\n解析：这是完整解答过程。'];
 const split=await request.post(`${base}/past-questions/${p.questions[0].id}/split`,{headers,data:{revision:p.questions[0].revision,parts}});expect(split.ok()).toBeTruthy();
 expect((await split.json()).map((q:any)=>q.question_type)).toEqual(['single_choice','solution','solution']);
 await page.goto(`/exam?course=${course.id}`);
 await expect(page.locator('.bank-group-heading')).toContainText('第1大题');
 await expect(page.locator('.bank-question-editor .bank-question-number')).toHaveText(['题号 1-1','题号 1-2','题号 1-3']);
 const editor=page.locator('.bank-question-editor').first();if(await editor.getAttribute('open')===null)await editor.locator(':scope > summary').click();
 const parent=editor.getByLabel('新标签的上级',{exact:true});const name=editor.getByLabel('自定义知识点',{exact:true});const create=editor.getByRole('button',{name:'创建并选中',exact:true});
 const boxes=await Promise.all([parent.boundingBox(),name.boundingBox(),create.boundingBox()]);
 expect(Math.max(...boxes.map(b=>b!.y))-Math.min(...boxes.map(b=>b!.y))).toBeLessThan(2);
 expect(Math.max(...boxes.map(b=>b!.height))-Math.min(...boxes.map(b=>b!.height))).toBeLessThan(2);
 await editor.locator('.bank-topic-create').screenshot({path:'local_only/topic-create-aligned.png'});
 await parent.fill('计算机');await editor.getByRole('button',{name:'＋ 计算机',exact:true}).click();
 await expect(parent).toHaveValue('计算机');await expect(editor.locator('.bank-topic-create .bank-topic-search>.tag-list')).toHaveCount(0);
 const second=await(await request.post(`${base}/courses/${course.id}/topics`,{headers,data:{name:'存储系统'}})).json();
 await page.reload();const firstEditor=page.locator('.bank-question-editor').first();if(await firstEditor.getAttribute('open')===null)await firstEditor.locator(':scope > summary').click();
 const parentAgain=firstEditor.getByLabel('新标签的上级',{exact:true});await parentAgain.fill('计算机');await firstEditor.getByRole('button',{name:'＋ 计算机',exact:true}).click();
 await parentAgain.fill(second.name);await firstEditor.getByRole('button',{name:'＋ 存储系统',exact:true}).click();await expect(parentAgain).toHaveValue('存储系统');
 await expect(firstEditor.locator('.bank-topic-create .bank-topic-search>.tag-list')).toHaveCount(0);await firstEditor.getByRole('button',{name:'清除新标签的上级',exact:true}).click();await expect(parentAgain).toHaveValue('');
 await page.setViewportSize({width:390,height:900});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();await page.setViewportSize({width:1440,height:1000});
 expect((await request.post(`${base}/past-papers/${p.id}/confirm`,{headers})).ok()).toBeTruthy();
 await page.getByRole('button',{name:'题库练习与作答',exact:true}).click();await page.getByLabel('题数',{exact:true}).fill('3');await page.getByRole('button',{name:'随机抽取题库练习',exact:true}).click();
 await expect(page.locator('.bank-practice .bank-group-heading')).toContainText('第1大题');
 await expect(page.getByRole('region',{name:'参考答案与解答'})).toHaveCount(0);
 await page.getByRole('button',{name:'已核对题干，确认练习',exact:true}).click();await page.getByRole('button',{name:'开始作答',exact:true}).click();
 const questions=page.locator('.question-card');const choice=questions.filter({hasText:'1-1.'}),blank=questions.filter({hasText:'1-2.'}),written=questions.filter({hasText:'1-3.'});await expect(questions).toHaveCount(3);for(const number of ['1-1.','1-2.','1-3.'])await expect(questions.filter({hasText:number})).toHaveCount(1);await choice.getByRole('button',{name:/甲/}).click();
 await blank.getByLabel('解答内容').fill('缓存');await blank.getByRole('button',{name:'保存本题答案'}).click();
 await written.getByLabel('解答内容').fill('自己的解答');await written.getByRole('button',{name:'保存本题答案'}).click();
 await page.getByRole('button',{name:'交卷并查看答案',exact:true}).click();
 await expect(choice.getByRole('region',{name:'参考答案与解答'})).toContainText('这是选择参考解答');
 await expect(blank.getByRole('region',{name:'参考答案与解答'})).toContainText('这是填空参考解答');
 const solution=written.getByRole('region',{name:'参考答案与解答'});
 await expect(solution.getByRole('table')).toBeVisible();await expect(solution.locator('.katex')).toHaveCount(1);await expect(solution).toContainText('这是完整解答过程');
 await solution.screenshot({path:'local_only/submitted-reference.png'});
 await page.reload();await page.getByRole('button',{name:'题库练习与作答',exact:true}).click();await expect(page.getByRole('table')).toBeVisible();
});

test('恢复页面可见AI正在等待，排队与完成状态区分且始终有核对提醒',async({page,request})=>{
 const {course}=await setup(page,request);let status='RUNNING';
 await page.route('**/question-bank/image-jobs',route=>route.fulfill({json:[{id:'mock-job',paper_id:'mock-paper',title:'模拟AI原页转写',engine:'ai',status,progress:20,asset_ids:[],layout:'single'}]}));
 await page.goto(`/exam?course=${course.id}`);await expect(page.getByText('正在等待AI返回结果',{exact:true}).first()).toBeVisible();
 await expect(page.getByText('AI也会犯错，请仔细甄别',{exact:true}).first()).toBeVisible();
 status='QUEUED';await expect(page.getByText('AI任务已排队',{exact:true}).first()).toBeVisible({timeout:10000});
 status='FAILED';await expect(page.locator('.bank-file-import .ai-waiting')).toHaveCount(0,{timeout:10000});
 await expect(page.locator('.bank-file-import .ai-caution')).toBeVisible();
});

test('只抽一个子问时仍有完整公共题干和表格，不泄露其他子问解答',async({page,request})=>{
 const {headers,course}=await setup(page,request);
 const p=await(await request.post(`${base}/courses/${course.id}/question-bank/import`,{headers,data:{title:'共用题干',content:'1. 已知容量为8KB，请使用表中数据。\n\n| 地址 | 数值 |\n| --- | --- |\n| 0 | 2 |\n答案：父答案禁止泄露'}})).json();
 const r=await request.post(`${base}/past-questions/${p.questions[0].id}/split`,{headers,data:{revision:1,parts:['计算地址。\n答案：子问甲答案保密','解释数据。\n答案：子问乙答案保密']}});expect(r.ok()).toBeTruthy();
 expect((await request.post(`${base}/past-papers/${p.id}/confirm`,{headers})).ok()).toBeTruthy();
 await page.goto(`/exam?course=${course.id}`);await page.getByRole('button',{name:'题库练习与作答',exact:true}).click();await page.getByLabel('题数',{exact:true}).fill('1');await page.getByRole('button',{name:'随机抽取题库练习',exact:true}).click();
 await expect(page.locator('.question-card')).toHaveCount(1);
 const context=page.getByRole('region',{name:'整道题目',exact:true});
 await expect(context).toContainText('8KB');await expect(context.getByRole('table')).toBeVisible();
 await expect(context).toContainText('计算地址');await expect(context).toContainText('解释数据');
 await expect(page.getByRole('button',{name:'查看整道题',exact:true})).toHaveCount(0);
 await page.setViewportSize({width:390,height:900});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();
 await expect(context).toBeVisible();await page.setViewportSize({width:1440,height:1000});
 await expect(page.locator('.bank-practice')).not.toContainText('答案保密');await expect(page.locator('.bank-practice')).not.toContainText('父答案禁止泄露');
 await page.getByRole('button',{name:'已核对题干，确认练习',exact:true}).click();await page.getByRole('button',{name:'开始作答',exact:true}).click();
 await page.getByLabel('解答内容',{exact:true}).fill('自己的回答');await page.getByRole('button',{name:'保存本题答案',exact:true}).click();
 await page.reload();await page.getByRole('button',{name:'题库练习与作答',exact:true}).click();await expect(context).toContainText('8KB');
 await expect(page.locator('.question-card')).toHaveCount(1);
});

test('随机抽取后的新题号从小到大显示，原卷题号不再重排题卡',async({page,request})=>{
 const {headers,course}=await setup(page,request);
 const paper=await(await request.post(`${base}/courses/${course.id}/question-bank/import`,{headers,data:{title:'顺序验收',content:'1. 第一原题。\n2. 第二原题。\n3. 第三原题。'}})).json();
 expect((await request.post(`${base}/past-papers/${paper.id}/confirm`,{headers})).ok()).toBeTruthy();
 await page.route('**/question-bank/draw',async route=>{
  const response=await route.fetch();const body=await response.json();
  body.questions.sort((a:any,b:any)=>b.display_group.order[0]-a.display_group.order[0]);
  await route.fulfill({response,json:body});
 });
 await page.goto(`/exam?course=${course.id}`);await page.getByRole('button',{name:'题库练习与作答',exact:true}).click();await page.getByLabel('题数',{exact:true}).fill('3');await page.getByRole('button',{name:'随机抽取题库练习',exact:true}).click();
 const cards=page.locator('.question-card');await expect(cards.locator(':scope > strong')).toHaveText([/^1\./,/^2\./,/^3\./]);
 await expect(cards.nth(0)).toContainText('第三原题');await expect(cards.nth(1)).toContainText('第二原题');await expect(cards.nth(2)).toContainText('第一原题');
});
