import {test, expect, type APIRequestContext, type Page} from "@playwright/test";

const base = "http://127.0.0.1:8056/api/v1";
const file = (name: string, text = `# ${name}\n自制资料：进程分配资源，线程参与调度。`) => ({name, mimeType: "text/markdown", buffer: Buffer.from(text)});
async function setup(page: Page, request: APIRequestContext) {
  const username = "flow_" + crypto.randomUUID().replaceAll("-", "");
  const auth = await (await request.post(base + "/auth/register", {data: {username, password: "Test-password-2026"}})).json();
  const headers = {Authorization: "Bearer " + auth.access_token};
  const course = await (await request.post(base + "/courses", {headers, data: {name: "资料学习衔接验收"}})).json();
  await page.addInitScript(({username, token}) => {localStorage.setItem("hustudy_token", token); localStorage.setItem("hustudy_user", username);}, {username, token: auth.access_token});
  return {headers, course};
}
async function upload(request: APIRequestContext, headers: Record<string,string>, course: string, name: string, document?: string) {
  const response = await request.post(base + (document ? `/documents/${document}/versions` : `/courses/${course}/documents`), {headers, multipart: {file: file(name)}});
  expect(response.status()).toBe(202);
  const job = await response.json();
  await expect.poll(async () => (await (await request.get(base + `/versions/${job.resource_id}`, {headers})).json()).index_status, {timeout: 20_000}).toBe("SUCCEEDED");
  return (await request.get(base + `/versions/${job.resource_id}`, {headers})).json();
}

test("多选上传：服务异常暂停、显式重试不重发成功项、过滤空态", async ({page, request}) => {
  const {headers, course} = await setup(page, request);
  const posted: string[] = [];
  await page.route(`**/api/v1/courses/${course.id}/documents`, async route => {
    if (route.request().method() !== "POST") return route.continue();
    const name = /filename="([^"]+)"/.exec(route.request().postDataBuffer()!.toString())![1]; posted.push(name);
    if (posted.length === 2) return route.fulfill({status: 503, json: {error: {code: "TEST_PAUSE", message: "模拟服务中断"}}});
    return route.continue();
  });
  await page.goto(`/materials?course=${course.id}`);
  await page.getByLabel("选择课程文件").setInputFiles([file("one.md"), file("two.md"), file("three.md")]);
  await page.getByRole("button", {name: "上传并开始整理", exact: true}).click();
  const queue = page.getByRole("region", {name: "资料上传队列"});
  await expect(queue.locator('[data-state="paused"]')).toHaveCount(1);
  await expect(queue).toContainText("保存结果未确认"); expect(posted).toEqual(["one.md", "two.md"]);
  await page.getByRole("button", {name: "重试未成功文件", exact: true}).click();
  await expect(queue).toContainText("已保存 3 / 3 份");
  expect(posted).toEqual(["one.md", "two.md", "two.md", "three.md"]);
  const docs = await (await request.get(base + `/courses/${course.id}/documents`, {headers})).json(); expect(docs).toHaveLength(3);
  await page.getByLabel("筛选资料名称或标签").fill("绝无此名称");
  await expect(page.getByText("没有匹配资料，试试清除筛选", {exact: true})).toBeVisible();
});

test("版本上传限单份，已选文件保留明确目标资料", async ({page, request}) => {
  const {headers, course} = await setup(page, request);
  const version = await upload(request, headers, course.id, "version-one.md");
  await page.goto(`/materials?course=${course.id}&document=${version.document_id}&version=${version.id}`);
  await expect(page.locator(".reading-paper")).toBeVisible();
  await page.getByLabel("上传方式").selectOption("version");
  await expect(page.getByLabel("选择课程文件")).not.toHaveAttribute("multiple", "");
  // Drag/drop must not silently keep only the first file.
  await page.locator(".material-upload").evaluate(element => {
    const data = new DataTransfer(); data.items.add(new File(["one"], "one.md")); data.items.add(new File(["two"], "two.md"));
    element.dispatchEvent(new DragEvent("drop", {bubbles: true, cancelable: true, dataTransfer: data}));
  });
  await expect(page.getByRole("alert")).toContainText("只选择一份文件");
  await page.getByLabel("选择课程文件").setInputFiles(file("version-two.md"));
  await expect(page.locator(".material-upload")).toContainText("新版本目标：version-one");
  await page.getByRole("button", {name: "保存为新版本", exact: true}).click();
  await expect(page.getByRole("region", {name: "资料上传队列"})).toContainText("已保存 1 / 1 份");
  await expect.poll(async () => (await (await request.get(base + `/documents/${version.document_id}/versions`, {headers})).json()).length).toBe(2);
});

for (const mode of ["qa", "report"] as const) test(`从历史原文进入${mode}：保留版本/片段、刷新恢复、零自动发送`, async ({page, request}) => {
  const {headers, course} = await setup(page, request);
  const old = await upload(request, headers, course.id, "history.md");
  await upload(request, headers, course.id, "latest.md", old.document_id);
  const chunks = await (await request.get(base + `/versions/${old.id}/chunks`, {headers})).json();
  let writes = 0;
  page.on("request", request => {if (request.method() === "POST" && /remote-queries|study-reports/.test(request.url())) writes++;});
  await page.route("**/api/v1/ai/provider", route => route.fulfill({json: {configured: true, model: "test-model"}}));
  // A prior request must not replace the reader's selected source.
  await page.addInitScript(id => localStorage.setItem(`hustudy_remote_query:${id}`, "unrelated-old-request"), course.id);
  await page.goto(`/materials?course=${course.id}&document=${old.document_id}&version=${old.id}`);
  await expect(page.locator(".reading-paper")).toBeVisible();
  await page.screenshot({path: test.info().outputPath("materials-desktop.png"), fullPage: true});
  if (mode === "qa") await page.getByRole("button", {name: "就此片段提问", exact: true}).first().click();
  else await page.getByRole("button", {name: "整理学习报告", exact: true}).click();
  await expect(page).toHaveURL(new RegExp(`version=${old.id}.*study=${mode}`));
  const context = page.getByRole("region", {name: "从资料阅读带入的来源"});
  await expect(context).toContainText("history · v1");
  const picked = page.locator('.ai-scope-options input:checked');
  await expect(picked).toHaveCount(1);
  await expect(page.locator(".ai-scope-picker").first()).toContainText("已选1份");
  if (mode === "qa") await expect(page.getByText("精确选择片段 · 已选1段", {exact: true})).toBeVisible();
  expect(writes).toBe(0);
  await page.reload(); await expect(context).toContainText("history · v1"); expect(writes).toBe(0);
  const endpoint = mode === "qa" ? "remote-queries/preview" : "study-reports/preview";
  await page.route(`**/api/v1/courses/${course.id}/${endpoint}`, async route => {
    expect(route.request().postDataJSON().version_ids).toEqual([old.id]);
    expect(route.request().postDataJSON().chunk_ids).toEqual(mode === "qa" ? [chunks[0].id] : []);
    await route.fulfill({status: 422, json: {error: {code: "TEST_ONLY", message: "已验证来源，没有调用模型"}}});
  });
  if (mode === "qa") await page.getByLabel("向课程提问", {exact: true}).fill("请解释进程。");
  await page.getByRole("button", {name: "预览将发送的片段", exact: true}).click();
  await expect(page.locator(".real-ai-workspace")).toContainText("已验证来源，没有调用模型");
  await page.setViewportSize({width: 390, height: 844});
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  await page.screenshot({path: test.info().outputPath("study-phone.png"), fullPage: true});
});

test("来源错配或撤权不能回退为全课程发送，允许重试加载", async ({page, request}) => {
  const {headers, course} = await setup(page, request);
  const version = await upload(request, headers, course.id, "valid.md");
  await page.goto(`/ai?course=${course.id}&document=${crypto.randomUUID()}&version=${version.id}&study=qa`);
  await expect(page.getByRole("button", {name: "重新加载来源与配置", exact: true})).toBeVisible();
  await expect(page.locator(".real-ai-workspace")).toContainText("资料与版本不一致");
  await expect(page.getByRole("button", {name: "预览将发送的片段", exact: true})).toHaveCount(0);
  expect((await request.delete(base + `/documents/${version.document_id}`, {headers})).status()).toBe(204);
  await page.goto(`/ai?course=${course.id}&document=${version.document_id}&version=${version.id}&study=qa`);
  await expect(page.getByRole("button", {name: "重新加载来源与配置", exact: true})).toBeVisible();
  await expect(page.getByRole("button", {name: "预览将发送的片段", exact: true})).toHaveCount(0);
  await page.goto(`/ai?course=${course.id}&study=qa`);
  await expect(page.getByText("资料学习地址无效", {exact: true})).toBeVisible();
  await expect(page.getByRole("button", {name: "预览将发送的片段", exact: true})).toHaveCount(0);
});

test("待上传离开可取消，上传中阻止导航且完成后恢复", async ({page, request}) => {
  const {course} = await setup(page, request);
  let release!: () => void;
  const gate = new Promise<void>(resolve => {release = resolve;});
  await page.route(`**/api/v1/courses/${course.id}/documents`, async route => {if (route.request().method() === "POST") await gate; await route.continue();});
  await page.goto(`/materials?course=${course.id}`);
  await page.getByLabel("选择课程文件").setInputFiles(file("guard.md"));
  page.once("dialog", dialog => dialog.dismiss());
  await page.locator(".sidebar").getByRole("button", {name: "课程总览", exact: true}).click();
  await expect(page).toHaveURL(/materials/);
  await expect(page.getByRole("region", {name: "资料上传队列"})).toContainText("guard.md");
  await page.getByRole("button", {name: "上传并开始整理", exact: true}).click();
  await expect(page.getByRole("button", {name: "正在上传…", exact: true})).toBeDisabled();
  await page.locator(".sidebar").getByRole("button", {name: "课程总览", exact: true}).click();
  await expect(page).toHaveURL(/materials/);
  release();
  await expect(page.getByRole("region", {name: "资料上传队列"})).toContainText("已保存 1 / 1 份");
  await expect(page.getByLabel("上传方式")).toBeEnabled();
  await page.locator(".sidebar").getByRole("button", {name: "课程总览", exact: true}).click();
  await expect(page).toHaveURL(/overview/);
});
