import {expect, it, vi} from "vitest";
import {ApiError, type Asset} from "../../../src/api/client";
import {uploadImages} from "../../../src/features/materials/uploadImages";

const file = (name: string, data = "png") => new File([data], name, {type: "image/png"});
const asset = (name: string) => ({id: name, name} as Asset);

it("uploads sequentially in selection order, preserves successes and retries only failures", async () => {
  const files = [file("A.png"), file("bad.png"), file("B.png")];
  let active = 0;
  const upload = vi.fn(async (next: File) => {
    expect(active++).toBe(0);
    await Promise.resolve(); active--;
    if (next.name === "bad.png") throw new ApiError("图片无法解码", 422);
    return asset(next.name);
  });
  const progress = vi.fn();
  const result = await uploadImages(files, upload, progress);
  expect(result.assets.map(item => item.name)).toEqual(["A.png", "B.png"]);
  expect(result.failures.map(item => item.file)).toEqual([files[1]]);
  expect(result.interrupted).toBe(false);
  expect(progress.mock.calls.map(([p]) => p.current)).toEqual([1, 2, 3]);
  const retry = vi.fn(async (next: File) => asset(next.name));
  await uploadImages(result.failures.map(item => item.file), retry, vi.fn());
  expect(retry).toHaveBeenCalledExactlyOnceWith(files[1]);
});

it.each([0, 401, 403, 429, 500, 507])("stops on status %s and leaves remaining files for explicit retry", async status => {
  const files = [file("A.png"), file("failed.png"), file("pending.png")];
  const upload = vi.fn().mockResolvedValueOnce(asset("A.png")).mockRejectedValue(new ApiError("请求失败", status));
  const result = await uploadImages(files, upload, vi.fn());
  expect(upload).toHaveBeenCalledTimes(2);
  expect(result.assets).toHaveLength(1);
  expect(result.failures.map(item => item.file)).toEqual(files.slice(1));
  expect(result.interrupted).toBe(true);
  expect(result.failures[1].message).toContain("尚未上传");
  if (status === 0 || status >= 500) expect(result.failures[0].message).toContain("先在图库核对");
});

it("validates the batch limit and individual files before sending them", async () => {
  const upload = vi.fn(async (next: File) => asset(next.name));
  await expect(uploadImages(Array.from({length: 21}, () => file("A.png")), upload, vi.fn())).rejects.toThrow("20");
  expect(upload).not.toHaveBeenCalled();
  const result = await uploadImages([
    file("empty.png", ""), new File(["text"], "readme.txt", {type: "text/plain"}),
    new File([new Uint8Array(10 * 1024 * 1024 + 1)], "large.png"), file("ok.png"),
  ], upload, vi.fn());
  expect(result.failures).toHaveLength(3);
  expect(result.assets.map(item => item.name)).toEqual(["ok.png"]);
  expect(upload).toHaveBeenCalledTimes(1);
});
