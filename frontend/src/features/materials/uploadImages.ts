import {ApiError, type Asset} from "../../api/client";

export const MAX_IMAGE_BATCH = 20;
export type ImageFailure = {file: File; message: string};
export type ImageProgress = {current: number; total: number; name: string};
export type ImageBatchResult = {assets: Asset[]; failures: ImageFailure[]; interrupted: boolean};

export function imageFileError(file: File): string | undefined {
  if (!/\.(png|jpe?g|webp)$/i.test(file.name) && !["image/png", "image/jpeg", "image/webp"].includes(file.type)) return "请选择 PNG、JPG 或 WebP 图片。";
  if (!file.size || file.size > 10 * 1024 * 1024) return "图片不能为空，且不能超过 10 MiB。";
}

// One request at a time; a failed response is never automatically replayed.
export async function uploadImages(files: File[], upload: (file: File) => Promise<Asset>, progress: (value: ImageProgress) => void): Promise<ImageBatchResult> {
  if (!files.length || files.length > MAX_IMAGE_BATCH) throw new Error(`每批请选择 1–${MAX_IMAGE_BATCH} 张图片。`);
  const result: ImageBatchResult = {assets: [], failures: [], interrupted: false};
  for (const [index, file] of files.entries()) {
    progress({current: index + 1, total: files.length, name: file.name});
    const invalid = imageFileError(file);
    if (invalid) { result.failures.push({file, message: invalid}); continue; }
    try { result.assets.push(await upload(file)); }
    catch (error) {
      const stop = !(error instanceof ApiError) || ![400, 413, 415, 422].includes(error.status);
      const uncertain = !(error instanceof ApiError) || error.status === 0 || error.status >= 500;
      const message = error instanceof Error ? error.message : "上传失败";
      result.failures.push({file, message: message + (uncertain ? "；结果未确认，请先在图库核对，避免重复上传。" : "")});
      if (stop) {
        result.interrupted = true;
        result.failures.push(...files.slice(index + 1).map(next => ({file: next, message: "队列已暂停，尚未上传。"})));
        break;
      }
    }
  }
  return result;
}

export const imageLabel = (file: File) => file.name.replace(/\.(png|jpe?g|webp)$/i, "").slice(0, 500);
