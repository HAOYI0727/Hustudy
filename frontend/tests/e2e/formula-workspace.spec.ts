import {test, expect, type Page, type APIRequestContext} from '@playwright/test';
import {mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';
async function seed(page: Page, request: APIRequestContext) {
  const base = 'http://127.0.0.1:8056/api/v1', username = 'formula_' + crypto.randomUUID().replaceAll('-', '');
  const auth = await (await request.post(base + '/auth/register', {data: {username, password: 'Test-password-2026'}})).json();
  const headers = {Authorization: 'Bearer ' + auth.access_token};
  const course = await (await request.post(base + '/courses', {headers, data: {name: '公式工作区验收'}})).json();
  const note = await (await request.post(base + '/notes', {headers, data: {course_id: course.id, title: '公式组合测试', content: '测试正文'}})).json();
  await page.addInitScript(({token, username}) => {localStorage.setItem('hustudy_token', token); localStorage.setItem('hustudy_user', username);}, {token: auth.access_token, username});
  await page.goto('/notes?course=' + course.id + '&note=' + note.id);
  await expect(page.getByLabel('笔记标题')).toHaveValue(note.title);
}
async function screenshot(page: Page, name: string) {
  if (!process.env.HUSTUDY_M3_EVIDENCE) return;
  await mkdir(resolve('../docs/fzk/evidence'), {recursive: true});
  await page.screenshot({path: resolve('../docs/fzk/evidence/' + name + '.png'), animations: 'disabled'});
}
for (const width of [390, 1440]) test('完整公式工作区：嵌套参数、分类搜索、矩阵、速查与保存 ' + width, async ({page, request}, info) => {
  test.setTimeout(120000);
  await page.setViewportSize({width, height: 1100});
  await seed(page, request);
  const editor = page.getByLabel('Markdown 正文'); await editor.fill('');
  await page.getByRole('button', {name: '公式编辑器', exact: true}).click();
  const modal = page.getByRole('dialog', {name: '公式编辑器', exact: true}), source = modal.getByLabel('LaTeX 公式', {exact: true});
  await modal.getByRole('button', {name: '插入分数模板', exact: true}).click();
  await expect(source).toHaveValue(String.raw`\frac{a}{b}`);
  await source.pressSequentially('x+1');
  await modal.getByRole('button', {name: '编辑参数 分子', exact: true}).click();
  await modal.getByRole('button', {name: '插入根号模板', exact: true}).click();
  await expect(source).toHaveValue(String.raw`\frac{\sqrt{x+1}}{b}`);
  await modal.getByRole('button', {name: '编辑参数 分母', exact: true}).click();
  await source.pressSequentially('n+1');
  await expect(source).toHaveValue(String.raw`\frac{\sqrt{x+1}}{n+1}`);
  await modal.getByRole('button', {name: '撤销公式编辑', exact: true}).click();
  await expect(source).toHaveValue(String.raw`\frac{\sqrt{x+1}}{n+}`);
  await source.press('Control+Shift+z');
  await expect(source).toHaveValue(String.raw`\frac{\sqrt{x+1}}{n+1}`);
  await modal.getByRole('button', {name: '编辑参数 被开方数', exact: true}).click();
  await source.press('Alt+ArrowDown');
  expect(await source.evaluate((el: HTMLTextAreaElement) => el.value.slice(el.selectionStart, el.selectionEnd))).toBe('n+1');
  await modal.getByLabel('公式分类', {exact: true}).selectOption('greek');
  await modal.getByLabel('搜索公式符号与模板').fill('偏导数');
  await expect(modal.getByRole('button', {name: '插入偏导数模板', exact: true})).toBeVisible();
  await modal.getByLabel('搜索公式符号与模板').fill('');
  await modal.getByLabel('公式分类', {exact: true}).selectOption('calculus');
  await source.scrollIntoViewIfNeeded();
  await screenshot(page, 'formula-workspace-' + width + '-' + info.project.name);
  await modal.getByRole('button', {name: '插入公式', exact: true}).click();
  await expect(editor).toHaveValue(String.raw`$\frac{\sqrt{x+1}}{n+1}$`);
  await editor.evaluate((el: HTMLTextAreaElement) => {el.focus(); el.setSelectionRange(el.value.length, el.value.length);});
  await page.getByRole('button', {name: '公式编辑器', exact: true}).click();
  await modal.getByRole('button', {name: '矩阵 / 多行', exact: true}).click();
  await modal.getByLabel('公式表格结构').selectOption('array');
  await modal.getByLabel('公式表格行数').selectOption('3');
  await modal.getByLabel('公式表格列数').selectOption('3');
  await modal.getByLabel('公式列对齐').fill('cc|r');
  await modal.getByLabel('第1行第1列').fill(String.raw`\frac{1}{2}`);
  await modal.getByLabel('第3行第3列').fill('x&y');
  await expect(modal.getByRole('button', {name: '将结构插入公式'})).toBeDisabled();
  await modal.getByLabel('第3行第3列').fill('7');
  await modal.getByLabel('公式表格行数').selectOption('2');
  await modal.getByLabel('公式表格行数').selectOption('3');
  await expect(modal.getByLabel('第3行第3列')).toHaveValue('7');
  await modal.getByRole('button', {name: '将结构插入公式'}).click();
  const array = '\\begin{array}{cc|r}\n\\frac{1}{2} & 0 & {} \\\\\n0 & 1 & {} \\\\\n{} & {} & 7\n\\end{array}';
  await expect(source).toHaveValue(array);
  await expect(modal.getByRole('button', {name: /^独立公式/})).toHaveAttribute('aria-pressed', 'true');
  await expect(modal.locator('.formula-preview .katex')).toHaveCount(1);
  await source.scrollIntoViewIfNeeded();
  await screenshot(page, 'formula-grid-' + width + '-' + info.project.name);
  await modal.getByRole('button', {name: '插入公式', exact: true}).click();
  const expected = '$\\frac{\\sqrt{x+1}}{n+1}$\n\n$$\n' + array + '\n$$';
  await expect(editor).toHaveValue(expected);
  await page.getByRole('button', {name: '分屏预览', exact: true}).click();
  await expect(page.getByLabel('笔记实时预览').locator('.katex')).toHaveCount(2);
  await editor.press('Control+s'); await expect(page.locator('.save-indicator')).toHaveText('已保存到本地服务');
  await page.reload(); await expect(editor).toHaveValue(expected);
  await page.getByRole('button', {name: '公式编辑器', exact: true}).click();
  await modal.getByRole('button', {name: '语法速查', exact: true}).click();
  await modal.locator('summary').filter({hasText: '多行、分段与增广矩阵'}).click();
  await expect(modal.locator('.formula-guide details[open]')).toContainText('aligned');
  await page.keyboard.press('Escape');
  await expect(editor).toHaveValue(expected);
});

test('表格与分类工具触屏五尺寸不溢出，参数修改只在确认后生效', async ({browser, request}) => {
  test.setTimeout(120000);
  const context = await browser.newContext({baseURL: 'http://127.0.0.1:5178', hasTouch: true});
  try {
    const page = await context.newPage(); await seed(page, request);
    const editor = page.getByLabel('Markdown 正文'); await editor.fill('保留正文');
    await page.getByRole('button', {name: '公式编辑器', exact: true}).click();
    const modal = page.getByRole('dialog', {name: '公式编辑器', exact: true});
    await modal.getByRole('button', {name: '矩阵 / 多行', exact: true}).click();
    await modal.getByLabel('公式表格列数').selectOption('8');
    for (const width of [320, 390, 820, 1024, 1440]) {
      await page.setViewportSize({width, height: 1000});
      expect(await modal.evaluate(el => el.scrollWidth <= el.clientWidth + 1), String(width)).toBe(true);
      const sizes = await modal.locator('button:visible').evaluateAll(elements => elements.map(el => el.getBoundingClientRect().height));
      expect(sizes.every(h => h >= 44)).toBe(true);
    }
    await modal.getByLabel('公式表格结构').selectOption('cases');
    await modal.getByLabel('第2行第2列').fill(String.raw`\text{其他}`);
    await modal.getByRole('button', {name: '将结构插入公式'}).click();
    await expect(modal.getByLabel('LaTeX 公式', {exact: true})).toHaveValue(/\\begin\{cases\}[\s\S]+\\text\{其他\}/);
    await modal.getByRole('button', {name: '取消', exact: true}).click();
    await expect(editor).toHaveValue('保留正文');
  } finally {await context.close();}
});
