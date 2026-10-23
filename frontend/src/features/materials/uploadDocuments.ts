import { ApiError, type Job } from "../../api/client";

export const MAX_DOCUMENT_BATCH = 20;
export const MAX_DOCUMENT_BYTES = 30 * 1024 * 1024;
export const MAX_BATCH_BYTES = 100 * 1024 * 1024;
export type UploadState = "waiting" | "uploading" | "saved" | "existing" | "failed" | "paused";
export type DocumentUpload = { id: string; file: File; state: UploadState; message?: string; job?: Job };

export function documentFileError(file: File) {
  if (!/\.(pptx|pdf|docx|md|markdown|txt)$/i.test(file.name)) return "请选择 PPTX、PDF、DOCX、Markdown 或 TXT 文件";
  if (!file.size || file.size > MAX_DOCUMENT_BYTES) return "文件不能为空，每份不能超过 30 MiB";
}

export function documentBatchError(files: File[], version: boolean) {
  if (!files.length || files.length > (version ? 1 : MAX_DOCUMENT_BATCH)) return version ? "添加新版本时请只选择一份文件" : "每批请选择 1–20 份资料";
  if (files.reduce((size, file) => size + file.size, 0) > MAX_BATCH_BYTES) return "整批文件不能超过 100 MiB，请分批导入";
}

// Only an explicit user action starts this loop. Saved rows are never replayed.
export async function uploadDocuments(rows: DocumentUpload[], upload: (file: File) => Promise<Job>, changed: (row: DocumentUpload) => void) {
  const completed: DocumentUpload[] = [];
  for (const [index, original] of rows.entries()) {
    if (["saved", "existing"].includes(original.state)) continue;
    const invalid = documentFileError(original.file);
    if (invalid) { changed({...original, state: "failed", message: invalid}); continue; }
    changed({...original, state: "uploading", message: undefined});
    try {
      const job = await upload(original.file);
      const row: DocumentUpload = {...original, job, state: job.status === "SUCCEEDED" ? "existing" : "saved", message: undefined};
      changed(row); completed.push(row);
    } catch (error) {
      const message = error instanceof Error ? error.message : "上传失败";
      const uncertain = !(error instanceof ApiError) || error.status === 0 || error.status >= 500;
      changed({...original, state: "failed", message: message + (uncertain ? "；保存结果未确认，请先核对资料库，再决定是否重试。" : "")});
      if (!(error instanceof ApiError) || ![400, 413, 415, 422].includes(error.status)) {
        rows.slice(index + 1).filter(row => !["saved", "existing"].includes(row.state)).forEach(row => changed({...row, state: "paused", message: "队列已暂停，尚未上传"}));
        break;
      }
    }
  }
  return completed;
}
