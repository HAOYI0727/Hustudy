import {memo, useMemo, useState} from 'react';
import {renderFormula} from '../../components/mathRendering';
import {formulaRecipes, type FormulaRecipe} from './formulaCatalog';
import {formulaRecipeIcon, quickStructureRecipes, quickSymbolGroups, quickSymbolRecipes} from './formulaQuickCatalog';

const GraphicButton = memo(function GraphicButton({recipe, structure, onInsert}: {recipe: FormulaRecipe; structure?: boolean; onInsert: (recipe: FormulaRecipe) => void}) {
  const icon = structure ? formulaRecipeIcon(recipe) : recipe.snippet;
  const html = useMemo(() => renderFormula(icon, false).html, [icon]);
  return <button type="button" className={'secondary formula-graphic ' + (structure ? 'is-structure' : '')} aria-label={(structure ? '快捷结构 ' : '快捷符号 ') + recipe.label} title={recipe.label + (structure ? '：选中内容可嵌套' : '\n' + recipe.snippet.trim())} onClick={() => onInsert(recipe)}><span aria-hidden="true" dangerouslySetInnerHTML={{__html: html}}/></button>;
});
export function FormulaQuickTools({recent, onInsert}: {recent: string[]; onInsert: (recipe: FormulaRecipe) => void}) {
  const [group, setGroup] = useState('common');
  const entries = useMemo(() => quickSymbolRecipes(group), [group]);
  return <div className="formula-quick-tools">
    <div className="formula-quick-heading"><strong>图形符号</strong><small>点击插入 · 悬停查看名称与命令</small></div>
    <div className="formula-symbol-tabs" role="group" aria-label="快捷符号分类">{quickSymbolGroups.map(item => <button type="button" className="secondary" key={item.id} aria-pressed={group === item.id} aria-label={'符号分类 ' + item.name} onClick={() => setGroup(item.id)}><span aria-hidden="true">{item.icon}</span><small>{item.name}</small></button>)}</div>
    <div className="formula-symbol-ribbon" role="group" aria-label="快捷图形符号">{entries.map(recipe => <GraphicButton key={recipe.id} recipe={recipe} onInsert={onInsert}/>)}</div>
    <div className="formula-structure-ribbon" role="group" aria-label="快捷公式结构">{quickStructureRecipes.map(recipe => <GraphicButton key={recipe.id} recipe={recipe} structure onInsert={onInsert}/>)}</div>
    {!!recent.length && <details className="formula-recent"><summary>本次最近使用</summary><div className="formula-symbol-ribbon" role="group" aria-label="最近使用公式">{recent.map(id => {
      const recipe = formulaRecipes.find(item => item.id === id);
      return recipe ? <button type="button" className="secondary" key={id} onClick={() => onInsert(recipe)}>{recipe.label}</button> : null;
    })}</div></details>}
  </div>;
}
