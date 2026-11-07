import {describe, expect, it} from 'vitest';
import {captureText} from '../../../src/features/notes/captureText';

describe('capture text compatibility', () => {
  it('uses source parts for legacy files without inserting location or AI formatting', () => {
    expect(captureText({text: '### 第1页\n\n旧包装', parts: [
      {location: '第1页', text: '# 原文里的井号', method: 'ocr'},
      {location: '1–2秒', text: ' 第二段 ', method: 'speech'},
      {location: '第3页', text: ' ', method: 'ocr'},
    ]})).toBe('# 原文里的井号\n\n 第二段 ');
  });
  it('preserves fallback text exactly when older records have no parts', () => {
    expect(captureText({text: '### 原始正文\r\n保留', parts: []})).toBe('### 原始正文\r\n保留');
    expect(captureText({})).toBe('');
  });
});
