import {describe, expect, it, vi} from 'vitest';
import {readAutoSavePreference, writeAutoSavePreference} from '../../src/features/notes/notePreferences';

const first = '10000000-0000-4000-8000-000000000001';
const second = '10000000-0000-4000-8000-000000000002';
function memory() {
  const values = new Map<string, string>();
  return {values, getItem: (key: string) => values.get(key) ?? null, setItem: (key: string, value: string) => {values.set(key, value);}};
}

describe('自动保存个人偏好', () => {
  it('新账户默认关闭，明确开启和关闭均可读取', () => {
    const storage = memory();
    expect(readAutoSavePreference(first, storage)).toBe(false);
    expect(writeAutoSavePreference(first, true, storage)).toBe(true);
    expect(readAutoSavePreference(first, storage)).toBe(true);
    expect(writeAutoSavePreference(first, false, storage)).toBe(true);
    expect(readAutoSavePreference(first, storage)).toBe(false);
  });

  it('同一设备上的账户偏好互不影响', () => {
    const storage = memory();
    writeAutoSavePreference(first, true, storage);
    expect(readAutoSavePreference(second, storage)).toBe(false);
    writeAutoSavePreference(second, false, storage);
    expect(readAutoSavePreference(first, storage)).toBe(true);
    expect(readAutoSavePreference(second, storage)).toBe(false);
    writeAutoSavePreference(second, true, storage);
    writeAutoSavePreference(first, false, storage);
    expect(readAutoSavePreference(second, storage)).toBe(true);
  });

  it('损坏或近似的存储值不能隐式开启自动保存', () => {
    const storage = memory();
    const key = 'hustudy:note-autosave:v1:' + first;
    for (const value of ['', 'true', '1', 'Enabled', ' enabled ', '{"enabled":true}', 'null']) {
      storage.values.set(key, value);
      expect(readAutoSavePreference(first, storage), value).toBe(false);
    }
    storage.values.set(key, 'enabled');
    expect(readAutoSavePreference(first, storage)).toBe(true);
  });

  it('缺失账户或存储禁用时不抛错，不误称偏好已保存', () => {
    const unavailable = {getItem: vi.fn(() => {throw new Error('storage disabled');}), setItem: vi.fn(() => {throw new Error('quota exceeded');})};
    expect(readAutoSavePreference('', unavailable)).toBe(false);
    expect(writeAutoSavePreference('', true, unavailable)).toBe(false);
    expect(unavailable.getItem).not.toHaveBeenCalled();
    expect(unavailable.setItem).not.toHaveBeenCalled();
    expect(readAutoSavePreference(first, unavailable)).toBe(false);
    expect(writeAutoSavePreference(first, true, unavailable)).toBe(false);
  });
});
