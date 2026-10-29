import {test,expect} from '@playwright/test';
const base='http://127.0.0.1:8056/api/v1';
async function setup(page:any,request:any){
 const auth=await(await request.post(base+'/auth/register',{data:{username:'bulk_'+crypto.randomUUID().replaceAll('-',''),password:'Synthetic-password-2026'}})).json();
 const headers={Authorization:'Bearer '+auth.access_token};
 const course=await(await request.post(base+'/courses',{headers,data:{name:'批量编辑隔离验证'}})).json();
 await page.addInitScript(a=>{localStorage.setItem('hustudy_token',a.access_token);localStorage.setItem('hustudy_user',a.user.username);},auth);
 return {headers,course};
}
test('跨题库全选批量归类，成功移除，失败保留（模拟模型）',async({page,request})=>{
 const {headers,course}=await setup(page,request);
 const papers=[];for(const title of ['成功题库','失败题库'])papers.push(await(await request.post(`${base}/courses/${course.id}/question-bank/import`,{headers,data:{title,content:`1. ${title}题一。\n2. ${title}题二。`}})).json());
 const topic=await(await request.post(`${base}/courses/${course.id}/topics`,{headers,data:{name:'测试标签'}})).json();
 await page.route('**/question-bank/ai-capabilities',r=>r.fulfill({json:{configured:true,model:'deepseek-flash',vendor:'deepseek',endpoint:'https://api.deepseek.com/chat/completions'}}));
 const completed=new Set<string>(),submitted:string[]=[];
 await page.route('**/past-papers/*/auto-classify',async r=>{const paper=papers.find(p=>r.request().url().includes(p.id))!;const data=r.request().postDataJSON();expect(data.confirm_remote_send).toBe(true);expect(Object.keys(data.revisions).sort()).toEqual(paper.questions.map((q:any)=>q.id).sort());submitted.push(paper.id);await r.fulfill({status:202,json:{paper_id:paper.id,preview_id:paper.id,status:'QUEUED',model:'deepseek-flash'}});});
 await page.route('**/past-papers/*/topic-ai-preview',r=>{const paper=papers.find(p=>r.request().url().includes(p.id));if(!paper||!submitted.includes(paper.id))return r.fulfill({json:{paper_id:paper?.id,status:'NONE',model:'deepseek-flash'}});const success=paper.title==='成功题库';if(success)completed.add(paper.id);return r.fulfill({json:{paper_id:paper.id,preview_id:paper.id,status:success?'SUCCEEDED':'FAILED',error:success?null:'模拟无法判断',model:'deepseek-flash'}});});
 await page.route('**/question-directory?*',async r=>{const response=await r.fetch(),data=await response.json();for(const q of data.items)if(completed.has(q.paper_id)){q.bank_data.topic_ids=[topic.id];q.topic_id=topic.id;q.revision++;}await r.fulfill({response,json:data});});
 await page.goto(`/exam?course=${course.id}`);await page.getByRole('button',{name:'考点、统计与蓝图',exact:true}).click();await page.getByRole('button',{name:/未归类/}).click();
 await page.getByRole('button',{name:'全选全部未归类（4）',exact:true}).click();await page.getByRole('button',{name:'批量AI自动归类（4）',exact:true}).click();
 await expect(page.getByText('批量归类完成：成功2题，失败2题；模拟无法判断',{exact:true})).toBeVisible({timeout:20000});
 await expect(page.locator('.bank-directory-question')).toHaveCount(2);expect(submitted).toHaveLength(2);
});
test('仅录入页编辑原题年份分值，考点页保留矩阵蓝图搜索',async({page,request})=>{
 const {headers,course}=await setup(page,request);
 const paper=await(await request.post(`${base}/courses/${course.id}/question-bank/import`,{headers,data:{title:'全部原题',year:2022,content:'1. 重复题目。\n分值：5\n知识标签：网络\n2. 重复题目。\n分值：5\n知识标签：网络\n3. 存储题目。\n知识标签：存储'}})).json();
 await request.post(`${base}/past-papers/${paper.id}/confirm`,{headers});await request.post(`${base}/courses/${course.id}/exam-analyses`,{headers});
 await page.goto(`/exam?course=${course.id}`);
 await expect(page.locator('.bank-question-editor')).toHaveCount(3);
 const form=page.locator('.bank-question-editor').first();await form.getByText('编辑Markdown源码与答案',{exact:true}).click();await form.getByLabel('题目年份',{exact:true}).fill('2025');await form.getByLabel('原题分值（未知留空，不自动分摊父题分值）',{exact:true}).fill('12');
 const savedRequest=page.waitForResponse(r=>r.url().endsWith(`/past-questions/${paper.questions[0].id}`)&&r.request().method()==='PATCH');
 await form.getByRole('button',{name:'保存本题校正',exact:true}).click();expect((await savedRequest).status()).toBe(200);
 await expect(page.getByText('已保存校正，请核验修改后的题目',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'考点、统计与蓝图',exact:true}).click();
 await expect(page.getByRole('button',{name:'展开全部题目编辑',exact:true})).toHaveCount(0);
 const saved=await(await request.get(`${base}/past-questions/${paper.questions[0].id}`,{headers})).json();expect(saved.bank_data.year).toBe(2025);expect(saved.points).toBe(12);
 const other=await(await request.get(`${base}/past-questions/${paper.questions[1].id}`,{headers})).json();expect(other.bank_data.year).toBeUndefined();expect(other.points).toBe(5);
 await page.getByText('资料 / 笔记 / 练习矩阵',{exact:true}).click();const matrix=page.locator('details').filter({has:page.locator('summary',{hasText:'资料 / 笔记 / 练习矩阵'})});await expect(matrix.locator('article')).toHaveCount(0);await page.getByLabel('搜索矩阵标签',{exact:true}).fill('网络');await expect(matrix.locator('article')).toHaveCount(1);await expect(matrix.locator('article strong')).toHaveText('网络');await page.getByLabel('搜索矩阵标签',{exact:true}).fill('不存在');await expect(matrix.locator('article')).toHaveCount(0);
 await page.getByText('题库蓝图：明确题型、分值和标签数量',{exact:true}).click();await expect(page.getByLabel('网络题数',{exact:true})).toHaveCount(0);await page.getByLabel('搜索蓝图标签',{exact:true}).fill('网络');await page.getByLabel('网络题数',{exact:true}).fill('2');await page.getByLabel('搜索蓝图标签',{exact:true}).fill('存储');await expect(page.getByLabel('网络题数',{exact:true})).toHaveCount(0);await expect(page.getByRole('button',{name:'网络：2题 × 清除',exact:true})).toBeVisible();await page.getByLabel('搜索蓝图标签',{exact:true}).fill('网络');await expect(page.getByLabel('网络题数',{exact:true})).toHaveValue('2');
});

test('录入页批量设置年份分值，仅影响勾选题目并支持未知',async({page,request})=>{
 const {headers,course}=await setup(page,request);
 const paper=await(await request.post(`${base}/courses/${course.id}/question-bank/import`,{headers,data:{title:'批量数值测试',year:2022,content:'1. 一题。\n分值：5\n2. 二题。\n分值：6\n3. 三题。\n分值：7'}})).json();
 await page.goto(`/exam?course=${course.id}`);
 await page.getByLabel('选择题号 1',{exact:true}).check();await page.getByLabel('选择题号 2',{exact:true}).check();
 const form=page.getByRole('form',{name:'批量设置年份和分值',exact:true});
 await form.getByLabel('批量年份操作',{exact:true}).selectOption('set');await form.getByLabel('批量题目年份',{exact:true}).fill('2025');
 await form.getByLabel('批量分值操作',{exact:true}).selectOption('set');await form.getByLabel('批量每题分值',{exact:true}).fill('12');
 const save=page.waitForResponse(r=>r.url().endsWith('/batch-values')&&r.request().method()==='POST');await form.getByRole('button',{name:'应用年份和分值到所选（2）',exact:true}).click();expect((await save).status()).toBe(200);
 await expect(page.getByText('已批量更新2题的年份或分值，请重新核验修改后的题目',{exact:true})).toBeVisible();
 for(const q of paper.questions.slice(0,2)){const saved=await(await request.get(`${base}/past-questions/${q.id}`,{headers})).json();expect(saved.bank_data.year).toBe(2025);expect(saved.points).toBe(12);}
 const other=await(await request.get(`${base}/past-questions/${paper.questions[2].id}`,{headers})).json();expect(other.bank_data.year).toBeUndefined();expect(other.points).toBe(7);
 await form.getByLabel('批量年份操作',{exact:true}).selectOption('keep');await form.getByLabel('批量分值操作',{exact:true}).selectOption('unknown');
 const clear=page.waitForResponse(r=>r.url().endsWith('/batch-values')&&r.request().method()==='POST');await form.getByRole('button',{name:'应用年份和分值到所选（2）',exact:true}).click();expect((await clear).status()).toBe(200);
 const cleared=await(await request.get(`${base}/past-questions/${paper.questions[0].id}`,{headers})).json();expect(cleared.points).toBeNull();expect(cleared.bank_data.year).toBe(2025);
});
