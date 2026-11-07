import {test, expect, type APIRequestContext, type Page} from '@playwright/test';
import {mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';

const base = 'http://127.0.0.1:8056/api/v1';
async function seed(request: APIRequestContext, page: Page) {
  const username = 'citations_' + crypto.randomUUID().replaceAll('-', '');
  const auth = await (await request.post(base + '/auth/register', {data: {username, password: 'Test-password-2026'}})).json();
  const headers = {Authorization: 'Bearer ' + auth.access_token};
  const course = await (await request.post(base + '/courses', {headers, data: {name: '引用生命周期验收'}})).json();
  const uploaded = await (await request.post(base + `/courses/${course.id}/documents`, {headers, multipart: {file: {name: '队列讲义.md', mimeType: 'text/markdown', buffer: Buffer.from('# 队列\n\n队列遵循先进先出，可以记录排队顺序。')}}})).json();
  await expect.poll(async () => (await (await request.get(base + `/versions/${uploaded.resource_id}`, {headers})).json()).index_status, {timeout: 20000}).toBe('SUCCEEDED');
  const version = await (await request.get(base + `/versions/${uploaded.resource_id}`, {headers})).json();
  const chunk = (await (await request.get(base + `/versions/${version.id}/chunks`, {headers})).json())[0];
  const citation = {version_id: version.id, chunk_id: chunk.id, quote: chunk.text.slice(0, 500)};
  const note = await (await request.post(base + '/notes', {headers, data: {course_id: course.id, title: '队列复习', content: '这是我的理解。', citations: [citation, citation]}})).json();
  await page.addInitScript(({token, username}) => {localStorage.setItem('hustudy_token', token); localStorage.setItem('hustudy_user', username);}, {token: auth.access_token, username});
  const url = `/notes?course=${course.id}&note=${note.id}`;
  await page.goto(url);
  await expect(page.getByLabel('笔记标题')).toHaveValue(note.title);
  return {headers, course, version, chunk, citation, note, url};
}

for (const width of [390, 1440]) {
  test(`引用来源名、固定版本回源、重复添加及移除保留草稿 ${width}px`, async ({page, request}) => {
    test.setTimeout(90000);
    await page.setViewportSize({width, height: 1000});
    const s = await seed(request, page);
    await page.getByRole('button', {name: /^引用与关联/}).click();
    const sources = page.getByRole('region', {name: '资料来源', exact: true});
    await expect(sources.locator('.citation-card')).toHaveCount(1);
    await expect(sources).toContainText('队列讲义 · v1');
    await page.getByRole('button', {name: '回到原文 ↗', exact: true}).click();
    await expect(page).toHaveURL(new RegExp('version=' + s.version.id));
    await expect(page.locator('.chunk-highlight')).toContainText('先进先出');
    await page.getByLabel('引用到笔记', {exact: true}).selectOption(s.note.id);
    await page.getByRole('button', {name: '引用到所选笔记', exact: true}).first().click();
    await expect(page.locator('.material-reference-grid .source-note-card')).toHaveCount(1);
    await page.locator('.material-reference-grid .source-note-card').click();
    await page.getByRole('button', {name: /^引用与关联/}).click();
    await expect(sources.locator('.citation-card')).toHaveCount(1);
    await request.post(base + `/documents/${s.version.document_id}/versions`, {headers: s.headers, multipart: {file: {name: '新版.md', mimeType: 'text/markdown', buffer: Buffer.from('# 新版\n\n已更新，但旧引用不改写。')}}});
    await sources.getByRole('button', {name: '刷新引用', exact: true}).click();
    await expect(sources).toContainText('队列讲义 · v1');
    if (process.env.HUSTUDY_M3_EVIDENCE) {
      const directory = resolve('../.artifacts/e2e/m3'); await mkdir(directory, {recursive: true});
      await page.evaluate(() => {(document.activeElement as HTMLElement)?.blur(); window.scrollTo({top: 0, behavior: 'instant'});});
      await page.screenshot({path: resolve(directory, `note-citations-${width}.png`), fullPage: true, animations: 'disabled'});
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
    page.once('dialog', dialog => dialog.dismiss());
    await sources.getByRole('button', {name: '移除此引用', exact: true}).click();
    await expect(sources.locator('.citation-card')).toHaveCount(1);
    await page.getByRole('button', {name: '关闭引用与关联', exact: true}).click();
    await page.getByLabel('笔记标题').fill(''); // Keep this draft unsaved while editing only its citations.
    await page.getByLabel('Markdown 正文').fill('移除引用期间保留的本地草稿');
    await page.getByRole('button', {name: /^引用与关联/}).click();
    page.once('dialog', dialog => dialog.accept());
    await sources.getByRole('button', {name: '移除此引用', exact: true}).click();
    await expect(sources.locator('.citation-card')).toHaveCount(0);
    await expect(page.getByLabel('Markdown 正文')).toHaveValue('移除引用期间保留的本地草稿');
    const saved = await (await request.get(base + `/notes/${s.note.id}`, {headers: s.headers})).json();
    expect(saved.content).toBe('这是我的理解。'); expect(saved.revision).toBe(1);
    expect((await request.get(base + `/versions/${s.version.id}/original`, {headers: s.headers})).status()).toBe(200);
    expect(await (await request.get(base + `/versions/${s.version.id}/references`, {headers: s.headers})).json()).toEqual([]);
  });
}

test('引用加载失败可重试，失效来源仍可移除且不会清空草稿', async ({page, request}) => {
  const s = await seed(request, page);
  const route = `**/api/v1/notes/${s.note.id}/citations`;
  await page.getByRole('button', {name: /^引用与关联/}).click();
  await expect(page.locator('.citation-card')).toHaveCount(1);
  await page.route(route, r => r.abort('failed'));
  const sources = page.getByRole('region', {name: '资料来源', exact: true});
  await sources.getByRole('button', {name: '刷新引用', exact: true}).click();
  await expect(sources).toContainText('资料引用未能加载');
  await page.getByRole('button', {name: '关闭引用与关联', exact: true}).click();
  await page.getByLabel('笔记标题').fill('');
  await page.getByLabel('Markdown 正文').fill('网络失败时编辑的内容');
  await page.getByRole('button', {name: /^引用与关联/}).click();
  await page.unroute(route);
  await sources.getByRole('button', {name: '重试加载引用', exact: true}).click();
  await expect(sources.locator('.citation-card')).toHaveCount(1);
  await request.delete(base + `/documents/${s.version.document_id}`, {headers: s.headers});
  await sources.getByRole('button', {name: '刷新引用', exact: true}).click();
  await expect(sources).toContainText('来源当前不可用');
  await expect(sources.getByRole('button', {name: '回到原文 ↗', exact: true})).toHaveCount(0);
  await page.route(route + '/*', r => r.request().method() === 'DELETE' ? r.abort('failed') : r.continue());
  page.once('dialog', dialog => dialog.accept());
  await sources.getByRole('button', {name: '移除此引用', exact: true}).click();
  await expect(page.locator('.toast.error')).toBeVisible();
  await expect(sources.locator('.citation-card')).toHaveCount(1);
  await expect(sources.getByRole('button', {name: '移除此引用', exact: true})).toBeEnabled();
  await page.unroute(route + '/*');
  page.once('dialog', dialog => dialog.accept());
  await sources.getByRole('button', {name: '移除此引用', exact: true}).click();
  await expect(sources.locator('.citation-card')).toHaveCount(0);
  await expect(page.getByLabel('Markdown 正文')).toHaveValue('网络失败时编辑的内容');
});

test('自动保存按2秒触发，隐藏页暂停，回到前台恢复计时', async ({page, request}) => {
  const s = await seed(request, page);
  await page.getByLabel('自动保存笔记', {exact: true}).check();
  await page.getByRole('button', {name: /^引用与关联/}).click();
  await expect(page.locator('.citation-card')).toHaveCount(1);
  await page.getByRole('button', {name: '关闭引用与关联', exact: true}).click();
  await page.clock.install({time: new Date('2026-10-18T01:00:00Z')});
  await page.clock.pauseAt(new Date('2026-10-18T01:00:01Z'));
  let writes = 0;
  page.on('request', r => {if (r.method() === 'PATCH' && r.url().endsWith('/notes/' + s.note.id)) writes++;});
  await page.getByLabel('Markdown 正文').fill('前台定时保存');
  await page.clock.runFor(1999); expect(writes).toBe(0);
  await page.clock.runFor(501);
  await expect.poll(() => writes).toBe(1);
  await expect(page.locator('.save-indicator')).toHaveText('已保存到本地服务');
  await page.getByLabel('Markdown 正文').fill('切回前台后保存');
  await page.evaluate(() => {Object.defineProperty(document, 'visibilityState', {configurable: true, value: 'hidden'}); document.dispatchEvent(new Event('visibilitychange'));});
  await page.clock.runFor(6000); expect(writes).toBe(1);
  expect((await (await request.get(base + `/notes/${s.note.id}`, {headers: s.headers})).json()).content).toBe('前台定时保存');
  await page.evaluate(() => {Object.defineProperty(document, 'visibilityState', {configurable: true, value: 'visible'}); document.dispatchEvent(new Event('visibilitychange'));});
  await page.clock.runFor(1999); expect(writes).toBe(1);
  await page.clock.runFor(501);
  await expect.poll(() => writes).toBe(2);
  await expect(page.locator('.save-indicator')).toHaveText('已保存到本地服务');
  expect((await (await request.get(base + `/notes/${s.note.id}`, {headers: s.headers})).json()).content).toBe('切回前台后保存');
  await page.route(`**/api/v1/notes/${s.note.id}`, route => route.request().method() === 'PATCH'
    ? route.fulfill({status: 409, contentType: 'application/json', body: JSON.stringify({error: {message: '笔记版本冲突', details: {server_title: '队列复习', server_content: '另一窗口版本', server_revision: 99, server_tags: []}}})})
    : route.continue());
  await page.getByLabel('Markdown 正文').fill('冲突后的本地草稿');
  await page.clock.runFor(2500);
  await expect(page.locator('.conflict-panel')).toBeVisible();
  expect(writes).toBe(3);
  for (const visibility of ['hidden', 'visible']) {
    await page.evaluate(value => {Object.defineProperty(document, 'visibilityState', {configurable: true, value}); document.dispatchEvent(new Event('visibilitychange'));}, visibility);
    await page.clock.runFor(6000);
  }
  expect(writes).toBe(3);
  await expect(page.getByLabel('Markdown 正文')).toHaveValue('冲突后的本地草稿');
});
