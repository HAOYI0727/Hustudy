import {describe, expect, it} from 'vitest';
import {formulaRecipes, formulaCategories, searchFormulaRecipes} from '../../src/features/notes/formulaCatalog';
import {buildFormulaGrid, expandFormulaSnippet, formulaGridKinds, formulaGridColumnCount, formulaGuide, insertFormulaSnippet, updateFormulaSource} from '../../src/features/notes/formulaAuthoring';
import {renderFormula} from '../../src/components/mathRendering';

describe('公式工作区', () => {
  it('所有内置模板和速查示例都由实际渲染器成功渲染，分类与ID完整', () => {
    expect(new Set(formulaRecipes.map(r => r.id)).size).toBe(formulaRecipes.length);
    for (const category of formulaCategories) expect(formulaRecipes.some(r => r.category === category[0])).toBe(true);
    for (const recipe of formulaRecipes) {
      const {source, slots} = expandFormulaSnippet(recipe.snippet);
      expect(source, recipe.id).not.toMatch(/[«»]/);
      expect(renderFormula(source, !!recipe.display).error, recipe.id + ': ' + source).toBe('');
      for (const slot of slots) expect(source.slice(slot.start, slot.end), recipe.id).not.toBe('');
    }
    for (const item of formulaGuide) expect(renderFormula(item.example, true).error, item.title).toBe('');
  });
  it('按中文与命令跨分类查找，不因当前分类漏掉目标', () => {
    expect(searchFormulaRecipes('偏导', 'greek').some(r => r.label === '偏导数')).toBe(true);
    expect(searchFormulaRecipes('\\alpha', 'basic').some(r => r.label.includes('阿尔法'))).toBe(true);
    expect(searchFormulaRecipes('\\neq', 'basic').some(r => r.label === '不等于 ≠')).toBe(true);
    expect(searchFormulaRecipes('\\gets', 'basic').some(r => r.label === '左箭头 ←')).toBe(true);
    expect(searchFormulaRecipes('zzzzzz', 'common')).toEqual([]);
    expect(searchFormulaRecipes('', 'common')).toHaveLength(8);
  });
  it('选区嵌套保留分母、前后文，并在输入与删除后更新参数偏移', () => {
    const empty = {source: 'L+x+R', slots: []};
    const frac = insertFormulaSnippet(empty, 2, 3, String.raw`\frac{«分子:a»}{«分母:b»}`);
    expect(frac.draft.source).toBe(String.raw`L+\frac{x}{b}+R`);
    const root = insertFormulaSnippet(frac.draft, frac.start, frac.end, String.raw`\sqrt{«被开方数:x»}`);
    expect(root.draft.source).toBe(String.raw`L+\frac{\sqrt{x}}{b}+R`);
    const typed = updateFormulaSource(root.draft, root.draft.source.replace('sqrt{x}', 'sqrt{a+b}'));
    expect(typed.slots.map(s => [s.label, typed.source.slice(s.start, s.end)])).toEqual([['被开方数', 'a+b'], ['分母', 'b']]);
    const appended = updateFormulaSource(typed, typed.source.replace('sqrt{a+b}', 'sqrt{a+b+1}'));
    expect(appended.source.slice(appended.slots[0].start, appended.slots[0].end)).toBe('a+b+1');
    const cleared = updateFormulaSource(typed, 'z');
    expect(cleared.slots).toEqual([]);
    const power = formulaRecipes.find(recipe => recipe.label === '上标')!;
    const powered = insertFormulaSnippet({source: 'x^2', slots: []}, 0, 3, power.snippet);
    expect(powered.draft.source).toBe('{x^2}^{n}');
    expect(renderFormula(powered.draft.source, false).error).toBe('');
  });
  it('每种表格结构生成有效LaTeX，支持嵌套矩阵与增广列', () => {
    for (const [kind] of formulaGridKinds) {
      const count = formulaGridColumnCount(kind, 3);
      const grid = Array.from({length: 3}, () => Array.from({length: count}, () => 'x^2'));
      const result = buildFormulaGrid(kind, grid, 'cc|r');
      expect(result.error, kind).toBe('');
      expect(renderFormula(result.source, true).error, kind).toBe('');
    }
    const nested = buildFormulaGrid('pmatrix', [[String.raw`\begin{matrix}a&b\\c&d\end{matrix}`, 'x']]);
    expect(nested.error).toBe('');
    expect(renderFormula(nested.source, true).error).toBe('');
    expect(buildFormulaGrid('pmatrix', [['a&b']]).error).toContain('单元格');
    expect(buildFormulaGrid('array', [['x','y']], 'c|x').error).toContain('l、c');
    expect(buildFormulaGrid('pmatrix', [['']]).error).toContain('空单元格');
    expect(buildFormulaGrid('pmatrix', Array.from({length: 9}, () => ['x'])).error).toContain('1–8');
    expect(buildFormulaGrid('aligned', [['x']]).error).toContain('列数');
  });
});
