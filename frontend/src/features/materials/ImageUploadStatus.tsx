import type {ImageFailure, ImageProgress} from "./uploadImages";
import "./imageUpload.css";

export function ImageUploadStatus({progress, failures, summary, busy, retry, clear}: {
  progress: ImageProgress | null; failures: ImageFailure[]; summary: string; busy: boolean;
  retry: () => void; clear: () => void;
}) {
  return <div className="image-upload-status">
    {progress && <p role="status">正在上传 {progress.current} / {progress.total} · {progress.name}</p>}
    {!progress && summary && <p role="status">{summary}</p>}
    {!!failures.length && <div className="note-upload-error" role="alert">
      <ul>{failures.map((item, index) => <li key={index}><strong>{item.file.name}</strong>：{item.message}</li>)}</ul>
      <div className="image-upload-actions"><button type="button" className="secondary" disabled={busy} onClick={retry}>重试未完成图片（{failures.length}）</button><button type="button" className="text-button" disabled={busy} onClick={clear}>清除未完成列表</button></div>
    </div>}
  </div>;
}
