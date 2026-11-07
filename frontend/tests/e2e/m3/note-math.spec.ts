import {test, expect, type APIRequestContext, type Page} from '@playwright/test';
import {mkdir, readFile} from 'node:fs/promises';
import {resolve} from 'node:path';

const base = 'http://127.0.0.1:8056/api/v1';
async function seed(page: Page, request: APIRequestContext) {
  const username = 'math_' + crypto.randomUUID().replaceAll('-', '');
  const auth = await (await request.post(base + '/auth/register', {data: {username, password: 'Test-password-2026'}})).json();
  const headers = {Authorization: 'Bearer ' + auth.access_token};
  const course = await (await request.post(base + '/courses', {headers, data: {name: '数学笔记'}})).json();
  const note = await (await request.post(base + '/notes', {headers, data: {course_id: course.id, title: '微积分 · 公式练习', content: '# 微积分\n\n从一个公式开始。'}})).json();
  await page.addInitScript(({token, username}) => {localStorage.setItem('hustudy_token', token); localStorage.setItem('hustudy_user', username);}, {token: auth.access_token, username});
  await page.goto(`/notes?course=${course.id}&note=${note.id}`);
  await expect(page.getByLabel('笔记标题')).toHaveValue(note.title);
  return {headers, note};
}
async function screenshot(page: Page, name: string) {
  if (!process.env.HUSTUDY_M3_EVIDENCE) return;
  await mkdir(resolve('../.artifacts/e2e/m3'), {recursive: true});
  await page.screenshot({path: resolve(`../.artifacts/e2e/m3/${name}.png`), animations: 'disabled'});
}

for (const width of [390, 1440]) test(`图标与公式插入、修改、撤销、预览和导出 ${width}px`, async ({page, request}, testInfo) => {
  test.setTimeout(90000);
  await page.setViewportSize({width, height: 1000});
  await seed(page, request);
  const editor = page.getByLabel('Markdown 正文'), open = page.getByRole('button', {name: '公式编辑器', exact: true});
  const modal = page.getByRole('dialog', {name: '公式编辑器', exact: true});
  await editor.fill('前文 x^2 后文');
  await editor.evaluate((el: HTMLTextAreaElement) => {el.focus(); el.setSelectionRange(3, 6);});
  await open.click(); await expect(modal.getByLabel('LaTeX 公式', {exact: true})).toHaveValue('x^2');
  await modal.getByLabel('LaTeX 公式', {exact: true}).fill('\\frac{a}');
  await expect(modal.getByRole('button', {name: '插入公式', exact: true})).toBeDisabled();
  await expect(modal.getByRole('status')).toContainText('公式语法有误');
  await modal.getByLabel('LaTeX 公式', {exact: true}).fill('\\frac{a}{b}');
  await expect(modal.locator('.formula-preview .katex')).toHaveCount(1);
  await modal.getByRole('button', {name: '插入公式', exact: true}).click();
  await expect(editor).toHaveValue('前文 $\\frac{a}{b}$ 后文');
  await expect(editor).toBeFocused();
  await page.getByRole('button', {name: '撤销', exact: true}).click(); await expect(editor).toHaveValue('前文 x^2 后文');
  await page.getByRole('button', {name: '重做', exact: true}).click(); await expect(editor).toHaveValue('前文 $\\frac{a}{b}$ 后文');
  await editor.evaluate((el: HTMLTextAreaElement) => {el.focus(); el.setSelectionRange(8, 8);});
  await open.click(); await expect(modal.getByLabel('LaTeX 公式', {exact: true})).toHaveValue('\\frac{a}{b}');
  await modal.getByLabel('LaTeX 公式', {exact: true}).fill('\\sqrt{x}');
  await modal.getByRole('button', {name: '更新公式', exact: true}).click();
  await expect(editor).toHaveValue('前文 $\\sqrt{x}$ 后文');
  await editor.evaluate((el: HTMLTextAreaElement) => {el.focus(); el.setSelectionRange(el.value.length, el.value.length);});
  await editor.press('Control+Shift+m');
  await modal.getByRole('button', {name: /^独立公式/}).click();
  await modal.getByRole('button', {name: '插入积分模板', exact: true}).click();
  await expect(modal.getByLabel('LaTeX 公式', {exact: true})).toHaveValue('\\int_{a}^{b} f(x)\\,dx');
  await screenshot(page, `note-formula-dialog-${width}-${testInfo.project.name}`);
  expect(await modal.evaluate(el => el.scrollWidth <= el.clientWidth + 1)).toBe(true);
  await modal.getByRole('button', {name: '插入公式', exact: true}).click();
  const expected = '前文 $\\sqrt{x}$ 后文\n\n$$\n\\int_{a}^{b} f(x)\\,dx\n$$';
  await expect(editor).toHaveValue(expected);
  await page.getByRole('button', {name: '分屏预览', exact: true}).click();
  await expect(page.getByLabel('笔记实时预览').locator('.katex')).toHaveCount(2);
  await editor.press('Control+s'); await expect(page.locator('.save-indicator')).toHaveText('已保存到本地服务');
  const downloading = page.waitForEvent('download');
  await page.getByRole('button', {name: '导出 .md', exact: true}).click();
  const downloaded = await downloading;
  await downloaded.saveAs(testInfo.outputPath('formula.md'));
  expect(await readFile(testInfo.outputPath('formula.md'), 'utf8')).toContain(expected);
  await page.getByRole('button', {name: '专注编辑', exact: true}).click();
  await screenshot(page, `note-math-editor-${width}-${testInfo.project.name}`);
  await open.click(); await modal.getByLabel('LaTeX 公式', {exact: true}).fill('未确认的公式');
  await page.keyboard.press('Escape'); await expect(modal).not.toBeVisible();
  await expect(page.locator('.knowledge-editor.is-focused')).toBeVisible();
  await expect(open).toBeFocused(); await expect(editor).toHaveValue(expected);
  await page.keyboard.press('Escape'); await expect(page.locator('.knowledge-editor.is-focused')).toHaveCount(0);
  await page.reload(); await expect(editor).toHaveValue(expected);
});

test('公式安全降级与触屏布局：320/390/820/1024/1440', async ({browser, request}, testInfo) => {
  test.setTimeout(120000);
  const context = await browser.newContext({baseURL: 'http://127.0.0.1:5178', hasTouch: true});
  try {
    const page = await context.newPage(); await seed(page, request);
    const external: string[] = [];
    await page.route('https://formula-test.invalid/**', route => {external.push(route.request().url()); return route.abort();});
    const editor = page.getByLabel('Markdown 正文');
    await editor.fill('# 数学笔记\n\n行内 $x_i^2$。\n\n$$\n\\int_0^1 x^2\\,dx=\\frac{1}{3}\n$$\n\n`$notMath$`\n\n$\\includegraphics{https://formula-test.invalid/spy.png}$\n\n$\\href{javascript:alert(1)}{X}$\n\n<script>window.mathUnsafe=true</script>');
    await page.getByRole('button', {name: '分屏预览', exact: true}).click();
    await expect(page.getByLabel('笔记实时预览').locator('code')).toContainText('$notMath$');
    expect(await page.getByLabel('笔记实时预览').locator('a,img,script').count()).toBe(0);
    expect(await page.evaluate(() => (window as unknown as {mathUnsafe?: boolean}).mathUnsafe)).toBeUndefined();
    for (const width of [320, 390, 820, 1024, 1440]) {
      await page.setViewportSize({width, height: 1000});
      await page.getByRole('button', {name: '专注编辑', exact: true}).click();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `${width}px body`).toBe(true);
      const tools = page.locator('.note-format-toolbar button');
      const sizes = await tools.evaluateAll(buttons => buttons.map(button => {const rect = button.getBoundingClientRect(); return {w: rect.width, h: rect.height, label: button.getAttribute('aria-label')};}));
      expect(sizes.every(size => size.w >= 44 && size.h >= 44 && size.label), `${width}px controls`).toBe(true);
      await page.getByRole('button', {name: '公式编辑器', exact: true}).click();
      const modal = page.getByRole('dialog', {name: '公式编辑器', exact: true});
      await modal.getByLabel('LaTeX 公式', {exact: true}).fill('x'.repeat(4001));
      await expect(modal.getByRole('status')).toContainText('最多 4000');
      await expect(modal.getByRole('button', {name: /^(插入|更新)公式$/})).toBeDisabled();
      expect(await modal.evaluate(el => el.scrollWidth <= el.clientWidth + 1), `${width}px dialog`).toBe(true);
      await page.keyboard.press('Escape'); await page.keyboard.press('Escape');
    }
    expect(external).toEqual([]);
    await screenshot(page, `note-math-touch-${testInfo.project.name}`);
  } finally {await context.close();}
});

test('特殊LaTeX提示使用独立公式并保留内容', async ({page, request}) => {
  await seed(page, request);
  const editor = page.getByLabel('Markdown 正文'); await editor.fill('');
  await page.getByRole('button', {name: '公式编辑器', exact: true}).click();
  const modal = page.getByRole('dialog', {name: '公式编辑器', exact: true});
  await modal.getByLabel('LaTeX 公式', {exact: true}).fill('x+%comment\ny');
  await expect(modal.getByRole('status')).toContainText('独立公式');
  await expect(modal.getByRole('button', {name: '插入公式', exact: true})).toBeDisabled();
  await modal.getByRole('button', {name: /^独立公式/}).click();
  await modal.getByRole('button', {name: '插入公式', exact: true}).click();
  await expect(editor).toHaveValue('$$\nx+%comment\ny\n$$');
  await page.getByRole('button', {name: '分屏预览', exact: true}).click();
  await expect(page.getByLabel('笔记实时预览').locator('.katex')).toHaveCount(1);
  await expect(page.getByLabel('笔记实时预览').locator('.katex-html')).toContainText('x+y');
});

test('自动保存401时公式窗口让出登录，登录后公式草稿仍在', async ({page, request}) => {
  await seed(page, request);
  await page.getByLabel('自动保存笔记', {exact: true}).check();
  let release!: () => void;
  const gate = new Promise<void>(resolve => {release = resolve;});
  await page.route('**/api/v1/notes/*', async route => {
    if (route.request().method() !== 'PATCH') return route.continue();
    await gate;
    await route.fulfill({status: 401, contentType: 'application/json', body: JSON.stringify({error: {message: '登录已过期'}})});
  });
  const editor = page.getByLabel('Markdown 正文'); await editor.fill('正文保留');
  await page.getByRole('button', {name: '公式编辑器', exact: true}).click();
  const modal = page.getByRole('dialog', {name: '公式编辑器', exact: true});
  await modal.getByLabel('LaTeX 公式', {exact: true}).fill('\\sqrt{a+b}');
  release();
  const login = page.getByRole('dialog', {name: /登录已过期/});
  await expect(login).toBeVisible(); await expect(modal).not.toBeVisible();
  await page.unroute('**/api/v1/notes/*');
  await login.getByLabel('密码', {exact: true}).fill('Test-password-2026'); await login.getByRole('button', {name: '登录', exact: true}).click();
  await expect(login).not.toBeVisible();
  await page.getByRole('button', {name: '公式编辑器', exact: true}).click();
  await expect(modal.getByLabel('LaTeX 公式', {exact: true})).toHaveValue('\\sqrt{a+b}');
  await modal.getByRole('button', {name: '插入公式', exact: true}).click();
  await expect(editor).toHaveValue('正文保留$\\sqrt{a+b}$');
});
