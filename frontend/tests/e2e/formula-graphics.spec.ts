import {test, expect, type Page, type APIRequestContext} from '@playwright/test';
import {mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';
async function seed(page: Page, request: APIRequestContext) {
  const base = 'http://127.0.0.1:8056/api/v1', username = 'graphics_' + crypto.randomUUID().replaceAll('-', '');
  const auth = await (await request.post(base + '/auth/register', {data: {username, password: 'Test-password-2026'}})).json();
  const headers = {Authorization: 'Bearer ' + auth.access_token};
  const course = await (await request.post(base + '/courses', {headers, data: {name: '图形公式验收'}})).json();
  const note = await (await request.post(base + '/notes', {headers, data: {course_id: course.id, title: '结构输入测试', content: '测试正文'}})).json();
  await page.addInitScript(({token, username}) => {localStorage.setItem('hustudy_token', token); localStorage.setItem('hustudy_user', username);}, {token: auth.access_token, username});
  await page.goto('/notes?course=' + course.id + '&note=' + note.id);
  await expect(page.getByLabel('笔记标题')).toHaveValue(note.title);
}
async function screenshot(page: Page, name: string) {
  if (!process.env.HUSTUDY_M3_EVIDENCE) return;
  await mkdir(resolve('../docs/fzk/evidence'), {recursive: true});
  await page.screenshot({path: resolve('../docs/fzk/evidence/' + name + '.png'), animations: 'disabled'});
}
for (const width of [390, 1440]) test('图形按钮、字段连续输入、嵌套、重新打开与保存 ' + width, async ({page, request}, info) => {
  test.setTimeout(120000);
  await page.setViewportSize({width, height: 1100}); await seed(page, request);
  const editor = page.getByLabel('Markdown 正文'); await editor.fill('');
  const open = page.getByRole('button', {name: '公式编辑器', exact: true}); await open.click();
  const modal = page.getByRole('dialog', {name: '公式编辑器', exact: true}), source = modal.getByLabel('LaTeX 公式', {exact: true});
  await modal.getByRole('button', {name: '快捷结构 分数', exact: true}).click();
  const numerator = modal.getByLabel('填写 分子', {exact: true}), denominator = modal.getByLabel('填写 分母', {exact: true});
  await expect(numerator).toBeFocused(); await numerator.fill('x+1');
  await numerator.press('End');
  await modal.getByRole('button', {name: '快捷符号 正负 ±', exact: true}).click();
  await expect(numerator).toBeFocused(); await expect(numerator).toHaveValue('x+1\\pm ');
  await expect.poll(() => numerator.evaluate((el: HTMLTextAreaElement) => el.selectionStart)).toBe(7);
  await modal.getByRole('button', {name: '快捷符号 阿尔法 α', exact: true}).click();
  await expect(numerator).toHaveValue('x+1\\pm \\alpha ');
  await numerator.press('Tab'); await expect(denominator).toBeFocused(); await denominator.fill('n+1');
  await numerator.focus(); await numerator.press('Control+a');
  await modal.getByRole('button', {name: '快捷结构 根号', exact: true}).click();
  const radicand = modal.getByLabel('填写 被开方数', {exact: true});
  await expect(radicand).toBeFocused();
  await expect(source).toHaveValue(String.raw`\frac{\sqrt{x+1\pm \alpha }}{n+1}`);
  await radicand.fill('a+b');
  await modal.getByRole('button', {name: '撤销公式编辑', exact: true}).click();
  await expect(source).toHaveValue(String.raw`\frac{\sqrt{x+1\pm \alpha }}{n+1}`);
  await modal.getByRole('button', {name: '重做公式编辑', exact: true}).click();
  await expect(source).toHaveValue(String.raw`\frac{\sqrt{a+b}}{n+1}`);
  await modal.getByRole('button', {name: '移到公式末尾 →', exact: true}).click();
  await modal.getByRole('button', {name: '快捷符号 加号 +', exact: true}).click();
  await modal.getByRole('button', {name: '快捷符号 派 π', exact: true}).click();
  await expect(source).toHaveValue(String.raw`\frac{\sqrt{a+b}}{n+1}+\pi `);
  await modal.getByRole('button', {name: '插入公式', exact: true}).click();
  const expected = String.raw`$\frac{\sqrt{a+b}}{n+1}+\pi$`;
  await expect(editor).toHaveValue(expected);
  await editor.press('Control+s'); await expect(page.locator('.save-indicator')).toHaveText('已保存到本地服务');
  await page.reload(); await expect(editor).toHaveValue(expected);
  await editor.evaluate((el: HTMLTextAreaElement) => {el.focus(); el.setSelectionRange(8, 8);});
  await open.click(); await modal.getByRole('button', {name: '填写参数', exact: true}).click();
  await expect(modal.getByLabel('填写 分子', {exact: true})).toHaveValue(String.raw`\sqrt{a+b}`);
  await expect(modal.getByLabel('填写 被开方数', {exact: true})).toHaveValue('a+b');
  await modal.getByLabel('填写 被开方数', {exact: true}).fill('y+2');
  await expect(modal.getByLabel('填写 分子', {exact: true})).toHaveValue(String.raw`\sqrt{y+2}`);
  await expect(modal.getByLabel('填写 分母', {exact: true})).toHaveValue('n+1');
  await modal.getByRole('button', {name: '符号分类 关系', exact: true}).click();
  await modal.getByRole('button', {name: '填写参数', exact: true}).scrollIntoViewIfNeeded();
  await screenshot(page, 'formula-graphics-' + width + '-' + info.project.name);
  await modal.getByRole('button', {name: '更新公式', exact: true}).click();
  await expect(editor).toHaveValue(expected.replace('a+b', 'y+2'));
  await page.getByRole('button', {name: '分屏预览', exact: true}).click();
  await expect(page.getByLabel('笔记实时预览').locator('.katex')).toHaveCount(1);
});

test('图形工具触控五尺寸及不完整结构保护', async ({browser, request}, info) => {
  test.setTimeout(120000);
  const context = await browser.newContext({baseURL: 'http://127.0.0.1:5178', hasTouch: true});
  try {
    const page = await context.newPage(); await seed(page, request);
    const editor = page.getByLabel('Markdown 正文'); await editor.fill('保留正文');
    await page.getByRole('button', {name: '公式编辑器', exact: true}).click();
    const modal = page.getByRole('dialog', {name: '公式编辑器', exact: true}), source = modal.getByLabel('LaTeX 公式', {exact: true});
    await modal.getByRole('button', {name: '快捷结构 分数', exact: true}).click();
    await modal.getByLabel('填写 分子', {exact: true}).fill('\\sqrt{');
    await expect(modal.getByLabel('填写 分子', {exact: true})).toBeFocused();
    await expect(modal.getByRole('button', {name: '插入公式', exact: true})).toBeDisabled();
    await modal.getByLabel('填写 分子', {exact: true}).fill('x+1');
    await expect(modal.getByRole('button', {name: '插入公式', exact: true})).toBeEnabled();
    for (const width of [320,390,820,1024,1440]) {
      await page.setViewportSize({width, height: 1100});
      expect(await modal.evaluate(el => el.scrollWidth <= el.clientWidth + 1), String(width)).toBe(true);
      const sizes = await modal.locator('.formula-graphic').evaluateAll(els => els.map(el => {const r = el.getBoundingClientRect(); return [r.width,r.height];}));
      expect(sizes.every(([w,h]) => w >= 44 && h >= 44), String(width)).toBe(true);
    }
    await source.fill(String.raw`\unknown{\frac{a}{b}}`);
    await modal.getByRole('button', {name: '识别结构', exact: true}).click();
    await expect(source).toHaveValue(String.raw`\unknown{\frac{a}{b}}`);
    await expect(modal.getByRole('button', {name: '插入公式', exact: true})).toBeDisabled();
    await screenshot(page, 'formula-graphics-touch-' + info.project.name);
    await modal.getByRole('button', {name: '取消', exact: true}).click();
    await expect(editor).toHaveValue('保留正文');
  } finally {await context.close();}
});
