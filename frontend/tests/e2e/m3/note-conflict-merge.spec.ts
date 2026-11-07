import {test, expect, type Page, type APIRequestContext, type Download} from '@playwright/test';
import {fileURLToPath} from 'node:url';

const base = 'http://127.0.0.1:8056/api/v1';
const original = '# 合并练习\n\n第一段原文。\n\n第二段原文。\n\n第三段原文。\n';
const localText = original.replace('第一段原文。', '第一段本地补充 $x^2$。');
const serverText = original.replace('第二段原文。', '第二段服务端补充。');
const combinedText = localText.replace('第二段原文。', '第二段服务端补充。');

async function setup(page: Page, request: APIRequestContext, content = original, title = '合并练习') {
  const username = 'merge_' + crypto.randomUUID().replaceAll('-', '');
  const registration = await request.post(base + '/auth/register', {data: {username, password: 'Test-password-2026'}});
  expect(registration.status()).toBe(201);
  const auth = await registration.json();
  const headers = {Authorization: 'Bearer ' + auth.access_token};
  const courseResponse = await request.post(base + '/courses', {headers, data: {name: '隔离合并练习'}});
  expect(courseResponse.status()).toBe(201);
  const course = await courseResponse.json();
  const noteResponse = await request.post(base + '/notes', {headers, data: {course_id: course.id, title, content}});
  expect(noteResponse.status()).toBe(201);
  const note = await noteResponse.json();
  await page.addInitScript(({token, username}) => {
    localStorage.setItem('hustudy_token', token);
    localStorage.setItem('hustudy_user', username);
  }, {token: auth.access_token, username});
  return {headers, course, note, auth};
}

async function openNote(page: Page, fixture: Awaited<ReturnType<typeof setup>>, content = fixture.note.content) {
  await page.goto(`/notes?course=${fixture.course.id}&note=${fixture.note.id}`);
  await expect(page.getByLabel('Markdown 正文')).toHaveValue(content);
}

async function remoteEdit(request: APIRequestContext, fixture: Awaited<ReturnType<typeof setup>>, revision: number, content: string, extra: Record<string, unknown> = {}) {
  const response = await request.patch(base + `/notes/${fixture.note.id}`, {headers: fixture.headers, data: {revision, content, ...extra}});
  expect(response.status()).toBe(200);
  return response.json();
}

async function mergeDialog(page: Page) {
  await expect(page.locator('.conflict-panel')).toBeVisible();
  await page.getByRole('button', {name: '逐段合并', exact: true}).click();
  const dialog = page.getByRole('dialog', {name: '合并笔记修改', exact: true});
  await expect(dialog).toBeVisible();
  return dialog;
}

async function downloadedText(download: Download) {
  const stream = await download.createReadStream();
  if (!stream) throw new Error('下载未生成可读文件');
  const chunks: Buffer[] = [];
  for await (const chunk of stream) chunks.push(Buffer.from(chunk));
  return Buffer.concat(chunks).toString('utf8');
}

for (const width of [390, 1440]) test(`非重叠正文与元数据合并只生成草稿，明确保存后保留双方修改 ${width}px`, async ({page, request}) => {
  await page.setViewportSize({width, height: 1000});
  const fixture = await setup(page, request);
  let writes = 0;
  page.on('request', r => {if (r.method() === 'PATCH' && r.url().endsWith('/notes/' + fixture.note.id)) writes++;});
  await openNote(page, fixture);
  await remoteEdit(request, fixture, fixture.note.revision, serverText, {tags: ['服务端标签']});
  await page.getByLabel('自动保存笔记', {exact: true}).check();
  await page.getByLabel('笔记标题').fill('本地更正的标题');
  await page.getByLabel('Markdown 正文').fill(localText);
  const dialog = await mergeDialog(page);
  const beforeMerge = writes;
  await expect(dialog.getByLabel('合并结果预览')).toHaveText(combinedText);
  await expect(dialog.getByRole('region', {name: /^冲突段落 /})).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2)).toBe(true);
  expect(await dialog.evaluate(element => element.scrollWidth <= element.clientWidth + 2)).toBe(true);
  await dialog.screenshot({path: fileURLToPath(new URL(`../../../../.artifacts/e2e/optional/note-merge-${width}-${test.info().project.name}.png`, import.meta.url))});
  await dialog.getByRole('button', {name: '应用合并到草稿', exact: true}).click();
  await expect(dialog).not.toBeVisible();
  await expect(page.getByLabel('Markdown 正文')).toHaveValue(combinedText);
  await page.waitForTimeout(2200);
  expect(writes).toBe(beforeMerge);
  expect((await (await request.get(base + `/notes/${fixture.note.id}`, {headers: fixture.headers})).json()).content).toBe(serverText);
  await page.getByRole('button', {name: '立即保存', exact: true}).click();
  await expect(page.locator('.save-indicator')).toHaveText('已保存到本地服务');
  const saved = await (await request.get(base + `/notes/${fixture.note.id}`, {headers: fixture.headers})).json();
  expect(saved.content).toBe(combinedText);
  expect(saved.title).toBe('本地更正的标题');
  expect(saved.tags).toEqual(['服务端标签']);
  expect(writes).toBe(beforeMerge + 1);
});

test('重叠段落须逐项选择，取消保留草稿，混合选择保留准确正文', async ({page, request}) => {
  const baseline = '# 两处冲突\n\n左侧原文\n\n固定段落一\n固定段落二\n固定段落三\n\n右侧原文\n';
  const local = baseline.replace('左侧原文', '左侧本地').replace('右侧原文', '右侧本地');
  const server = baseline.replace('左侧原文', '左侧服务端').replace('右侧原文', '右侧服务端');
  const fixture = await setup(page, request, baseline);
  await openNote(page, fixture);
  await remoteEdit(request, fixture, fixture.note.revision, server);
  await page.getByLabel('自动保存笔记', {exact: true}).check();
  await page.getByLabel('Markdown 正文').fill(local);
  let dialog = await mergeDialog(page);
  await expect(dialog.getByRole('region', {name: /^冲突段落 /})).toHaveCount(2);
  await expect(dialog.getByRole('button', {name: '应用合并到草稿', exact: true})).toBeDisabled();
  await dialog.getByRole('region', {name: '冲突段落 1', exact: true}).getByRole('button', {name: '采用本地内容', exact: true}).click();
  await expect(dialog.getByRole('button', {name: '应用合并到草稿', exact: true})).toBeDisabled();
  await dialog.getByRole('button', {name: '关闭合并笔记修改', exact: true}).click();
  await expect(page.getByRole('button', {name: '逐段合并', exact: true})).toBeFocused();
  await expect(page.getByLabel('Markdown 正文')).toHaveValue(local);
  dialog = await mergeDialog(page);
  await dialog.getByRole('region', {name: '冲突段落 1', exact: true}).getByRole('button', {name: '采用本地内容', exact: true}).click();
  await dialog.getByRole('region', {name: '冲突段落 2', exact: true}).getByRole('button', {name: '采用服务端内容', exact: true}).click();
  const mixed = baseline.replace('左侧原文', '左侧本地').replace('右侧原文', '右侧服务端');
  await expect(dialog.getByLabel('合并结果预览')).toHaveText(mixed);
  await dialog.getByRole('button', {name: '应用合并到草稿', exact: true}).click();
  await expect(page.getByLabel('Markdown 正文')).toHaveValue(mixed);
  expect((await (await request.get(base + `/notes/${fixture.note.id}`, {headers: fixture.headers})).json()).content).toBe(server);
});

test('合并后再次发生服务端修改，旧 revision 不覆盖并可再次合并', async ({page, request}) => {
  const fixture = await setup(page, request);
  await openNote(page, fixture);
  const second = await remoteEdit(request, fixture, fixture.note.revision, serverText);
  await page.getByLabel('自动保存笔记', {exact: true}).check();
  await page.getByLabel('Markdown 正文').fill(localText);
  let dialog = await mergeDialog(page);
  await dialog.getByRole('button', {name: '应用合并到草稿', exact: true}).click();
  const thirdText = serverText.replace('第三段原文。', '第三段再次远程更新。');
  await remoteEdit(request, fixture, second.revision, thirdText);
  await page.getByRole('button', {name: '立即保存', exact: true}).click();
  await expect(page.locator('.conflict-panel')).toContainText('第三段再次远程更新。');
  await expect(page.getByLabel('Markdown 正文')).toHaveValue(combinedText);
  expect((await (await request.get(base + `/notes/${fixture.note.id}`, {headers: fixture.headers})).json()).content).toBe(thirdText);
  dialog = await mergeDialog(page);
  const finalText = combinedText.replace('第三段原文。', '第三段再次远程更新。');
  await expect(dialog.getByLabel('合并结果预览')).toHaveText(finalText);
  await dialog.getByRole('button', {name: '应用合并到草稿', exact: true}).click();
  await page.getByRole('button', {name: '立即保存', exact: true}).click();
  await expect(page.locator('.save-indicator')).toHaveText('已保存到本地服务');
  expect((await (await request.get(base + `/notes/${fixture.note.id}`, {headers: fixture.headers})).json()).content).toBe(finalText);
});

test('冲突全文可分别下载，安全标题命名且比较中的 HTML 不执行', async ({page, request}) => {
  const fixture = await setup(page, request, original, '实验/公式:草稿');
  const unsafeMarkup = '<img src="/merge-probe" onerror="window.mergeExecuted=1">\n<script>window.mergeExecuted=2</script>\n';
  const local = localText + unsafeMarkup;
  await openNote(page, fixture);
  await remoteEdit(request, fixture, fixture.note.revision, serverText);
  await page.getByLabel('自动保存笔记', {exact: true}).check();
  await page.getByLabel('Markdown 正文').fill(local);
  await expect(page.locator('.conflict-panel')).toBeVisible();
  for (const [button, content] of [['下载本地草稿', local], ['下载服务端版本', serverText]]) {
    const pending = page.waitForEvent('download');
    await page.locator('.conflict-panel').getByRole('button', {name: button, exact: true}).click();
    const download = await pending;
    expect(download.suggestedFilename()).toContain('实验');
    expect(download.suggestedFilename()).toMatch(/\.md$/);
    expect(download.suggestedFilename()).not.toMatch(/[<>:"/\\|?*\x00-\x1f]/);
    expect(await downloadedText(download)).toBe(content);
  }
  const dialog = await mergeDialog(page);
  await expect(dialog.getByLabel('合并结果预览')).toContainText(unsafeMarkup);
  await expect(dialog.locator('script, img')).toHaveCount(0);
  expect(await page.evaluate(() => (window as Window & {mergeExecuted?: number}).mergeExecuted)).toBeUndefined();
});

test('刷新后的新恢复副本携带共同版本，仍能正确合并', async ({page, request}) => {
  const fixture = await setup(page, request);
  await page.route(`**/api/v1/notes/${fixture.note.id}`, async route => {
    if (route.request().method() === 'PATCH') await route.fulfill({status: 503, json: {error: {message: '隔离模拟离线'}}});
    else await route.continue();
  });
  await openNote(page, fixture);
  await page.getByLabel('自动保存笔记', {exact: true}).check();
  await page.getByLabel('Markdown 正文').fill(localText);
  await expect(page.locator('.save-indicator')).toContainText('未保存');
  await expect.poll(async () => page.evaluate(userId => Object.keys(localStorage)
    .filter(key => key.startsWith(`hustudy-note-recovery:v1:${userId}:`))
    .map(key => JSON.parse(localStorage.getItem(key)!)).find(row => row.draft.content.includes('第一段本地补充'))?.base?.content, fixture.auth.user.id)).toBe(original);
  await remoteEdit(request, fixture, fixture.note.revision, serverText);
  page.once('dialog', d => d.accept());
  await page.reload();
  await expect(page.getByLabel('Markdown 正文')).toHaveValue(serverText);
  await page.getByRole('button', {name: '核对并恢复', exact: true}).click();
  await expect(page.getByLabel('Markdown 正文')).toHaveValue(localText);
  const dialog = await mergeDialog(page);
  await expect(dialog.getByLabel('合并结果预览')).toHaveText(combinedText);
  await dialog.getByRole('button', {name: '应用合并到草稿', exact: true}).click();
  await expect(page.getByLabel('Markdown 正文')).toHaveValue(combinedText);
});

test('旧恢复副本缺少共同版本时拒绝猜测合并，原草稿仍可下载', async ({page, request}) => {
  const fixture = await setup(page, request);
  const row = {id: crypto.randomUUID(), userId: fixture.auth.user.id, courseId: fixture.course.id, noteId: fixture.note.id,
    noteCourseId: fixture.course.id, baseRevision: fixture.note.revision, draft: {title: fixture.note.title, content: localText, tags: []},
    tagInput: '', pending: null, updatedAt: new Date().toISOString()};
  await page.addInitScript(row => {
    localStorage.setItem(`hustudy-note-recovery:v1:${row.userId}:${row.courseId}:${row.id}`, JSON.stringify(row));
  }, row);
  await remoteEdit(request, fixture, fixture.note.revision, serverText);
  await openNote(page, fixture, serverText);
  await page.getByRole('button', {name: '核对并恢复', exact: true}).click();
  await expect(page.getByLabel('Markdown 正文')).toHaveValue(localText);
  const dialog = await mergeDialog(page);
  await expect(dialog).toContainText(/共同版本|基线|无法自动合并/);
  await expect(dialog.getByRole('button', {name: '应用合并到草稿', exact: true})).toBeDisabled();
  await dialog.getByRole('button', {name: '关闭合并笔记修改', exact: true}).click();
  const pending = page.waitForEvent('download');
  await page.locator('.conflict-panel').getByRole('button', {name: '下载本地草稿', exact: true}).click();
  expect(await downloadedText(await pending)).toBe(localText);
  expect((await (await request.get(base + `/notes/${fixture.note.id}`, {headers: fixture.headers})).json()).content).toBe(serverText);
});

for (const baseState of ['missing', 'null'] as const) test(`恢复副本版本号相同但共同版本${baseState === 'missing' ? '缺失' : '为 null'}时仍须冲突核对`, async ({page, request}) => {
  const fixture = await setup(page, request);
  const latest = await remoteEdit(request, fixture, fixture.note.revision, serverText);
  const row = {id: crypto.randomUUID(), userId: fixture.auth.user.id, courseId: fixture.course.id, noteId: fixture.note.id,
    noteCourseId: fixture.course.id, baseRevision: latest.revision, draft: {title: fixture.note.title, content: localText, tags: []},
    ...(baseState === 'null' ? {base: null} : {}), tagInput: '', pending: null, updatedAt: new Date().toISOString()};
  await page.addInitScript(row => {
    localStorage.setItem(`hustudy-note-recovery:v1:${row.userId}:${row.courseId}:${row.id}`, JSON.stringify(row));
  }, row);
  let writes = 0;
  page.on('request', r => {if (r.method() === 'PATCH' && r.url().endsWith('/notes/' + fixture.note.id)) writes++;});
  await openNote(page, fixture, serverText);
  await page.getByLabel('自动保存笔记', {exact: true}).check();
  await page.getByRole('button', {name: '核对并恢复', exact: true}).click();
  await expect(page.getByLabel('Markdown 正文')).toHaveValue(localText);
  await expect(page.locator('.conflict-panel')).toContainText('第二段服务端补充。');
  await expect(page.getByRole('button', {name: '立即保存', exact: true})).toBeDisabled();
  const dialog = await mergeDialog(page);
  await expect(dialog).toContainText(/共同版本|基线|无法自动合并/);
  await expect(dialog.getByRole('button', {name: '应用合并到草稿', exact: true})).toBeDisabled();
  await page.waitForTimeout(2200);
  expect(writes).toBe(0);
  expect((await (await request.get(base + `/notes/${fixture.note.id}`, {headers: fixture.headers})).json()).content).toBe(serverText);
});

test('恢复副本写入配额不足时拒绝应用，保留草稿且不发送保存请求', async ({page, request}) => {
  const fixture = await setup(page, request);
  let writes = 0;
  page.on('request', r => {if (r.method() === 'PATCH' && r.url().endsWith('/notes/' + fixture.note.id)) writes++;});
  await openNote(page, fixture);
  await page.getByLabel('自动保存笔记', {exact: true}).check();
  await remoteEdit(request, fixture, fixture.note.revision, serverText);
  await page.getByLabel('Markdown 正文').fill(localText);
  const dialog = await mergeDialog(page);
  const beforeApply = writes;
  await expect(dialog.getByLabel('合并结果预览')).toHaveText(combinedText);
  // Affect only this isolated page's recovery writes after the preview is ready.
  await page.evaluate(() => {
    const originalSet = Storage.prototype.setItem;
    Storage.prototype.setItem = function (key, value) {
      if (key.startsWith('hustudy-note-recovery:v1:')) throw new DOMException('Isolated quota failure', 'QuotaExceededError');
      originalSet.call(this, key, value);
    };
  });
  await dialog.getByRole('button', {name: '应用合并到草稿', exact: true}).click();
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole('alert')).toContainText(/恢复副本|存储空间|权限不足/);
  await expect(page.getByLabel('Markdown 正文')).toHaveValue(localText);
  await page.waitForTimeout(2200);
  expect(writes).toBe(beforeApply);
  expect((await (await request.get(base + `/notes/${fixture.note.id}`, {headers: fixture.headers})).json()).content).toBe(serverText);
  const pending = page.waitForEvent('download');
  await dialog.getByRole('button', {name: '下载本地草稿', exact: true}).click();
  expect(await downloadedText(await pending)).toBe(localText);
  await dialog.getByRole('button', {name: '关闭合并笔记修改', exact: true}).click();
  page.once('dialog', confirmation => confirmation.accept());
  await page.getByRole('button', {name: '核对后保留本地草稿', exact: true}).click();
  await expect(page.locator('.conflict-panel')).not.toBeVisible();
  await expect(page.getByLabel('Markdown 正文')).toHaveValue(localText);
  await page.waitForTimeout(2200);
  expect(writes).toBe(beforeApply);
  await page.getByRole('button', {name: '立即保存', exact: true}).click();
  await expect(page.locator('.save-indicator')).toHaveText('已保存到本地服务');
  expect(writes).toBe(beforeApply + 1);
  expect((await (await request.get(base + `/notes/${fixture.note.id}`, {headers: fixture.headers})).json()).content).toBe(localText);
});

test('标题标签文件夹同时冲突必须逐项核对，保存采用各自选择的值', async ({page, request}) => {
  const fixture = await setup(page, request);
  const folders = [];
  for (const name of ['本地目录', '服务端目录']) {
    const response = await request.post(base + '/note-folders', {headers: fixture.headers, data: {course_id: fixture.course.id, name}});
    expect(response.status()).toBe(201);
    folders.push(await response.json());
  }
  // Pause autosaving through a real failed request so editing three fields is independent of timing.
  const notePattern = `**/api/v1/notes/${fixture.note.id}`;
  await page.route(notePattern, async route => {
    if (route.request().method() === 'PATCH') await route.fulfill({status: 503, json: {error: {message: '隔离模拟保存失败'}}});
    else await route.continue();
  });
  await openNote(page, fixture);
  await page.getByLabel('自动保存笔记', {exact: true}).check();
  await page.getByLabel('Markdown 正文').fill(localText);
  await expect(page.locator('.save-indicator')).toContainText('未保存');
  await page.getByLabel('笔记标题').fill('本地标题');
  await page.getByRole('button', {name: /^文件夹与标签/}).click();
  const metadata = page.getByRole('dialog', {name: '文件夹与标签', exact: true});
  await metadata.getByLabel('笔记所在文件夹', {exact: true}).selectOption(folders[0].id);
  await metadata.getByLabel('新标签', {exact: true}).fill('本地标签');
  await metadata.getByRole('button', {name: '添加标签', exact: true}).click();
  await metadata.getByRole('button', {name: '关闭文件夹与标签', exact: true}).click();
  await remoteEdit(request, fixture, fixture.note.revision, serverText, {title: '服务端标题', tags: ['服务端标签'], folder_id: folders[1].id});
  await page.unroute(notePattern);
  await page.getByRole('button', {name: '立即保存', exact: true}).click();
  const dialog = await mergeDialog(page);
  const apply = dialog.getByRole('button', {name: '应用合并到草稿', exact: true});
  await expect(apply).toBeDisabled();
  const title = dialog.getByRole('region', {name: '标题冲突', exact: true});
  await expect(title).toContainText('本地标题');
  await expect(title).toContainText('服务端标题');
  await title.getByRole('button', {name: '采用本地标题', exact: true}).click();
  await expect(apply).toBeDisabled();
  const tags = dialog.getByRole('region', {name: '标签冲突', exact: true});
  await expect(tags).toContainText('本地标签');
  await expect(tags).toContainText('服务端标签');
  await tags.getByRole('button', {name: '采用服务端标签', exact: true}).click();
  await expect(apply).toBeDisabled();
  const folder = dialog.getByRole('region', {name: '文件夹冲突', exact: true});
  await expect(folder).toContainText('本地目录');
  await expect(folder).toContainText('服务端目录');
  await folder.getByRole('button', {name: '采用本地文件夹', exact: true}).click();
  await expect(apply).toBeEnabled();
  await expect(dialog.getByLabel('合并结果预览')).toHaveText(combinedText);
  await apply.click();
  await expect(page.getByLabel('笔记标题')).toHaveValue('本地标题');
  await page.getByRole('button', {name: '立即保存', exact: true}).click();
  await expect(page.locator('.save-indicator')).toHaveText('已保存到本地服务');
  const saved = await (await request.get(base + `/notes/${fixture.note.id}`, {headers: fixture.headers})).json();
  expect(saved.title).toBe('本地标题');
  expect(saved.tags).toEqual(['服务端标签']);
  expect(saved.folder_id).toBe(folders[0].id);
  expect(saved.content).toBe(combinedText);
});

test('合并窗口的过期草稿快照不能覆盖新内容，会话失效关闭窗口但保留草稿', async ({page, request}) => {
  const fixture = await setup(page, request);
  let writes = 0;
  page.on('request', r => {if (r.method() === 'PATCH' && r.url().endsWith('/notes/' + fixture.note.id)) writes++;});
  await openNote(page, fixture);
  await page.getByLabel('自动保存笔记', {exact: true}).check();
  await remoteEdit(request, fixture, fixture.note.revision, serverText);
  await page.getByLabel('Markdown 正文').fill(localText);
  const dialog = await mergeDialog(page);
  await expect(dialog.getByLabel('合并结果预览')).toHaveText(combinedText);
  const beforeApply = writes;
  const laterDraft = localText + '\n窗口打开后追加的本地内容。\n';
  // Simulate an editor update arriving after the merge snapshot, without bypassing React state.
  await page.getByLabel('Markdown 正文').evaluate((element, value) => {
    const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')!.set!;
    setter.call(element, value);
    element.dispatchEvent(new Event('input', {bubbles: true}));
  }, laterDraft);
  await expect(page.getByLabel('Markdown 正文')).toHaveValue(laterDraft);
  await dialog.getByRole('button', {name: '应用合并到草稿', exact: true}).click();
  await expect(dialog.getByRole('alert')).toContainText(/已变化|重新核对/);
  await expect(page.getByLabel('Markdown 正文')).toHaveValue(laterDraft);
  await page.evaluate(() => window.dispatchEvent(new Event('hustudy:notes-session-expired')));
  await expect(dialog).not.toBeVisible();
  await expect(page.getByLabel('Markdown 正文')).toHaveValue(laterDraft);
  await expect(page.locator('.conflict-panel')).toBeVisible();
  await page.waitForTimeout(2200);
  expect(writes).toBe(beforeApply);
  expect((await (await request.get(base + `/notes/${fixture.note.id}`, {headers: fixture.headers})).json()).content).toBe(serverText);
});

test('全部采用服务端时无需保存，原本地草稿保留为可下载恢复副本', async ({page, request}) => {
  const fixture = await setup(page, request);
  let writes = 0;
  page.on('request', r => {if (r.method() === 'PATCH' && r.url().endsWith('/notes/' + fixture.note.id)) writes++;});
  await openNote(page, fixture);
  const server = original.replace('第一段原文。', '第一段服务端修订。');
  const latest = await remoteEdit(request, fixture, fixture.note.revision, server, {title: '服务端最终标题'});
  await page.getByLabel('自动保存笔记', {exact: true}).check();
  await page.getByLabel('笔记标题').fill('待合并本地标题');
  await page.getByLabel('Markdown 正文').fill(localText);
  const dialog = await mergeDialog(page);
  const beforeApply = writes;
  await dialog.getByRole('region', {name: '标题冲突', exact: true}).getByRole('button', {name: '采用服务端标题', exact: true}).click();
  await dialog.getByRole('region', {name: '冲突段落 1', exact: true}).getByRole('button', {name: '采用服务端内容', exact: true}).click();
  await expect(dialog.getByLabel('合并结果预览')).toHaveText(server);
  await dialog.getByRole('button', {name: '应用合并到草稿', exact: true}).click();
  await expect(page.getByLabel('Markdown 正文')).toHaveValue(server);
  await expect(page.getByLabel('笔记标题')).toHaveValue('服务端最终标题');
  await expect(page.getByRole('button', {name: '立即保存', exact: true})).toBeDisabled();
  await expect(page.locator('.save-indicator')).toHaveText('合并结果与服务端一致 · 无需保存');
  await page.waitForTimeout(2200);
  expect(writes).toBe(beforeApply);
  const saved = await (await request.get(base + `/notes/${fixture.note.id}`, {headers: fixture.headers})).json();
  expect(saved.content).toBe(server);
  expect(saved.revision).toBe(latest.revision);
  const recovery = page.getByRole('region', {name: '本机笔记恢复'}).locator('article').filter({hasText: '待合并本地标题'});
  await expect(recovery).toHaveCount(1);
  const pending = page.waitForEvent('download');
  await recovery.getByRole('button', {name: '下载副本', exact: true}).click();
  expect(await downloadedText(await pending)).toBe(localText);
});
