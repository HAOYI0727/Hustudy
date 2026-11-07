import {test, expect, type Page, type APIRequestContext} from '@playwright/test';
import {mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';

const base = 'http://127.0.0.1:8056/api/v1';
const reader = (page: Page) => page.getByRole('region', {name: '笔记阅读模式', exact: true});
const article = (page: Page) => reader(page).getByRole('article', {name: '笔记阅读正文', exact: true});

async function seed(page: Page, request: APIRequestContext, withCitation = false) {
  const username = 'reading_' + crypto.randomUUID().replaceAll('-', '');
  const authResponse = await request.post(base + '/auth/register', {data: {username, password: 'Test-password-2026'}});
  expect(authResponse.ok()).toBe(true);
  const auth = await authResponse.json();
  const headers = {Authorization: 'Bearer ' + auth.access_token};
  const course = await (await request.post(base + '/courses', {headers, data: {name: '笔记阅读模式验收'}})).json();
  const encoded = await page.evaluate(() => {
    const canvas = document.createElement('canvas'); canvas.width = 320; canvas.height = 120;
    const context = canvas.getContext('2d')!;
    context.fillStyle = '#e8f5ef'; context.fillRect(0, 0, 320, 120);
    context.fillStyle = '#217b64'; context.fillRect(24, 28, 110, 64); context.fillRect(186, 28, 110, 64);
    context.fillStyle = 'white'; context.font = '18px sans-serif'; context.fillText('READ', 48, 66); context.fillText('WRITE', 210, 66);
    return canvas.toDataURL('image/png').split(',')[1];
  });
  const image = await (await request.post(base + `/courses/${course.id}/assets`, {headers, multipart: {file: {name: '阅读示意图.png', mimeType: 'image/png', buffer: Buffer.from(encoded, 'base64')}}})).json();
  const target = await (await request.post(base + '/notes', {headers, data: {course_id: course.id, title: '延伸阅读笔记', content: '# 延伸阅读\n\n双链可以在阅读模式中连续查看。'}})).json();
  let version: {id: string} | undefined;
  const citations: {version_id: string; chunk_id: string; quote: string}[] = [];
  if (withCitation) {
    const uploaded = await (await request.post(base + `/courses/${course.id}/documents`, {headers, multipart: {file: {name: '阅读模式来源.md', mimeType: 'text/markdown', buffer: Buffer.from('# 事务\n\n事务将相关操作组织为一个整体，需要同时考虑原子性与隔离性。')}}})).json();
    await expect.poll(async () => (await (await request.get(base + `/versions/${uploaded.resource_id}`, {headers})).json()).index_status, {timeout: 20000}).toBe('SUCCEEDED');
    version = await (await request.get(base + `/versions/${uploaded.resource_id}`, {headers})).json();
    const chunk = (await (await request.get(base + `/versions/${version!.id}/chunks`, {headers})).json())[0];
    citations.push({version_id: version!.id, chunk_id: chunk.id, quote: chunk.text});
  }
  const content = [
    '# 正文标题', '', '> 学习时先理解概念，再核对例子。', '',
    '这里有 **重点**、*说明* 和行内公式 $a^2+b^2=c^2$。', '',
    '## 对比表', '', '| 项目 | 含义 |', '| --- | --- |', '| 原子性 | 整体提交 |', '',
    '- [x] 已核对概念', '- [ ] 继续复习', '',
    '## 公式与代码', '', '$$', '\\sum_{i=1}^{n}i=\\frac{n(n+1)}{2}', '$$', '',
    '```markdown', '# 代码中的伪标题', 'SELECT id, name FROM students WHERE active = 1;', '```', '',
    '补充说明', '---', '', `![[asset:${image.id}|阅读示意图]]`, '',
    '## 重复小节', '', '第一个小节保留独立位置。', '', '## 重复小节', '', '第二个小节也应可定位。', '',
    `[[note:${target.id}|延伸链接]]`, '',
    '![外部图片](https://reading-probe.invalid/private.png)', '',
    '<script>window.__noteReadingUnsafe = true</script>', '', '[不安全链接](javascript:alert(1))', '',
    ...Array.from({length: 12}, (_, index) => `阅读段落 ${index + 1}：保持适当的行距和宽度，长笔记也能通过目录定位重点。\n`),
  ].join('\n');
  const noteResponse = await request.post(base + '/notes', {headers, data: {course_id: course.id, title: 'Markdown 阅读样例', content, tags: ['阅读验收', '重点'], citations}});
  expect(noteResponse.ok()).toBe(true);
  const note = await noteResponse.json();
  await page.addInitScript(({token, username}) => {localStorage.setItem('hustudy_token', token); localStorage.setItem('hustudy_user', username);}, {token: auth.access_token, username});
  return {headers, auth, username, course, note, target, version, content, image};
}

async function evidence(page: Page, name: string) {
  if (!process.env.HUSTUDY_NOTE_READING_EVIDENCE) return;
  await mkdir(resolve('../.artifacts/e2e/optional'), {recursive: true});
  await page.screenshot({path: resolve(`../.artifacts/e2e/optional/${name}.png`), animations: 'disabled'});
}

async function expandSources(page: Page) {
  const summary = reader(page).locator('summary').filter({hasText: /^资料引用$/});
  if (!await summary.evaluate(element => (element.parentElement as HTMLDetailsElement).open)) await summary.click();
  return reader(page).getByRole('region', {name: '资料来源', exact: true});
}

for (const width of [390, 1440]) test(`独立阅读富Markdown、实际标题目录、字号及专注布局 ${width}px`, async ({page, request}, testInfo) => {
  test.setTimeout(90000);
  await page.setViewportSize({width, height: 1000});
  const s = await seed(page, request);
  const writes: string[] = [], external: string[] = [];
  page.on('request', r => {
    if (['POST', 'PATCH', 'PUT', 'DELETE'].includes(r.method()) && r.url().includes('/api/v1/notes')) writes.push(r.url());
  });
  await page.route('https://reading-probe.invalid/**', route => {external.push(route.request().url()); return route.abort();});
  await page.goto(`/notes?course=${s.course.id}`);
  await page.getByRole('button', {name: `阅读：${s.note.title}`, exact: true}).click();
  await expect(reader(page)).toBeVisible();
  await expect(page.getByRole('button', {name: '阅读模式', exact: true})).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByLabel('Markdown 正文')).not.toBeVisible();
  await expect(page.getByRole('group', {name: 'Markdown 格式工具', exact: true})).not.toBeVisible();
  await expect(article(page).getByRole('heading', {name: '正文标题', exact: true})).toBeVisible();
  await expect(article(page).getByRole('table')).toContainText('原子性');
  await expect(article(page).locator('pre')).toContainText('SELECT id, name');
  await expect(article(page).locator('.katex')).toHaveCount(2);
  await expect(article(page).getByRole('checkbox').first()).toBeChecked();
  await expect(article(page).getByRole('checkbox').first()).toBeDisabled();
  const checkboxBounds = await article(page).getByRole('checkbox').first().boundingBox();
  expect(checkboxBounds!.width).toBeLessThan(30);
  expect(checkboxBounds!.height).toBeLessThan(30);
  const image = article(page).getByRole('img', {name: '阅读示意图', exact: true});
  await expect.poll(() => image.evaluate((element: HTMLImageElement) => element.naturalWidth)).toBe(320);
  await expect(article(page)).toContainText('外部图片请先上传到课程资料库');
  expect(external).toEqual([]);
  expect(await page.evaluate(() => '__noteReadingUnsafe' in window)).toBe(false);
  await expect(article(page).locator('script, a[href^="javascript:"]')).toHaveCount(0);
  const outline = reader(page).getByRole('navigation', {name: '笔记目录', exact: true});
  await expect(outline.getByRole('button', {name: '代码中的伪标题', exact: true})).toHaveCount(0);
  await expect(outline.getByRole('button', {name: '补充说明', exact: true})).toHaveCount(1);
  const repeated = outline.getByRole('button', {name: '重复小节', exact: true});
  await expect(repeated).toHaveCount(2);
  await repeated.nth(1).click();
  await expect(article(page).getByRole('heading', {name: '重复小节', exact: true}).nth(1)).toBeFocused();
  const standardSize = await article(page).evaluate(element => parseFloat(getComputedStyle(element).fontSize));
  await reader(page).getByLabel('阅读字号', {exact: true}).selectOption('large');
  expect(await article(page).evaluate(element => parseFloat(getComputedStyle(element).fontSize))).toBeGreaterThan(standardSize);
  await reader(page).getByLabel('阅读字号', {exact: true}).selectOption('standard');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  await reader(page).locator('.note-reader-toolbar').scrollIntoViewIfNeeded();
  await evidence(page, `note-reading-${width}-${testInfo.project.name}`);
  await reader(page).getByRole('button', {name: '专注阅读', exact: true}).click();
  const focus = page.getByRole('dialog', {name: '专注阅读', exact: true});
  await expect(focus).toBeVisible();
  await focus.getByRole('button', {name: '本篇目录', exact: true}).click();
  await expect(page.getByRole('article', {name: '笔记阅读正文', exact: true})).toHaveCount(1);
  await focus.getByRole('navigation', {name: '笔记目录', exact: true}).getByRole('button', {name: '补充说明', exact: true}).click();
  await expect(article(page).getByRole('heading', {name: '补充说明', exact: true})).toBeFocused();
  expect(await focus.evaluate(element => element.scrollWidth <= element.clientWidth + 1)).toBe(true);
  await evidence(page, `note-reading-focus-${width}-${testInfo.project.name}`);
  await reader(page).locator('.note-reader-toolbar').scrollIntoViewIfNeeded();
  await evidence(page, `note-reading-focus-top-${width}-${testInfo.project.name}`);
  await page.keyboard.press('Escape');
  await expect(focus).not.toBeVisible();
  await expect(reader(page).getByRole('button', {name: '专注阅读', exact: true})).toBeFocused();
  await article(page).getByRole('button', {name: s.target.title + ' ↗', exact: true}).click();
  await expect(article(page).getByRole('heading', {name: '延伸阅读', exact: true})).toBeVisible();
  await expect(reader(page).locator('.note-reader-heading').getByRole('heading', {name: s.target.title, exact: true})).toBeFocused();
  await expect(page.getByRole('button', {name: '阅读模式', exact: true})).toHaveAttribute('aria-pressed', 'true');
  const libraryToggle = page.getByRole('button', {name: /笔记列表与新建/});
  if (await libraryToggle.isVisible() && await libraryToggle.getAttribute('aria-expanded') === 'false') await libraryToggle.click();
  await page.locator('.knowledge-library .knowledge-item').filter({hasText: s.note.title}).click();
  await expect(article(page).getByRole('heading', {name: '正文标题', exact: true})).toBeVisible();
  expect(writes).toEqual([]);
  const saved = await (await request.get(base + `/notes/${s.note.id}`, {headers: s.headers})).json();
  expect(saved.content).toBe(s.content); expect(saved.revision).toBe(1);
});

test('阅读保留未保存草稿、阻止静默写入，返回编辑保留撤销和导航保护', async ({page, request}) => {
  const s = await seed(page, request);
  await page.goto(`/notes?course=${s.course.id}&note=${s.note.id}`);
  await expect(page.getByLabel('Markdown 正文')).toHaveValue(s.content);
  await page.getByLabel('自动保存笔记', {exact: true}).check();
  await page.clock.install({time: new Date('2026-10-27T01:00:00Z')});
  await page.clock.pauseAt(new Date('2026-10-27T01:00:01Z'));
  let writes = 0;
  page.on('request', r => {if (r.method() === 'PATCH' && r.url().endsWith('/notes/' + s.note.id)) writes++;});
  const draft = `# 本地阅读草稿\n\n没有保存，也能阅读。\n\n[[note:${s.target.id}]]`;
  await page.getByLabel('Markdown 正文').fill(draft);
  await page.getByRole('button', {name: '阅读模式', exact: true}).click();
  await expect(article(page).getByRole('heading', {name: '本地阅读草稿', exact: true})).toBeVisible();
  await expect(reader(page)).toContainText('未保存');
  await page.clock.runFor(6000);
  expect(writes).toBe(0);
  expect((await (await request.get(base + `/notes/${s.note.id}`, {headers: s.headers})).json()).content).toBe(s.content);
  page.once('dialog', dialog => dialog.dismiss());
  await article(page).getByRole('button', {name: s.target.title + ' ↗', exact: true}).click();
  await expect(article(page).getByRole('heading', {name: '本地阅读草稿', exact: true})).toBeVisible();
  await reader(page).getByRole('button', {name: '返回编辑', exact: true}).click();
  await expect(page.getByLabel('Markdown 正文')).toHaveValue(draft);
  await page.getByRole('button', {name: '撤销', exact: true}).click();
  await expect(page.getByLabel('Markdown 正文')).toHaveValue(s.content);
  await page.getByRole('button', {name: '重做', exact: true}).click();
  await expect(page.getByLabel('Markdown 正文')).toHaveValue(draft);
  await page.clock.runFor(2500);
  await expect.poll(() => writes).toBe(1);
  await expect(page.locator('.save-indicator')).toHaveText('已保存到本地服务');
  expect((await (await request.get(base + `/notes/${s.note.id}`, {headers: s.headers})).json()).content).toBe(draft);
});

test('自动保存默认关闭，手动保存与明确启停有效，刷新保留本账户偏好', async ({page, request}) => {
  const s = await seed(page, request);
  await page.goto(`/notes?course=${s.course.id}&note=${s.note.id}`);
  await expect(page.getByLabel('Markdown 正文')).toHaveValue(s.content);
  const autoSave = page.getByLabel('自动保存笔记', {exact: true});
  await expect(autoSave).not.toBeChecked();
  await page.clock.install({time: new Date('2026-10-27T02:00:00Z')});
  await page.clock.pauseAt(new Date('2026-10-27T02:00:01Z'));
  let writes = 0;
  page.on('request', r => {if (r.method() === 'PATCH' && r.url().endsWith('/notes/' + s.note.id)) writes++;});
  const savedContent = async () => (await (await request.get(base + `/notes/${s.note.id}`, {headers: s.headers})).json()).content;
  await page.getByLabel('Markdown 正文').fill('默认使用手动保存。');
  await page.clock.runFor(6000);
  expect(writes).toBe(0); expect(await savedContent()).toBe(s.content);
  await page.getByRole('button', {name: '立即保存', exact: true}).click();
  await expect(page.locator('.save-indicator')).toHaveText('已保存到本地服务');
  expect(writes).toBe(1); expect(await savedContent()).toBe('默认使用手动保存。');
  await autoSave.check();
  await page.getByLabel('Markdown 正文').fill('主动开启后定时保存。');
  await page.clock.runFor(2500);
  await expect.poll(() => writes).toBe(2);
  await expect(page.locator('.save-indicator')).toHaveText('已保存到本地服务');
  expect(await savedContent()).toBe('主动开启后定时保存。');
  await page.getByLabel('Markdown 正文').fill('关闭后保留为未保存草稿。');
  await autoSave.uncheck();
  await page.clock.runFor(6000);
  expect(writes).toBe(2); expect(await savedContent()).toBe('主动开启后定时保存。');
  await expect(page.getByLabel('Markdown 正文')).toHaveValue('关闭后保留为未保存草稿。');
  await page.getByLabel('Markdown 正文').press('Control+s');
  await expect(page.locator('.save-indicator')).toHaveText('已保存到本地服务');
  expect(writes).toBe(3); expect(await savedContent()).toBe('关闭后保留为未保存草稿。');
  // Timer behavior is already verified. Allow React's lazy-loading timers to run after navigation.
  await page.clock.resume();
  await page.goto(`/notes?course=${s.course.id}&note=${s.note.id}`);
  await expect(page.getByLabel('Markdown 正文')).toHaveValue('关闭后保留为未保存草稿。');
  await expect(autoSave).not.toBeChecked();
  await autoSave.check();
  await page.goto(`/notes?course=${s.course.id}&note=${s.note.id}`);
  await expect(page.getByLabel('Markdown 正文')).toHaveValue('关闭后保留为未保存草稿。');
  await expect(autoSave).toBeChecked();
  expect(writes).toBe(3);
});

test('打开关联笔记期间阻止输入，加载完成后的改名可保存且不会被覆盖', async ({page, request}) => {
  const s = await seed(page, request);
  await page.goto(`/notes?course=${s.course.id}&note=${s.note.id}`);
  const title = page.getByLabel('笔记标题', {exact: true});
  await expect(title).toHaveValue(s.note.title);
  await expect(page.getByLabel('Markdown 正文')).toHaveValue(s.content);
  let release!: () => void;
  const gate = new Promise<void>(resolve => {release = resolve;});
  let openingResponseReady = false;
  await page.route(`**/api/v1/notes/${s.target.id}`, async route => {
    if (route.request().method() !== 'GET') {await route.continue(); return;}
    const response = await route.fetch();
    expect(response.ok()).toBe(true);
    openingResponseReady = true;
    await gate;
    await route.fulfill({response});
  });
  try {
    await page.getByRole('button', {name: /^引用与关联/}).click();
    await page.getByRole('button', {name: '↗ ' + s.target.title, exact: true}).click();
    await expect.poll(() => openingResponseReady).toBe(true);
    const editor = page.locator('.knowledge-editor');
    await expect(editor).toHaveAttribute('inert', '');
    await expect(editor).toHaveAttribute('aria-busy', 'true');
    const renamedTitle = '加载完成后改名的延伸笔记';
    let renameFinished = false;
    const rename = (async () => {
      await title.click();
      await title.fill(renamedTitle);
      renameFinished = true;
    })();
    await expect(title).toHaveValue(s.note.title);
    expect(renameFinished).toBe(false);
    release();
    await rename;
    await expect(editor).not.toHaveAttribute('inert');
    await expect(title).toHaveValue(renamedTitle);
    await expect(page.getByLabel('Markdown 正文')).toHaveValue(s.target.content);
    await page.getByRole('button', {name: '立即保存', exact: true}).click();
    await expect(page.locator('.save-indicator')).toHaveText('已保存到本地服务');
    const saved = await (await request.get(base + `/notes/${s.target.id}`, {headers: s.headers})).json();
    expect(saved.title).toBe(renamedTitle); expect(saved.content).toBe(s.target.content); expect(saved.revision).toBe(2);
    const original = await (await request.get(base + `/notes/${s.note.id}`, {headers: s.headers})).json();
    expect(original.title).toBe(s.note.title); expect(original.content).toBe(s.content); expect(original.revision).toBe(1);
  } finally {release();}
});

test('保存响应晚于会话401返回时保留后续草稿与恢复副本，并停止自动写入', async ({page, request}) => {
  const s = await seed(page, request);
  await page.goto(`/notes?course=${s.course.id}&note=${s.note.id}`);
  const editor = page.getByLabel('Markdown 正文');
  await expect(editor).toHaveValue(s.content);
  await page.getByLabel('自动保存笔记', {exact: true}).check();
  await page.clock.install({time: new Date('2026-10-27T03:00:00Z')});
  await page.clock.pauseAt(new Date('2026-10-27T03:00:01Z'));
  const firstDraft = '# 第一版\n\n服务端已保存，响应暂未返回。';
  const latestDraft = firstDraft + '\n\n保存期间继续输入，这一段必须保留为未保存草稿。';
  let release!: () => void;
  const gate = new Promise<void>(resolve => {release = resolve;});
  let writes = 0, serverSaved = false, expiredReads = 0;
  await page.route(`**/api/v1/notes/${s.note.id}`, async route => {
    if (route.request().method() !== 'PATCH') {await route.continue(); return;}
    writes++;
    if (writes !== 1) {await route.continue(); return;}
    const response = await route.fetch();
    expect(response.ok()).toBe(true);
    expect((await response.json()).content).toBe(firstDraft);
    serverSaved = true;
    await gate;
    await route.fulfill({response});
  });
  try {
    await editor.fill(firstDraft);
    await page.clock.runFor(2500);
    await expect.poll(() => serverSaved).toBe(true);
    await editor.fill(latestDraft);
    await expect(editor).toHaveValue(latestDraft);
    await page.route(`**/api/v1/notes/${s.note.id}/citations`, route => {
      expiredReads++;
      return route.fulfill({status: 401, contentType: 'application/json', body: JSON.stringify({error: {message: '引用读取会话已过期'}})});
    });
    // The first visit loads citations while staying in edit mode; reading mode cannot mask a stray autosave.
    await page.getByRole('button', {name: /^引用与关联/}).click();
    const login = page.getByRole('dialog', {name: /登录已过期/});
    await expect(login).toBeVisible();
    expect(expiredReads).toBeGreaterThan(0);
    const lateResponse = page.waitForResponse(response => response.request().method() === 'PATCH' && response.url().endsWith('/notes/' + s.note.id));
    release();
    expect((await lateResponse).status()).toBe(200);
    await expect(page.locator('.save-indicator')).not.toContainText('保存中');
    await page.clock.runFor(6000);
    await expect(login).toBeVisible();
    await expect(editor).toHaveValue(latestDraft);
    await expect.poll(() => page.evaluate(noteId => Object.keys(localStorage)
      .filter(key => key.startsWith('hustudy-note-recovery:v1:'))
      .map(key => JSON.parse(localStorage.getItem(key)!))
      .find(copy => copy.noteId === noteId)?.draft.content, s.note.id)).toBe(latestDraft);
    expect(writes).toBe(1);
    const saved = await (await request.get(base + `/notes/${s.note.id}`, {headers: s.headers})).json();
    expect(saved.content).toBe(firstDraft); expect(saved.revision).toBe(2);
    await expect(page.locator('.save-indicator')).not.toHaveText('已保存到本地服务');
  } finally {release();}
});

test('专注阅读图片401通过共享会话处理让出登录，未保存草稿仍保留', async ({page, request}) => {
  const s = await seed(page, request);
  await page.goto(`/notes?course=${s.course.id}&note=${s.note.id}`);
  await expect(page.getByLabel('Markdown 正文')).toHaveValue(s.content);
  await expect(page.getByLabel('自动保存笔记', {exact: true})).not.toBeChecked();
  let writes = 0;
  page.on('request', r => {if (['PATCH', 'POST', 'DELETE'].includes(r.method()) && r.url().includes('/api/v1/notes')) writes++;});
  const draft = s.content + '\n\n图片会话过期时保留的本地补充。';
  await page.getByLabel('Markdown 正文').fill(draft);
  await page.getByRole('button', {name: '阅读模式', exact: true}).click();
  await expect.poll(() => article(page).getByRole('img', {name: '阅读示意图', exact: true}).evaluate((element: HTMLImageElement) => element.naturalWidth)).toBe(320);
  const assetRoute = `**/api/v1/assets/${s.image.id}`;
  let release!: () => void;
  const gate = new Promise<void>(resolve => {release = resolve;});
  let expired = false, attempts = 0;
  await page.route(assetRoute, async route => {
    attempts++;
    if (expired) {await route.continue(); return;}
    expired = true;
    await gate;
    await route.fulfill({status: 401, contentType: 'application/json', body: JSON.stringify({error: {message: '图片读取会话已过期'}})});
  });
  await reader(page).getByRole('button', {name: '专注阅读', exact: true}).click();
  await expect(page.getByRole('dialog', {name: '专注阅读', exact: true})).toBeVisible();
  await expect.poll(() => attempts).toBeGreaterThan(0);
  release();
  const login = page.getByRole('dialog', {name: /登录已过期/});
  await expect(login).toBeVisible();
  await expect(page.locator('dialog[open]')).toHaveCount(0);
  await page.unroute(assetRoute);
  await login.getByLabel('密码', {exact: true}).fill('Test-password-2026');
  await login.getByRole('button', {name: '登录', exact: true}).click();
  await expect(login).not.toBeVisible();
  await expect(article(page)).toContainText('图片会话过期时保留的本地补充。');
  await expect(page.getByRole('dialog', {name: '专注阅读', exact: true})).not.toBeVisible();
  await reader(page).getByRole('button', {name: '返回编辑', exact: true}).click();
  await expect(page.getByLabel('Markdown 正文')).toHaveValue(draft);
  expect(writes).toBe(0);
  const token = await page.evaluate(() => localStorage.getItem('hustudy_token'));
  const saved = await (await request.get(base + `/notes/${s.note.id}`, {headers: {Authorization: 'Bearer ' + token}})).json();
  expect(saved.content).toBe(s.content); expect(saved.revision).toBe(1);
});

test('阅读引用只读、失败可重试，专注401让出登录并保留笔记', async ({page, request}) => {
  test.setTimeout(90000);
  const s = await seed(page, request, true);
  await page.goto(`/notes?course=${s.course.id}&note=${s.note.id}`);
  await expect(page.getByLabel('Markdown 正文')).toHaveValue(s.content);
  await page.getByRole('button', {name: '阅读模式', exact: true}).click();
  let sources = await expandSources(page);
  await expect(sources.locator('.citation-card')).toHaveCount(1);
  await expect(sources).toContainText('阅读模式来源 · v1');
  await expect(sources.getByRole('button', {name: '移除此引用', exact: true})).toHaveCount(0);
  const route = `**/api/v1/notes/${s.note.id}/citations`;
  await page.route(route, requestRoute => requestRoute.abort('failed'));
  await sources.getByRole('button', {name: '刷新引用', exact: true}).click();
  await expect(sources).toContainText('资料引用未能加载');
  await expect(article(page).getByRole('heading', {name: '正文标题', exact: true})).toBeVisible();
  await page.unroute(route);
  await sources.getByRole('button', {name: '重试加载引用', exact: true}).click();
  await expect(sources.locator('.citation-card')).toHaveCount(1);
  await reader(page).getByRole('button', {name: '专注阅读', exact: true}).click();
  await expect(page.getByRole('dialog', {name: '专注阅读', exact: true})).toBeVisible();
  sources = await expandSources(page);
  await expect(sources.locator('.citation-card')).toHaveCount(1);
  await page.route(route, requestRoute => requestRoute.fulfill({status: 401, contentType: 'application/json', body: JSON.stringify({error: {message: '阅读验收：登录已过期'}})}));
  await sources.getByRole('button', {name: '刷新引用', exact: true}).click();
  const auth = page.getByRole('dialog', {name: /登录已过期/});
  await expect(auth).toBeVisible();
  await expect(page.locator('dialog[open]')).toHaveCount(0);
  await page.unroute(route);
  await auth.getByLabel('密码', {exact: true}).fill('Test-password-2026');
  await auth.getByRole('button', {name: '登录', exact: true}).click();
  await expect(auth).not.toBeVisible();
  await expect(article(page).getByRole('heading', {name: '正文标题', exact: true})).toBeVisible();
  sources = await expandSources(page);
  const retry = sources.getByRole('button', {name: '重试加载引用', exact: true});
  if (await retry.isVisible()) await retry.click();
  await expect(sources.locator('.citation-card')).toHaveCount(1);
  await expect(sources.getByRole('button', {name: '移除此引用', exact: true})).toHaveCount(0);
  const loadedChunks = page.waitForResponse(response => response.url().includes(`/api/v1/versions/${s.version!.id}/chunks`) && response.ok());
  await sources.getByRole('button', {name: '回到原文 ↗', exact: true}).click();
  await loadedChunks;
  await expect(page).toHaveURL(new RegExp('version=' + s.version!.id));
  await expect(page.locator('.chunk-highlight')).toContainText('原子性与隔离性');
  const token = await page.evaluate(() => localStorage.getItem('hustudy_token'));
  const saved = await (await request.get(base + `/notes/${s.note.id}`, {headers: {Authorization: 'Bearer ' + token}})).json();
  expect(saved.content).toBe(s.content); expect(saved.revision).toBe(1);
});
