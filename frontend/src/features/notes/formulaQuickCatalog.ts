import {formulaRecipes, type FormulaRecipe} from './formulaCatalog';
export const quickSymbolGroups = [
  {id: 'common', name: '常用', icon: '± ∞', symbols: ['+', '-', '=', '\\pm', '\\times', '\\div', '\\cdot', '\\ne', '\\le', '\\ge', '\\approx', '\\infty', '\\alpha', '\\beta', '\\theta', '\\pi', '\\in', '\\cup', '\\cap', '\\rightarrow', '\\Rightarrow', '\\Leftrightarrow']},
  {id: 'greek', name: '希腊', icon: 'α β', symbols: ['\\alpha','\\beta','\\gamma','\\delta','\\epsilon','\\varepsilon','\\theta','\\lambda','\\mu','\\pi','\\rho','\\sigma','\\phi','\\varphi','\\omega','\\Gamma','\\Delta','\\Theta','\\Lambda','\\Sigma','\\Phi','\\Omega']},
  {id: 'relations', name: '关系', icon: '≤ ≈', symbols: ['=','<','>','\\ne','\\le','\\ge','\\approx','\\equiv','\\sim','\\cong','\\propto','\\ll','\\gg','\\perp','\\parallel','\\mid','\\nmid','\\prec','\\succ']},
  {id: 'sets', name: '集合逻辑', icon: '∈ ∀', symbols: ['\\in','\\notin','\\subset','\\subseteq','\\supset','\\supseteq','\\cup','\\cap','\\setminus','\\emptyset','\\forall','\\exists','\\nexists','\\neg','\\land','\\lor','\\therefore','\\because','\\mathbb{N}','\\mathbb{Z}','\\mathbb{R}','\\mathbb{C}']},
  {id: 'arrows', name: '箭头', icon: '→ ⇔', symbols: ['\\rightarrow','\\leftarrow','\\leftrightarrow','\\Rightarrow','\\Leftarrow','\\Leftrightarrow','\\longrightarrow','\\longleftarrow','\\Longrightarrow','\\Longleftrightarrow','\\mapsto','\\longmapsto','\\uparrow','\\downarrow','\\updownarrow','\\nearrow','\\searrow','\\hookrightarrow','\\rightleftharpoons']},
] as const;
export const quickStructureLabels = ['分数','根号','高次根号','上标','下标','幂与下标','求和','积分','圆括号','绝对值','向量','矩阵'] as const;
export function quickSymbolRecipes(group: string): FormulaRecipe[] {
  const symbols = quickSymbolGroups.find(item => item.id === group)?.symbols ?? quickSymbolGroups[0].symbols;
  return symbols.map(source => formulaRecipes.find(recipe => recipe.snippet.trim() === source)).filter((r): r is FormulaRecipe => !!r);
}
export const quickStructureRecipes = quickStructureLabels.map(label => formulaRecipes.find(recipe => recipe.label === label)!);
export function formulaRecipeIcon(recipe: FormulaRecipe): string {
  // Empty boxes describe the structure; the actual insertion still uses the existing editable recipe.
  return recipe.snippet.replace(/«[^:»]+:[^»]*»/g, '\\square');
}
