import {test,expect} from '@playwright/test';
import {readFileSync,existsSync} from 'node:fs';
import {resolve} from 'node:path';
import JSZip from 'jszip';
const base='http://127.0.0.1:8056/api/v1';
const markdown=String.raw`# Hustudy 题库 v1

## 题目 1-1
### 题型
解答题
### 公共条件
已知 $x=2$，请保留公共条件。
### 题干
根据下表解释计算过程。

| 参数 | 数值 |
| --- | --- |
| 输入 | $x$ |

### 参考答案
$$
\frac{x^2}{2}=2
$$
### 知识标签
综合

## 题目 1-2
### 题型
选择题
### 题干
选择数值。
### 选项
A. $1$
B. $2$
C. $3$
D. $4$
### 参考答案
B
### 知识标签
综合
`;
async function setup(page:any,request:any){
 const auth=await(await request.post(base+'/auth/register',{data:{username:'strict_'+crypto.randomUUID().replaceAll('-',''),password:'Test-password-2026'}})).json();
 const headers={Authorization:'Bearer '+auth.access_token};
 const course=await(await request.post(base+'/courses',{headers,data:{name:'M4严格格式验收'}})).json();
 await page.addInitScript((a:any)=>{localStorage.setItem('hustudy_token',a.access_token);localStorage.setItem('hustudy_user',a.user.username);},auth);
 await page.goto(`/exam?course=${course.id}`);return {auth,headers,course};
}
test('本地限制与严格公式表格ZIP导入、批量身份确认撤销',async({page,request})=>{
 const s=await setup(page,request);
 const input=page.getByLabel('上传本地题库（Markdown / ZIP）');
 await expect(input).toHaveAttribute('accept','.md,.markdown,.zip');
 await input.setInputFiles({name:'rejected.pdf',mimeType:'application/pdf',buffer:Buffer.from('not sent')});
 await expect(page.getByText('本地只接受Markdown或ZIP，其他格式请使用AI识别',{exact:false}).first()).toBeVisible();
 const zip=new JSZip();zip.file('第一份.md',markdown);zip.file('第二份.md',markdown.replace('选择数值。','选择正确数值。'));zip.file('skip.pdf','not uploaded');
 await input.setInputFiles({name:'strict.zip',mimeType:'application/zip',buffer:await zip.generateAsync({type:'nodebuffer'})});
 await page.getByRole('button',{name:'上传选中文件并开始导入',exact:true}).click();
 await expect(page.getByRole('heading',{name:'题目校正 · 共2题'})).toBeVisible({timeout:30000});
 const section=page.getByRole('region',{name:'真题身份批量审核'});
 await expect(section.getByLabel(/选择身份审核/)).toHaveCount(2);
 await page.getByLabel('全选本页',{exact:true}).check();
 page.once('dialog',d=>d.accept());
 await page.getByRole('button',{name:'批量确认所选知识标签关联'}).click();
 await expect(page.getByText('所选题目的知识标签关联已批量确认',{exact:true})).toBeVisible();
 await section.getByRole('button',{name:'选择全部题库（最多100份）'}).click();
 await section.getByLabel('所选题库的共同来源说明').fill('自制来源声明，仅用于自动验证');
 await section.getByRole('button',{name:'批量保存来源说明'}).click();
 await expect(section.getByLabel('所选题库的共同来源说明')).toHaveValue('');
 page.once('dialog',d=>d.accept());
 await section.getByRole('button',{name:'批量确认历年真题身份'}).click();
 await expect(section.getByText(/本人已确认真题/)).toHaveCount(2);
 await section.getByRole('button',{name:'批量撤销真题身份'}).click();
 await expect(section.getByText(/真题身份未确认/)).toHaveCount(2);
 const rows=await(await request.get(`${base}/courses/${s.course.id}/question-bank/papers`,{headers:s.headers})).json();
 expect(rows.every((p:any)=>p.metadata.exam_identity.confirmed===false)).toBeTruthy();
 expect((await(await request.get(`${base}/courses/${s.course.id}/question-bank/files`,{headers:s.headers})).json()).length).toBe(2);
});
test('AI入口保留多格式，PDF上传仅准备预览、不自动发送',async({page,request})=>{
 const s=await setup(page,request);
 const current=await(await request.get(base+'/api-connection',{headers:s.headers})).json();
 expect((await request.put(base+'/api-connection',{headers:s.headers,data:{revision:current.revision,model:'glm-5.3-flash',key:'synthetic-test-key-never-real'}})).ok()).toBeTruthy();
 await page.reload();
 await page.getByLabel('识别方式',{exact:true}).selectOption('ai');
 const input=page.getByLabel('上传题库文件（PDF/ZIP/PPTX/DOCX/Markdown）');
 await expect(input).toHaveAttribute('accept','.pdf,.zip,.pptx,.docx,.md,.markdown,.txt');
 await input.setInputFiles(resolve('../fixtures/preview_demo.pdf'));
 await page.getByRole('button',{name:'上传选中文件并开始导入',exact:true}).click();
 await expect(page.getByRole('button',{name:'确认发送并识别题目',exact:true})).toBeVisible({timeout:30000});
 const jobs=await(await request.get(`${base}/courses/${s.course.id}/question-bank/ai-jobs`,{headers:s.headers})).json();
 expect(jobs).toHaveLength(1);expect(jobs[0].status).toBe('PREVIEW');
});
for(const width of [1440,390])test(`严格Markdown公式表格在审核、作答与答案中保持 ${width}`,async({page,request})=>{
 await page.setViewportSize({width,height:1000});const s=await setup(page,request);
 await page.getByLabel('上传本地题库（Markdown / ZIP）').setInputFiles({name:'公式表格.md',mimeType:'text/markdown',buffer:Buffer.from(markdown)});
 await page.getByRole('button',{name:'上传选中文件并开始导入',exact:true}).click();
 await expect(page.getByRole('heading',{name:'题目校正 · 共2题'})).toBeVisible({timeout:30000});
 const editor=page.locator('.bank-question-editor').first();
 await expect(editor.locator('table').first()).toBeVisible();
 await expect(editor.locator('.katex').first()).toBeVisible();
 await expect(editor.locator('.katex-error')).toHaveCount(0);
 await page.getByRole('button',{name:'确认题库「公式表格.md」',exact:true}).click();
 await expect(page.getByText('本份题库已确认，可按标签抽题',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'题库练习与作答',exact:true}).click();
 await page.evaluate(()=>{const original=Storage.prototype.setItem;Storage.prototype.setItem=function(key,value){if(key.startsWith('hustudy-bank-'))throw new DOMException('blocked','SecurityError');return original.call(this,key,value);};});
 await page.getByLabel('题数',{exact:true}).fill('2');
 await page.getByRole('button',{name:'随机抽取题库练习',exact:true}).click();
 await page.getByRole('button',{name:'已核对题干，确认练习'}).click();
 await page.getByRole('button',{name:'开始作答',exact:true}).click();
 const q=page.locator('.bank-practice .question-card').filter({has:page.locator(':scope > strong').filter({hasText:'解答题'})});
 await expect(q.locator('.bank-math table').first()).toBeVisible();
 await expect(q.locator('.bank-math .katex').first()).toBeVisible();
 await q.getByLabel('解答内容').fill('计算并核对');await q.getByRole('button',{name:'保存本题答案'}).click();
 await page.getByRole('button',{name:'交卷并查看答案'}).click();
 const answer=q.getByRole('region',{name:'参考答案与解答'});
 await expect(answer.locator('.katex-display')).toBeVisible();
 await expect(page.locator('.katex-error')).toHaveCount(0);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();
 await page.screenshot({path:resolve(`../local/m4-formula-${width}.png`),fullPage:true});
});
test('ans6私人Markdown与ZIP分别录入17题且保留跨页解答',async({page,request})=>{
 const path=resolve('../local/ans6-严格题库.md');test.skip(!existsSync(path),'Private generated sample stays local');
 const s=await setup(page,request);
 await page.getByLabel('上传本地题库（Markdown / ZIP）').setInputFiles(path);
 await page.getByRole('button',{name:'上传选中文件并开始导入',exact:true}).click();
 await expect(page.getByRole('heading',{name:'题目校正 · 共17题'})).toBeVisible({timeout:30000});
 const rows=await(await request.get(`${base}/courses/${s.course.id}/question-bank`,{headers:s.headers})).json();
 expect(rows.total).toBe(17);expect(rows.items.find((q:any)=>q.number==='2-8').answer).toContain('第 7 个传输轮回');
 const bytes=readFileSync(resolve('../local/ans6-严格题库.zip'));
 const uploaded=await request.post(`${base}/courses/${s.course.id}/question-bank/archives`,{headers:s.headers,multipart:{file:{name:'ans6.zip',mimeType:'application/zip',buffer:bytes}}});
 expect(uploaded.status()).toBe(201);
});
