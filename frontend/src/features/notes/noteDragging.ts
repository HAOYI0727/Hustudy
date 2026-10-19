import type {Note, NoteFolder} from '../../api/client';
import {insideFolder} from './organization';

export const NOTE_DRAG_TYPE = 'application/x-hustudy-note-move';
export type NoteDrag = {kind: 'notes'; notes: Pick<Note, 'id' | 'revision' | 'folder_id'>[]}
  | {kind: 'folder'; folder: NoteFolder};
export function canDropNotes(drag: NoteDrag | null, target: string | null, folders: NoteFolder[]) {
  if (!drag || (target && !folders.some(folder => folder.id === target))) return false;
  if (drag.kind === 'notes') return drag.notes.length > 0 && drag.notes.length <= 200 && drag.notes.some(note => (note.folder_id ?? null) !== target);
  return drag.folder.parent_id !== target && (!target || !insideFolder(folders, target, drag.folder.id));
}
