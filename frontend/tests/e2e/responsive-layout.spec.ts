import { test, expect, type Page, type APIRequestContext, type Locator } from '@playwright/test';

const base = 'http://127.0.0.1:8056/api/v1';
async function seed(request: APIRequestContext) {
  const username = 'layout_' + crypto.randomUUID().replaceAll('-', '');
  const registration = await request.post(base + '/auth/register', { data: { username, password: 'Test-password-2026' } });
  expect(registration.status()).toBe(201);
  const { access_token: token } = await registration.json();
  const headers = { Authorization: 'Bearer ' + token };
  const course = await (await request.post(base + '/courses', { headers, data: { name: '计算机网络与操作系统 · 多端布局验收', description: 'LongUnbrokenCourseDescription'.repeat(8) } })).json();
  const upload = await request.post(base + `/courses/${course.id}/documents`, { headers, multipart: { file: { name: '计算机网络复习资料.md', mimeType: 'text/markdown', buffer: Buffer.from('# 缓冲区\n缓冲区用于暂存传输的数据。\n\n## 来源定位\n窗口大小与传输效率。') } } });
  expect(upload.status()).toBe(202);
  const job = await upload.json();
  await expect.poll(async () => (await (await request.get(base + `/versions/${job.resource_id}`, { headers })).json()).index_status).toBe('SUCCEEDED');
  const note = await (await request.post(base + '/notes', { headers, data: { course_id: course.id, title: '缓冲区学习笔记', content: '# 缓冲区与窗口\n\n理解概念，核对来源。\n\n```text\n' + 'long_code_identifier_'.repeat(30) + '\n```\n\n| 概念 | 含义 | 示例 |\n| --- | --- | --- |\n| 缓冲区 | 暂存传输数据 | 发送与接收 |' } })).json();
  return { username, token, course, note };
}
async function login(page: Page, user: { username: string; token: string }) {
  await page.addInitScript(user => { localStorage.setItem('hustudy_token', user.token); localStorage.setItem('hustudy_user', user.username); }, user);
}
async function navigate(page: Page, label: string) {
  const toggle = page.getByRole('button', { name: '打开导航菜单', exact: true });
  if (await toggle.isVisible()) {
    await toggle.click();
    await page.getByRole('dialog', { name: '导航菜单', exact: true }).getByRole('button', { name: label, exact: true }).click();
    await expect(page.getByRole('dialog', { name: '导航菜单', exact: true })).not.toBeVisible();
  } else await page.locator('.sidebar').getByRole('button', { name: label, exact: true }).click();
  await expect(page.locator('.content > .page')).toBeVisible();
}
async function fits(page: Page) {
  const size = await page.evaluate(() => ({ viewport: innerWidth, document: document.documentElement.scrollWidth, body: document.body.scrollWidth }));
  expect(size.document, JSON.stringify(size)).toBeLessThanOrEqual(size.viewport + 1);
  expect(size.body, JSON.stringify(size)).toBeLessThanOrEqual(size.viewport + 1);
  const content = await page.locator('.content').boundingBox();
  expect(content!.width).toBeGreaterThan(260);
  expect(content!.x + content!.width).toBeLessThanOrEqual(size.viewport + 1);
}

for (const [width, height] of [[1440, 1000], [1024, 768], [820, 1180], [390, 844], [320, 740]]) {
 test.describe(`${width}px 输入设备`, () => {
  test.use({ hasTouch: width <= 1024, isMobile: width <= 1024 });
  test(`全站 ${width}×${height} 布局与操作`, async ({ page, request }) => {
    test.setTimeout(90_000);
    const user = await seed(request); await login(page, user); await page.setViewportSize({ width, height });
    await page.goto(`/overview?course=${user.course.id}`);
    await expect(page.locator('.dashboard-metrics')).not.toContainText('…');
    await fits(page);
    await page.screenshot({ path: test.info().outputPath('overview.png'), fullPage: true, animations: 'disabled' });
    // A real native dialog must fit and remain usable even at 320px.
    await page.getByRole('button', { name: '整理课程：' + user.course.name, exact: true }).click();
    const editor = page.getByRole('dialog', { name: '整理课程空间', exact: true });
    await expect(editor).toBeVisible();
    const rect = await editor.boundingBox(); expect(rect!.width).toBeLessThanOrEqual(width);
    await page.keyboard.press('Escape'); await expect(editor).not.toBeVisible();
    for (const [label, section] of [['资料阅读', 'materials'], ['知识笔记', 'notes'], ['AI 学习', 'ai'], ['真题与模拟卷', 'exam'], ['错题复习', 'review'], ['课程查找', 'search'], ['备份与恢复', 'backup'], ['使用指南', 'help']]) {
      await navigate(page, label); await expect(page).toHaveURL(new RegExp('/' + section + '\\?'));
      if (section === 'materials') {
        const toggle = page.getByRole('button', { name: /资料库与上传/ });
        if (await toggle.isVisible()) await toggle.click();
        await page.locator('.material-document').first().click();
        await expect(page.locator('.reading-paper')).toContainText('缓冲区用于暂存传输的数据');
        if (await toggle.isVisible()) await toggle.click();
        await expect(page.locator('.reading-paper')).toBeVisible();
      }
      if (section === 'notes') {
        const toggle = page.getByRole('button', { name: /笔记列表与新建/ });
        if (await toggle.isVisible()) await toggle.click();
        await page.locator('.knowledge-item').filter({ hasText: user.note.title }).click();
        if (await toggle.isVisible()) await toggle.click();
        await page.getByRole('button', { name: 'Markdown 预览', exact: true }).click();
        await expect(page.locator('.markdown-preview pre')).toBeVisible();
      }
      if (section === 'search') {
        await page.getByLabel('查找课程资料与笔记').fill('缓冲区');
        await page.getByRole('button', { name: '查找', exact: true }).click();
        await expect(page.locator('.knowledge-hit').first()).toBeVisible();
      }
      if (section === 'help') await page.locator('.help-columns details').first().locator('summary').click();
      await fits(page);
      if (width <= 390) {
        const smallButtons = await page.locator('.content button:visible').evaluateAll(buttons => buttons.filter(button => button.getBoundingClientRect().height < 43.5).map(button => button.textContent));
        expect(smallButtons).toEqual([]);
      }
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.screenshot({ path: test.info().outputPath(`${section}.png`), fullPage: true, animations: 'disabled' });
    }
  });
 });
}

test('窄屏导航焦点、旋转与取消离开仍保留草稿', async ({ page, request }) => {
  const user = await seed(request); await login(page, user);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/notes?course=${user.course.id}`);
  await page.getByLabel('Markdown 正文').fill('未命名草稿，不能被导航或尺寸变化清除。');
  const toggle = page.getByRole('button', { name: '打开导航菜单', exact: true });
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await expect(toggle).toBeInViewport();
  await toggle.click();
  const drawer = page.getByRole('dialog', { name: '导航菜单', exact: true });
  await expect(drawer).toBeVisible();
  await expect(drawer.getByRole('button', { name: '关闭导航菜单', exact: true })).toBeFocused();
  // Native modal focus remains inside; Escape restores focus to the trigger.
  await page.keyboard.press('Shift+Tab'); expect(await drawer.evaluate(el => el.contains(document.activeElement))).toBe(true);
  await page.keyboard.press('Escape'); await expect(toggle).toBeFocused();
  await toggle.click();
  page.once('dialog', dialog => dialog.dismiss());
  await drawer.getByRole('button', { name: '资料阅读', exact: true }).click();
  await expect(page).toHaveURL(/\/notes\?/); await expect(drawer).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByLabel('Markdown 正文')).toHaveValue('未命名草稿，不能被导航或尺寸变化清除。');
  await toggle.click(); await page.setViewportSize({ width: 1440, height: 900 });
  await expect(drawer).not.toBeVisible();
  await expect(page.locator('.sidebar')).toBeVisible();
  await expect(page.getByLabel('Markdown 正文')).toHaveValue('未命名草稿，不能被导航或尺寸变化清除。');
  await page.setViewportSize({ width: 390, height: 844 }); await toggle.click();
  page.once('dialog', dialog => dialog.accept());
  await drawer.getByRole('button', { name: '资料阅读', exact: true }).click();
  await expect(page).toHaveURL(/\/materials\?/); await expect(drawer).not.toBeVisible();
  await expect(toggle).toBeFocused(); await fits(page);
});

test('手机登录注册界面和触控输入尺寸', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 740 }); await page.goto('/');
  const username = page.getByLabel('用户名', { exact: true });
  await expect(username).toBeVisible();
  expect(await username.evaluate(el => getComputedStyle(el).fontSize)).toBe('16px');
  await page.getByRole('button', { name: '还没有账户？注册一个', exact: true }).click();
  await expect(page.getByRole('heading', { name: '创建你的学习空间' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(320);
  await page.screenshot({ path: test.info().outputPath('registration.png'), fullPage: true, animations: 'disabled' });
});


// Measure actual rendered colors, including transparent ancestor backgrounds.
async function readable(locator: Locator) {
  const contrast = await locator.evaluate(element => {
    const rgb = (value: string) => { const parts = value.match(/[\d.]+/g)!.map(Number); return [parts[0], parts[1], parts[2], parts[3] ?? 1]; };
    const layers: number[][] = [];
    for (let node: Element | null = element; node; node = node.parentElement) layers.push(rgb(getComputedStyle(node).backgroundColor));
    const background = layers.reverse().reduce((under, over) => over.slice(0, 3).map((value, index) => value * over[3] + under[index] * (1 - over[3])), [255, 255, 255]);
    const foreground = rgb(getComputedStyle(element).color).slice(0, 3);
    const luminance = (color: number[]) => color.map(value => { const s = value / 255; return s <= .04045 ? s / 12.92 : ((s + .055) / 1.055) ** 2.4; }).reduce((total, value, index) => total + value * [.2126, .7152, .0722][index], 0);
    const a = luminance(background), b = luminance(foreground);
    return (Math.max(a, b) + .05) / (Math.min(a, b) + .05);
  });
  expect(contrast).toBeGreaterThanOrEqual(4.5);
}

test('关键文字配色、工作区标识与减少动效', async ({ page, request }) => {
  const user = await seed(request); await login(page, user);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(`/overview?course=${user.course.id}`);
  const context = page.locator('.workspace-context');
  await expect(context).toContainText('课程总览');
  await expect(page.locator('.sidebar .workspace-account strong')).toHaveText(user.username);
  await readable(context);
  await readable(page.getByRole('button', { name: '进入课程工作台', exact: false }));
  await readable(page.locator('.sidebar .nav-item.active'));
  await readable(page.locator('.metric-card small').first());
  await navigate(page, '资料阅读');
  await expect(context).toContainText('资料阅读');
  await expect(page.locator('.status-succeeded').first()).toBeVisible();
  await readable(page.locator('.status-succeeded').first());
  await navigate(page, 'AI 学习');
  await expect(context).toContainText('AI 学习');
  const primary = page.getByRole('button', { name: '资料原文检索', exact: true });
  await readable(primary);
  await readable(page.getByRole('button', { name: '资料问答', exact: true }));
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await primary.hover();
  expect(await primary.evaluate(element => getComputedStyle(element).transform)).toBe('none');
  expect(await page.locator('.module-illustration').evaluate(element => getComputedStyle(element).animationName)).toBe('none');
  await navigate(page, '备份与恢复');
  await expect(context).toContainText('备份与恢复');
  await expect(page.locator('.theme-backup')).toBeVisible();
  await fits(page);
});
