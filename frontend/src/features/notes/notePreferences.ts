const prefix = 'hustudy:note-autosave:v1:';

export function readAutoSavePreference(userId: string, storage?: Pick<Storage, 'getItem'>): boolean {
  if (!userId) return false;
  try {return (storage ?? window.localStorage).getItem(prefix + userId) === 'enabled';}
  catch {return false;}
}

export function writeAutoSavePreference(userId: string, enabled: boolean, storage?: Pick<Storage, 'setItem'>): boolean {
  if (!userId) return false;
  try {(storage ?? window.localStorage).setItem(prefix + userId, enabled ? 'enabled' : 'disabled'); return true;}
  catch {return false;}
}
