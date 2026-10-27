import {markdownFilename} from './exportNames';
import type {NoteDraft} from './noteRecovery';

/** Download the exact editor text locally, including unsaved and conflicted drafts. */
export function downloadDraft(draft: Pick<NoteDraft, 'title' | 'content'>, suffix = '草稿') {
  const url = URL.createObjectURL(new Blob([draft.content], {type: 'text/markdown;charset=utf-8'}));
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = markdownFilename(`${draft.title || '未命名笔记'}-${suffix}`);
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  // Keep the URL alive until the browser has consumed the click.
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
