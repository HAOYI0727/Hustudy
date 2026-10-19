import {describe, expect, it} from 'vitest';
import {recoverFormulaSlots, refreshFormulaSlots, formulaDomOffset, formulaSourceOffset} from '../../src/features/notes/formulaStructure';
import {replaceFormulaRange} from '../../src/features/notes/formulaAuthoring';
import {quickSymbolGroups, quickSymbolRecipes, quickStructureRecipes, formulaRecipeIcon} from '../../src/features/notes/formulaQuickCatalog';
import {renderFormula} from '../../src/components/mathRendering';
describe('图形公式输入', () => {
  it('所有快捷符号和空框结构图形均存在且可渲染', () => {
    for (const group of quickSymbolGroups) {
      const recipes = quickSymbolRecipes(group.id);
      expect(recipes.length, group.name).toBe(group.symbols.length);
      for (const recipe of recipes) expect(renderFormula(recipe.snippet, false).error, recipe.label).toBe('');
    }
    expect(quickStructureRecipes).toHaveLength(12);
    for (const recipe of quickStructureRecipes) expect(renderFormula(formulaRecipeIcon(recipe), false).error, recipe.label).toBe('');
  });
  it('重新打开嵌套根式分数、上下标能恢复精确偏移，编辑子字段保留其他内容', () => {
    const source = String.raw`L+\frac{\sqrt[3]{x+1}}{n_{i}^{2}}+R`;
    const slots = recoverFormulaSlots(source);
    expect(slots.map(slot => [slot.label, source.slice(slot.start, slot.end)])).toEqual([
      ['分子', String.raw`\sqrt[3]{x+1}`], ['根指数','3'], ['被开方数','x+1'], ['分母','n_{i}^{2}'], ['下标','i'], ['上标','2'],
    ]);
    const slot = slots.find(item => item.label === '被开方数')!;
    const changed = replaceFormulaRange({source, slots}, slot.start, slot.end, 'a+b+c');
    expect(changed.source).toBe(String.raw`L+\frac{\sqrt[3]{a+b+c}}{n_{i}^{2}}+R`);
    expect(changed.source.slice(changed.slots[0].start, changed.slots[0].end)).toBe(String.raw`\sqrt[3]{a+b+c}`);
    expect(changed.slots.find(s => s.label === '分母')).toEqual({...slots[3], start: slots[3].start + 2, end: slots[3].end + 2});
  });
  it('跳过注释、文本、环境元数据、未知宏，不改写不完整或宏定义输入', () => {
    for (const source of [String.raw`\frac{a}`, String.raw`\newcommand{\f}[1]{\frac{#1}{2}}\f{x}`, String.raw`\gdef\a{x}\frac{a}{b}`, String.raw`\foo{\frac{a}{b}}`, String.raw`\text{\frac{a}{b}}`]) expect(recoverFormulaSlots(source), source).toEqual([]);
    const source = '% \\frac{hidden}{hidden}\n\\frac{a\\{b\\}}{c}\n\\begin{matrix}x^{2}&y\\end{matrix}';
    expect(recoverFormulaSlots(source).map(s => source.slice(s.start, s.end))).toEqual(['a\\{b\\}', 'c', '2']);
    expect(recoverFormulaSlots('x'.repeat(4001))).toEqual([]);
    expect(recoverFormulaSlots('\\sqrt{' + '{'.repeat(50) + 'x' + '}'.repeat(51))).toEqual([]);
  });
  it('恢复字段去重且保留原模板标签，空值与多行偏移仍可编辑', () => {
    const source = '\\frac{\r\nx+y\r\n}{}';
    const slots = recoverFormulaSlots(source);
    expect(source.slice(slots[0].start, slots[0].end)).toBe('\r\nx+y\r\n');
    expect(slots[1].start).toBe(slots[1].end);
    const draft = {source, slots: [{...slots[0], label: '自定义分子'}]};
    const refreshed = refreshFormulaSlots(draft);
    expect(refreshed.slots).toHaveLength(2);
    expect(refreshed.slots[0].label).toBe('自定义分子');
    const changed = replaceFormulaRange(refreshed, slots[1].start, slots[1].end, 'n+1');
    expect(changed.source).toBe('\\frac{\r\nx+y\r\n}{n+1}');
    const value = 'a\r\nb\r\nc';
    expect(formulaSourceOffset(value, 4)).toBe(6);
    expect(formulaDomOffset(value, 6)).toBe(4);
    expect(formulaSourceOffset(value, 99)).toBe(value.length);
  });
});
