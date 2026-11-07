import {readFileSync} from "node:fs";
import {fileURLToPath} from "node:url";
import {test,expect} from '@playwright/test';
import JSZip from 'jszip';
const base='http://127.0.0.1:8056/api/v1';
async function setup(page:any,request:any){const a=await(await request.post(base+'/auth/register',{data:{username:'selection_'+crypto.randomUUID().replaceAll('-',''),password:'Test-password-2026'}})).json();const headers={Authorization:'Bearer '+a.access_token};const c=await(await request.post(base+'/courses',{headers,data:{name:'上传筛选与公式'}})).json();await page.addInitScript((a:any)=>{localStorage.setItem('hustudy_token',a.access_token);localStorage.setItem('hustudy_user',a.user.username);},a);await page.goto(`/exam?course=${c.id}`);return {c,headers};}

test('ZIP不按答案文件名排除内容，可自主取消成员或删除单项，上传前没有文件入库',async({page,request})=>{
 const {c,headers}=await setup(page,request);const z=new JSZip();const strict=(stem:string)=>`# Hustudy 题库 v1\n\n## 题目 1\n### 题型\n解答题\n### 题干\n${stem}`;z.file('2021-试卷.md',strict('求 $D_8\\oplus D_7$。'));z.file('2021-答案.md',strict('不应上传'));z.file('2022-试卷.md',strict('第二年试题。'));
 await page.getByLabel('上传本地题库（Markdown / ZIP）').setInputFiles({name:'计算机组成.zip',mimeType:'application/zip',buffer:await z.generateAsync({type:'nodebuffer'})});
 const queue=page.getByRole('region',{name:'待上传文件'});await expect(queue.getByLabel('2021-答案.md')).toBeChecked();await queue.getByLabel('2021-答案.md').uncheck();await expect(queue.getByLabel('2021-试卷.md')).toBeChecked();
 expect(await(await request.get(`${base}/courses/${c.id}/question-bank/files`,{headers})).json()).toEqual([]);
 await queue.locator('.bank-actions').filter({hasText:'2022-试卷.md'}).getByRole('button',{name:'删除此项',exact:true}).click();
 await queue.getByRole('button',{name:'上传选中文件并开始导入',exact:true}).click();await expect(page.getByRole('heading',{name:'题目校正 · 共1题'})).toBeVisible({timeout:30000});
 const files=await(await request.get(`${base}/courses/${c.id}/question-bank/files`,{headers})).json();expect(files).toHaveLength(1);expect(files[0].original_filename).toBe('2021-试卷.md');
 await expect(page.locator('.bank-question-editor .katex')).toBeVisible();await page.getByText('编辑Markdown源码与答案',{exact:true}).click();await expect(page.getByRole('textbox',{name:'题干',exact:true})).toHaveValue(/D_8/);await page.getByText('编辑Markdown源码与答案',{exact:true}).click();
 await page.setViewportSize({width:390,height:900});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();
 await page.locator('.bank-question-editor .bank-math').first().scrollIntoViewIfNeeded();
 await page.screenshot({path:'../.artifacts/e2e/m4-vision-formula-mobile.png',fullPage:false});
});

test('多文件上传可先删除单个文件，也可删除勾选的整批',async({page,request})=>{
 await setup(page,request);const strict=(stem:string)=>`# Hustudy 题库 v1\n\n## 题目 1\n### 题型\n解答题\n### 题干\n${stem}`;await page.getByLabel('上传本地题库（Markdown / ZIP）').setInputFiles([{name:'keep.md',mimeType:'text/markdown',buffer:Buffer.from(strict('保留题。'))},{name:'remove.md',mimeType:'text/markdown',buffer:Buffer.from(strict('删除题。'))}]);
 const queue=page.getByRole('region',{name:'待上传文件'});await queue.locator('.bank-job').filter({hasText:'remove.md'}).getByRole('button',{name:'删除文件',exact:true}).click();await expect(queue).not.toContainText('remove.md');await queue.getByRole('button',{name:'删除选中文件',exact:true}).click();await expect(queue).toHaveCount(0);
});

test('扫描PDF明确确认后才发送AI任务，默认自动判断答案与知识点归类',async({page,request})=>{
 await page.route('**/question-bank/ai-capabilities',r=>r.fulfill({json:{configured:true,vision_configured:true,model:'glm-5.3-flash'}}));
 const {c}=await setup(page,request);const seen:any[]=[];await page.getByLabel('识别方式',{exact:true}).selectOption('ai');
 await page.route('**/question-bank/pdf/*/ocr',r=>{seen.push(r.request().postDataJSON());return r.fulfill({json:{paper_id:crypto.randomUUID(),id:crypto.randomUUID(),status:'QUEUED',progress:0,asset_ids:[],layout:'single'}});});
 await page.getByLabel('上传题库文件（PDF/ZIP/PPTX/DOCX/Markdown）').setInputFiles({name:'公式试卷.pdf',mimeType:'application/pdf',buffer:readFileSync(fileURLToPath(new URL('../../../../fixtures/question_bank_scan_demo.pdf',import.meta.url)))});
 await page.getByRole('button',{name:'上传选中文件并开始导入',exact:true}).click();
 const button=page.getByRole('button',{name:/^AI转写原页与公式/});await expect(button).toBeVisible({timeout:30000});expect(seen).toEqual([]);
 page.once('dialog',d=>d.dismiss());await button.click();expect(seen).toEqual([]);
 page.once('dialog',async d=>{expect(d.message()).toContain('glm-5.3-flash');await d.accept();});await button.click();await expect.poll(()=>seen.length).toBe(1);expect(seen[0]).toMatchObject({engine:'ai',confirm_remote_send:true,questions_only:false,classify_topics:true});
});
