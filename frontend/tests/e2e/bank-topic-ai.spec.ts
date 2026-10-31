import {test,expect} from '@playwright/test';
const base='http://127.0.0.1:8056/api/v1';
async function setup(page:any,request:any){
 const auth=await(await request.post(base+'/auth/register',{data:{username:'aidx_'+crypto.randomUUID().replaceAll('-',''),password:'Test-password-2026'}})).json();
 const headers={Authorization:'Bearer '+auth.access_token};
 const course=await(await request.post(base+'/courses',{headers,data:{name:'AI知识点验收'}})).json();
 const topic=await(await request.post(`${base}/courses/${course.id}/topics`,{headers,data:{name:'拥塞控制',aliases:[]}})).json();
 await page.addInitScript((a:any)=>{localStorage.setItem('hustudy_token',a.access_token);localStorage.setItem('hustudy_user',a.user.username);},auth);
 return {headers,course,topic};
}
async function upload(page:any,course:any){
 await page.goto(`/exam?course=${course.id}`);
 await page.getByLabel('上传本地题库（Markdown / ZIP）').setInputFiles({name:'semantic.md',mimeType:'text/markdown',buffer:Buffer.from('# Hustudy 题库 v1\n\n## 题目 1\n### 题型\n解答题\n### 题干\n发送方发现丢包时如何调整发送窗口？\n### 参考答案\n这段参考答案不应出现在分类预览里。')});
 await page.getByRole('button',{name:'上传选中文件并开始导入',exact:true}).click();
 await expect(page.getByRole('heading',{name:'题目校正 · 共1题'})).toBeVisible({timeout:30000});
}

test('未配置时提供可见API接入说明，上传不再短语自动分配',async({page,request})=>{
 const s=await setup(page,request);await upload(page,s.course);
 const details=page.locator('.bank-api-setup').first();await expect(details.getByRole('link',{name:'打开左侧“API接入”按图设置 →'})).toHaveAttribute('href','/api-connect');
 await expect(page.getByRole('button',{name:'AI归类本卷待归类题目',exact:true})).toBeDisabled();
 const q=page.locator('.bank-question-editor').first();await expect(q.locator('.bank-topic-match')).toHaveCount(0);
});

// Provider responses are simulated here; backend tests cover worker/persistence.
for(const candidate of [false,true])test(`AI预览确认、轮询与${candidate?'备选创建':'语义高亮选用'}（模拟响应）`,async({page,request})=>{
 const s=await setup(page,request);let state='NONE',qid='',confirmed=0,previewCount=0;
 const common={preview_id:'preview-1',paper_id:'preview',model:'glm-5.3-flash',endpoint:'https://open.bigmodel.cn/api/paas/v4/chat/completions',expires_at:'2099-01-01T00:00:00+00:00'};
 await page.route('**/question-bank/ai-capabilities',r=>r.fulfill({json:{configured:true,model:'glm-5.3-flash'}}));
 await page.route('**/past-papers/*/topic-ai-preview',async r=>{
  if(r.request().method()==='POST'){previewCount++;qid=r.request().postDataJSON().question_ids[0];state='PREVIEW';}
  await r.fulfill({json:{...common,status:state,...(state==='PREVIEW'?{input:{questions:[{question_id:qid,revision:1,stem:'发送方发现丢包时如何调整发送窗口？',options:[]}],topics:[{id:s.topic.id,name:'拥塞控制',aliases:[],revision:1}]}}:{})}});
 });
 await page.route('**/past-papers/*/topic-ai-confirm',async r=>{confirmed++;state='SUCCEEDED';await r.fulfill({status:202,json:{...common,status:'QUEUED'}});});
 await page.route('**/courses/*/question-bank?*',async r=>{
  const response=await r.fetch();const data=await response.json();
  if(state==='SUCCEEDED')for(const q of data.items)q.bank_data.topic_index={selection_reviewed:q.bank_data.topic_index?.selection_reviewed,version:'bank-topic-ai-v3',reason:'丢包后的窗口调整涉及拥塞控制。',existing:candidate?[]:[{topic_id:s.topic.id,name:'拥塞控制',method:'ai',reason:'丢包后的窗口调整涉及拥塞控制。'}],candidates:candidate?['窗口调整策略']:[]};
  await r.fulfill({response,json:data});
 });
 await upload(page,s.course);
 await page.getByRole('button',{name:'AI归类本卷待归类题目',exact:true}).click();
 const consent=page.locator('.bank-topic-ai .bank-ai-consent');await expect(consent).toBeVisible();expect(confirmed).toBe(0);
 await expect(consent).toContainText('发送方发现丢包');await expect(consent).not.toContainText('这段参考答案');
 await consent.getByRole('button',{name:'确认发送并AI归类',exact:true}).click();
 const editor=page.locator('.bank-question-editor').first();
 if(candidate){await editor.getByRole('button',{name:'＋ 窗口调整策略',exact:true}).click();await expect(editor.locator('.bank-topic-option').filter({hasText:'窗口调整策略'}).locator('input')).toBeChecked();}
 else{const first=editor.locator('.bank-topic-option').first();await expect(first).toHaveClass(/bank-topic-match/);await expect(first).toContainText('丢包后的窗口调整');await expect(first.locator('input')).toBeChecked();}
 await editor.getByRole('button',{name:'保存本题校正',exact:true}).click();
 await expect(page.getByText('已保存校正，请核验修改后的题目',{exact:true})).toBeVisible();
 expect(confirmed).toBe(1);expect(previewCount).toBe(1);
 const data=await(await request.get(`${base}/courses/${s.course.id}/question-bank`,{headers:s.headers})).json();expect(data.items[0].bank_data.topic_ids).toHaveLength(1);
 if(!candidate){const checkbox=editor.locator('.bank-topic-option').first().locator('input');await checkbox.uncheck();await editor.getByRole('button',{name:'保存本题校正',exact:true}).click();await expect(checkbox).not.toBeChecked();await page.reload();await expect(page.locator('.bank-question-editor').first().locator('.bank-topic-option input').first()).not.toBeChecked();}
 await page.setViewportSize({width:390,height:900});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();
});
