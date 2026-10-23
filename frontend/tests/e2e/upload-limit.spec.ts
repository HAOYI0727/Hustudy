import {test,expect} from "@playwright/test";
import {spawnSync} from "node:child_process";
import {fileURLToPath} from "node:url";

for(const kind of ["pptx","docx"])test(`超过旧20MiB的${kind}可上传并原格式阅读`,async({page,request})=>{
 test.setTimeout(90000);const base="http://127.0.0.1:8056/api/v1";
 const auth=await(await request.post(base+"/auth/register",{data:{username:"limit_office_"+crypto.randomUUID().replaceAll("-",""),password:"Test-password-2026"}})).json();const headers={Authorization:"Bearer "+auth.access_token};const course=await(await request.post(base+"/courses",{headers,data:{name:"大于旧20MiB边界"}})).json();
 const python=fileURLToPath(new URL(process.platform==="win32"?"../../../.venv/Scripts/python.exe":"../../../.venv/bin/python",import.meta.url));const original=fileURLToPath(new URL(`../../../fixtures/native_preview.${kind}`,import.meta.url));
 const generated=spawnSync(python,["-c","import sys,zipfile,io; out=io.BytesIO(); src=zipfile.ZipFile(sys.argv[1]); target=zipfile.ZipFile(out,'w'); [target.writestr(item,src.read(item.filename)) for item in src.infolist()]; target.writestr('__local_size_fixture.bin',b'x'*(21*1024*1024),compress_type=zipfile.ZIP_STORED); target.close(); src.close(); sys.stdout.buffer.write(out.getvalue())",original],{maxBuffer:35*1024*1024});expect(generated.status,generated.stderr.toString()).toBe(0);expect(generated.stdout.length).toBeGreaterThan(20*1024*1024);expect(generated.stdout.length).toBeLessThan(30*1024*1024);
 const uploaded=await request.post(base+`/courses/${course.id}/documents`,{headers,multipart:{file:{name:"large."+kind,mimeType:"application/octet-stream",buffer:generated.stdout}}});expect(uploaded.status()).toBe(202);const job=await uploaded.json();
 await expect.poll(async()=>(await(await request.get(base+`/versions/${job.resource_id}`,{headers})).json()).index_status,{timeout:30000}).toBe("SUCCEEDED");const version=await(await request.get(base+`/versions/${job.resource_id}`,{headers})).json();
 await page.addInitScript(auth=>{if(window===window.top){localStorage.setItem("hustudy_token",auth.access_token);localStorage.setItem("hustudy_user",auth.user.username);}},auth);
 await page.goto(`/materials?course=${course.id}&document=${version.document_id}&version=${version.id}`);if(kind==="docx")await page.getByRole("button",{name:"Word 预览",exact:true}).click();
 const label=kind==="pptx"?"PPT":"Word";const region=page.getByRole("region",{name:label+" 原格式阅读",exact:true});await expect(region).toHaveAttribute("aria-busy","false",{timeout:40000});await expect(region.getByRole("alert")).toHaveCount(0);await expect(region.locator("iframe")).toHaveAttribute("sandbox","allow-scripts");await expect(page.frameLocator(`iframe[title="${label}原文件预览"]`).getByText(kind==="pptx"?"Native PPTX Slide 1":"Native DOCX Page 1",{exact:true})).toBeVisible();
 await expect(page.getByText("资料处理服务已连接，上传后会继续解析与索引。",{exact:true})).toHaveCount(0);await expect(page.getByRole("button",{name:"刷新处理服务",exact:true})).toHaveCount(0);
});
