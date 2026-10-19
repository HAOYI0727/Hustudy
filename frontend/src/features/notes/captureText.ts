import type {NoteCapture} from '../../api/client';

/** Older captures decorated result.text with headings; parts retain the actual text. */
export function captureText(result: NoteCapture['result']): string {
  const parts = result.parts?.filter(part => part.text.trim());
  return parts?.length ? parts.map(part => part.text).join('\n\n') : result.text || '';
}
