import {describe, expect, it} from 'vitest';
import {renderToStaticMarkup} from 'react-dom/server';
import {createElement} from 'react';
import {NotePreview} from '../../src/components/knowledge';
import {MAX_FORMULA_LENGTH, renderFormula} from '../../src/components/mathRendering';
import {formulaInsertionError, formulaSelection, insertFormula} from '../../src/features/notes/formulaEditing';

describe('formula editing and safe Markdown preview', () => {
  it('requires display mode for text dollars and multiline comments to avoid changing the formula on save', () => {
    for (const source of ['\\text{cost \\$5}', 'x+%comment\ny']) {
      expect(formulaInsertionError(source, false)).toContain('独立公式');
      expect(formulaInsertionError(source, true)).toBe('');
      const edit = insertFormula('', formulaSelection('', 0, 0), source, true);
      expect(formulaSelection(edit.text, edit.start, edit.end).source).toBe(source);
    }
    expect(formulaInsertionError('50\\%\n+x', false)).toBe('');
  });
  it('wraps a selection and updates an existing inline formula without touching the surrounding Chinese text', () => {
    const text = '前文 x^2 后文';
    const edit = insertFormula(text, formulaSelection(text, 3, 6), '\\frac{a}{b}', false);
    expect(edit.text).toBe('前文 $\\frac{a}{b}$ 后文');
    expect(edit.text.slice(edit.start, edit.end)).toBe('\\frac{a}{b}');
    const existing = formulaSelection(edit.text, edit.start + 2, edit.start + 2);
    expect(existing.existing).toBe(true);
    expect(existing.source).toBe('\\frac{a}{b}');
    expect(insertFormula(edit.text, existing, 'y^2', false).text).toBe('前文 $y^2$ 后文');
  });
  it('creates real display blocks and recognizes CRLF formulas for subsequent edits', () => {
    const text = '前文后文', selection = formulaSelection(text, 2, 2);
    const edit = insertFormula(text, selection, '\\sum_{i=1}^{n} x_i', true);
    expect(edit.text).toBe('前文\n\n$$\n\\sum_{i=1}^{n} x_i\n$$\n\n后文');
    expect(formulaSelection(edit.text, edit.start, edit.end).display).toBe(true);
    const windows = '前\r\n\r\n$$\r\nx^2\r\n$$\r\n\r\n后';
    const existing = formulaSelection(windows, windows.indexOf('x'), windows.indexOf('x'));
    expect(existing.existing).toBe(true);
    expect(insertFormula(windows, existing, 'z', false).text).toBe('前\r\n\r\n$z$\r\n\r\n后');
  });
  it('uses Markdown syntax boundaries instead of dollars inside code or escaped currency', () => {
    for (const body of ['`$x^2$`', '```tex\n$x^2$\n```', '    $x^2$']) {
      expect(formulaSelection(body, body.indexOf('x'), body.indexOf('x')).blocked).toBe(true);
    }
    const currency = '价格 \\$20，其他 \\$30';
    expect(formulaSelection(currency, 6, 6).existing).toBe(false);
    const body = '```tex\n$x$\n```\n\n正文 $y^2$';
    expect(formulaSelection(body, body.indexOf('y'), body.indexOf('y')).source).toBe('y^2');
  });
  it('renders inline and block formulas but leaves code literal and keeps raw HTML and external images blocked', () => {
    const html = renderToStaticMarkup(createElement(NotePreview, {token: 'test', notes: [], onNote: () => {}, content: '行内 $x^2$\n\n$$\n\\frac{1}{2}\n$$\n\n`$literal$`\n\n```tex\n$code$\n```\n\n<script>alert(1)</script>\n\n![图](https://invalid.test/x.png)'}));
    expect(html.match(/class="katex"/g)).toHaveLength(2);
    expect(html).toContain('class="math-block"');
    expect(html).toContain('<code>$literal$</code>');
    expect(html).toContain('$code$');
    expect(html).not.toContain('<script'); expect(html).not.toContain('<img');
  });
  it('rejects invalid or excessive formulas and prevents macro definitions from crossing formula boundaries', () => {
    expect(renderFormula('\\frac{a}', false).error).toContain('语法');
    expect(renderFormula('x'.repeat(MAX_FORMULA_LENGTH + 1), false).error).toContain('最多');
    expect(renderFormula('\\def\\loop{\\loop}\\loop', false).error).toContain('语法');
    expect(renderFormula('\\gdef\\private{X}\\private', false).error).toBe('');
    expect(renderFormula('\\private', false).error).toContain('语法');
    expect(renderFormula('\\text{数学公式}', false).error).toBe('');
  });
  it('does not emit external resources, active URLs or trusted HTML even from imported formulas', () => {
    for (const source of ['\\includegraphics{https://invalid.test/spy.png}', '\\href{javascript:alert(1)}{X}', '\\htmlStyle{position:fixed;inset:0}{X}']) {
      const html = renderFormula(source, false).html;
      expect(html).not.toMatch(/<(img|a|script)\b/);
      expect(html).not.toContain('style="position:fixed');
    }
  });
});
