import {expect, test, vi} from "vitest";
import {ApiError, type Job} from "../../src/api/client";
import {documentBatchError, documentFileError, uploadDocuments, type DocumentUpload} from "../../src/features/materials/uploadDocuments";

const files = (names = ["第一章.md", "第二章.pdf", "第三章.docx"]): DocumentUpload[] => names.map((name, index) => ({id: String(index), file: new File(["自制测试正文"], name), state: "waiting"}));
const job = (status = "QUEUED") => ({id: crypto.randomUUID(), status, resource_id: crypto.randomUUID()} as Job);

test("30MiB单文件含上限，超1字节拒绝；批量总量仍100MiB",()=>{
 const file=(size:number)=>({name:"source.pptx",size} as File);
 expect(documentFileError(file(30*1024*1024))).toBeUndefined();
 expect(documentFileError(file(30*1024*1024+1))).toContain("30 MiB");
 expect(documentBatchError(Array(3).fill(file(30*1024*1024)),false)).toBeUndefined();
 expect(documentBatchError(Array(4).fill(file(30*1024*1024)),false)).toContain("100 MiB");
});

test("限制单次文件数、版本单文件与整批大小", () => {
  expect(documentBatchError(files().map(row => row.file), false)).toBeUndefined();
  expect(documentBatchError(files().map(row => row.file), true)).toContain("只选择一份");
  expect(documentBatchError(Array(21).fill(files()[0].file), false)).toContain("1–20");
  expect(documentBatchError(Array(6).fill({size: 20 * 1024 * 1024} as File), false)).toContain("100 MiB");
});

test("串行上传，已存在和已保存分开显示，重试不重发成功项", async () => {
  const rows = files();
  let inflight = 0;
  const upload = vi.fn(async () => {expect(inflight++).toBe(0); await Promise.resolve(); inflight--; return job(upload.mock.calls.length === 1 ? "SUCCEEDED" : "QUEUED");});
  const changed = (row: DocumentUpload) => {rows[Number(row.id)] = row;};
  await uploadDocuments(rows, upload, changed);
  expect(rows.map(row => row.state)).toEqual(["existing", "saved", "saved"]);
  await uploadDocuments(rows, upload, changed);
  expect(upload).toHaveBeenCalledTimes(3);
});

test("无效文件本地拒绝，单文件业务错误不中断后续文件", async () => {
  const rows = files(["程序.exe", "坏文件.pdf", "有效.md"]);
  const upload = vi.fn().mockRejectedValueOnce(new ApiError("坏文件", 422)).mockResolvedValue(job());
  await uploadDocuments(rows, upload, row => {rows[Number(row.id)] = row;});
  expect(rows.map(row => row.state)).toEqual(["failed", "failed", "saved"]);
  expect(upload).toHaveBeenCalledTimes(2);
});

test.each([0, 401, 403, 409, 429, 500, 507])("错误 %i 暂停余项，只在显式重试后继续", async status => {
  const rows = files();
  const upload = vi.fn().mockResolvedValueOnce(job()).mockRejectedValueOnce(new ApiError("测试异常", status)).mockResolvedValue(job());
  const changed = (row: DocumentUpload) => {rows[Number(row.id)] = row;};
  await uploadDocuments(rows, upload, changed);
  expect(rows.map(row => row.state)).toEqual(["saved", "failed", "paused"]);
  expect(upload).toHaveBeenCalledTimes(2);
  if (status === 0 || status >= 500) expect(rows[1].message).toContain("结果未确认");
  await uploadDocuments(rows, upload, changed);
  expect(upload).toHaveBeenCalledTimes(4);
  expect(upload.mock.calls.map(call => call[0].name)).toEqual(["第一章.md", "第二章.pdf", "第二章.pdf", "第三章.docx"]);
});
