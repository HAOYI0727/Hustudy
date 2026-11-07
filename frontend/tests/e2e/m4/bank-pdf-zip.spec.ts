import {test,expect} from '@playwright/test';
import JSZip from 'jszip';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
const base='http://127.0.0.1:8056/api/v1';
async function setup(page:any,request:any){
 const auth=await(await request.post(base+'/auth/register',{data:{username:'pdf_'+crypto.randomUUID().replaceAll('-',''),password:'Test-password-2026'}})).json();
 const headers={Authorization:'Bearer '+auth.access_token};
 const course=await(await request.post(base+'/courses',{headers,data:{name:'PDF与ZIP验收'}})).json();
 await page.addInitScript((a:any)=>{localStorage.setItem('hustudy_token',a.access_token);localStorage.setItem('hustudy_user',a.user.username);},auth);
 await page.goto(`/exam?course=${course.id}`);return {headers,course};
}
test('ZIP文档自动显示，附带图片只入待识别队列',async({page,request})=>{
 const s=await setup(page,request);
 const zip=new JSZip();zip.file('unit/answers.md','# Hustudy 题库 v1\n\n## 题目 1\n### 题型\n解答题\n### 题干\n什么是队头阻塞？\n### 参考答案\n这是原文中的参考解答。\n\n## 题目 2\n### 题型\n解答题\n### 题干\n指出处理顺序。\n### 参考答案\n按FIFO处理。');
 zip.file('unit/figure.png',readFileSync(fileURLToPath(new URL('../../../../fixtures/question_bank_scan_demo.png',import.meta.url))));zip.file('ignored.exe','not executed');
 const buffer=await zip.generateAsync({type:'nodebuffer'});
 await page.getByLabel('上传本地题库（Markdown / ZIP）').setInputFiles({name:'questions.zip',mimeType:'application/zip',buffer});
 await page.getByRole('button',{name:'上传选中文件并开始导入',exact:true}).click();
 await expect(page.getByRole('heading',{name:'题目校正 · 共2题'})).toBeVisible({timeout:30000});
 const first=page.locator('.bank-question-editor').first();await first.getByText('编辑Markdown源码与答案',{exact:true}).click();await expect(first.getByRole('textbox',{name:'题干',exact:true})).toHaveValue('什么是队头阻塞？');
 await expect(first.getByRole('textbox',{name:'参考解答（原文提供，可校正，不用于自动评分）',exact:true})).toHaveValue('这是原文中的参考解答。');
 await expect(page.getByRole('region',{name:'题库插图库'})).toContainText('0 张插图');
 expect(await(await request.get(`${base}/courses/${s.course.id}/question-bank/image-jobs`,{headers:s.headers})).json()).toEqual([]);
 await page.setViewportSize({width:390,height:900});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();
});

test('缺少模型密钥时明确禁用AI选项，本地导入仍可用',async({page,request})=>{
 await setup(page,request);
 await expect(page.getByRole('button',{name:'本地直接上传（Markdown / ZIP）',exact:true})).toHaveClass('primary');
 await expect(page.getByLabel('从已上传资料或题库原件导入（含人工补录）')).toBeHidden();
 await page.getByRole('button',{name:'从资料库导入',exact:true}).click();
 await expect(page.getByLabel('从已上传资料或题库原件导入（含人工补录）')).toBeVisible();
 await expect(page.getByLabel('上传本地题库（Markdown / ZIP）')).toBeHidden();
 await page.getByRole('button',{name:'本地直接上传（Markdown / ZIP）',exact:true}).click();
 await expect(page.getByText(/未配置模型密钥/)).toBeVisible();
 await expect(page.getByLabel('识别方式').locator('option[value="ai"]')).toHaveJSProperty('disabled',true);
 await page.getByLabel('上传本地题库（Markdown / ZIP）').setInputFiles({name:'basic.md',mimeType:'text/markdown',buffer:Buffer.from('# Hustudy 题库 v1\n\n## 题目 1\n### 题型\n解答题\n### 题干\n简述协议。')});
 await page.getByRole('button',{name:'上传选中文件并开始导入',exact:true}).click();
 await expect(page.getByRole('heading',{name:'题目校正 · 共1题'})).toBeVisible({timeout:30000});
});

test('本地直接选择ZIP，内部实际PDF也能自动拆题',async({page,request})=>{
 test.skip(!process.env.HUSTUDY_TEST_BANK_PDF,'Private user PDF requires explicitly supplied path');
 await setup(page,request);
 const zip=new JSZip();zip.file('试卷/6-ans.pdf',readFileSync(process.env.HUSTUDY_TEST_BANK_PDF!));
 await page.getByLabel('上传本地题库（Markdown / ZIP）').setInputFiles({name:'本地题库.zip',mimeType:'application/zip',buffer:await zip.generateAsync({type:'nodebuffer'})});
 await page.getByLabel('试卷/6-ans.pdf',{exact:true}).check();
 await page.getByRole('button',{name:'上传选中文件并开始导入',exact:true}).click();
 await expect(page.getByRole('heading',{name:'题目校正 · 共17题'})).toBeVisible({timeout:30000});
 await expect(page.locator('.bank-import-results')).toContainText('试卷/6-ans.pdf');
 await page.locator('.bank-question-editor').first().getByText('编辑Markdown源码与答案',{exact:true}).click();
 await expect(page.locator('.bank-question-editor').first().getByRole('textbox',{name:'题干',exact:true})).toHaveValue('什么是 HOL 阻塞？它出现在输入端口还是输出端口？');
});

test('用户实际PDF上传后自动拆为17题并立即展开，跨页解答保留',async({page,request})=>{
 test.skip(!process.env.HUSTUDY_TEST_BANK_PDF,'Private user PDF requires explicitly supplied local path');
 await setup(page,request);
 await page.getByLabel('上传本地题库（Markdown / ZIP）').setInputFiles(process.env.HUSTUDY_TEST_BANK_PDF!);
 await page.getByRole('button',{name:'上传选中文件并开始导入',exact:true}).click();
 await expect(page.getByRole('heading',{name:'题目校正 · 共17题'})).toBeVisible({timeout:30000});
 await expect(page.locator('details.bank-question-editor[open]')).toHaveCount(17);
 const first=page.locator('.bank-question-editor').first();await first.getByText('编辑Markdown源码与答案',{exact:true}).click();await expect(first.getByRole('textbox',{name:'题干',exact:true})).toHaveValue('什么是 HOL 阻塞？它出现在输入端口还是输出端口？');
 await expect(first.getByRole('textbox',{name:'参考解答（原文提供，可校正，不用于自动评分）',exact:true})).toHaveValue(/Head-of-Line/);
 const crossing=page.locator('.bank-question-editor').filter({has:page.locator('.bank-question-number').filter({hasText:/^题号 2-8$/})});
 await crossing.getByText('编辑Markdown源码与答案',{exact:true}).click();
 await expect(crossing.getByRole('textbox',{name:'参考解答（原文提供，可校正，不用于自动评分）',exact:true})).toHaveValue(/第 7 个传输轮回/);
 await page.screenshot({path:'../.artifacts/e2e/m4-pdf-zip-actual-desktop.png',fullPage:false});
});
