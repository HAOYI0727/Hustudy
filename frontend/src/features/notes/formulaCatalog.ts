/** Local authoring recipes; this is not a whitelist of supported TeX commands. */
export type FormulaRecipe = {id: string; category: string; label: string; snippet: string; help: string; display?: boolean};
export const formulaCategories = [
  ['basic', '基础结构', '选中内容再点结构，会将选区放进第一个参数；分数、根号、上下标可以继续嵌套。'],
  ['greek', '希腊字母', '命令区分大小写；变体与普通字母分别列出，拉丁字形的大写字母直接输入即可。'],
  ['relations', '关系比较', '约等、同余、比例、整除、次序与否定关系。'],
  ['sets', '集合与逻辑', '数集用黑板粗体，集合花括号须转义；量词、逻辑和关系可以自由组合。'],
  ['operators', '二元与大型运算', '大型运算的上下限均可编辑，独立公式有更宽裕的排版空间。'],
  ['delimiters', '括号与定界符', '自动括号随内容伸缩，左右必须成对；单边括号另一侧使用点号。'],
  ['arrows', '箭头与映射', '箭头可附上下说明；向量箭头还可在重音分类中找到。'],
  ['functions', '标准函数', '函数名使用正体命令，自定义名称用 operatorname，中文解释用 text。'],
  ['calculus', '求和积分与微积分', '编辑上下限、函数与变量；多重积分、偏导、极限及向量微分可以组合。'],
  ['linear', '向量矩阵与线代', '小矩阵可直接改参数；更多行列请使用“矩阵 / 多行”生成器。'],
  ['equations', '分段与多行', '双反斜杠换行，& 标记对齐点；不要再嵌入美元符号或 equation 外层。'],
  ['fonts', '字体样式', '黑板粗体用于数集，花体用于算子，boldsymbol 可使希腊字母加粗。'],
  ['accents', '重音与标记', '帽、横线、波浪、点和箭头修饰变量，上下括号还能添加说明。'],
  ['spacing', '间距与文本', '数学空格使用显式命令；text 内可以放中文，换行请用多行结构。'],
  ['decoration', '颜色盒子与取消线', '颜色填写名称或十六进制值，效果均在本地预览。'],
  ['examples', '常用完整公式', '从示例开始，修改参数或源码，再与其他结构组合。重复字母需分别修改。'],
] as const;
const recipes: FormulaRecipe[] = [];
function add(category: string, label: string, snippet: string, help = '', display = false) {
  recipes.push({id: category + '-' + label, category, label, snippet, help, display});
}
function symbols(category: string, entries: string) {
  for (const entry of entries.split(';')) {
    const [label, command] = entry.split('|');
    add(category, label, '\\' + command + ' ');
  }
}
function forms(category: string, entries: [string, string, string?][], display = false) {
  for (const [label, source, help] of entries) add(category, label, source, help, display);
}
forms('basic', [
  ['分数', String.raw`\frac{«分子:a»}{«分母:b»}`], ['根号', String.raw`\sqrt{«被开方数:x»}`],
  ['幂与下标', '{«底数:x»}_{«下标:i»}^{«指数:2»}'], ['上标', '{«底数:x»}^{«指数:n»}'], ['下标', '{«主体:x»}_{«下标:i»}'],
  ['高次根号', String.raw`\sqrt[«次数:n»]{«被开方数:x»}`],
  ['显示分数', String.raw`\dfrac{«分子:a»}{«分母:b»}`], ['紧凑分数', String.raw`\tfrac{«分子:a»}{«分母:b»}`],
  ['二项式', String.raw`\binom{«总数:n»}{«选取数:k»}`],
  ['连分数', String.raw`\cfrac{«分子:1»}{«整数:a»+\cfrac{«内分子:1»}{«内分母:b»}}`],
  ['导数标记', "«函数:f»'(«变量:x»)"], ['多阶导数标记', "«函数:f»^{(«阶数:n»)}(«变量:x»)"],
  ['上方标记', String.raw`\overset{«上方:*»}{«主体:x»}`], ['下方标记', String.raw`\underset{«下方:n\to\infty»}{«主体:\lim»}`],
]);
symbols('greek', '阿尔法 α|alpha;贝塔 β|beta;伽马 γ|gamma;德尔塔 δ|delta;艾普西龙 ε|epsilon;泽塔 ζ|zeta;伊塔 η|eta;西塔 θ|theta;约塔 ι|iota;卡帕 κ|kappa;兰姆达 λ|lambda;缪 μ|mu;纽 ν|nu;克西 ξ|xi;派 π|pi;柔 ρ|rho;西格玛 σ|sigma;陶 τ|tau;宇普西龙 υ|upsilon;斐 φ|phi;凯 χ|chi;普西 ψ|psi;欧米伽 ω|omega');
add('greek', '奥密克戎 ο', 'o');
symbols('greek', '变体 ε|varepsilon;变体 ϑ|vartheta;变体 ϰ|varkappa;变体 ϖ|varpi;变体 ϱ|varrho;末尾 ς|varsigma;变体 φ|varphi;双伽马 ϝ|digamma;大写 Γ|Gamma;大写 Δ|Delta;大写 Θ|Theta;大写 Λ|Lambda;大写 Ξ|Xi;大写 Π|Pi;大写 Σ|Sigma;大写 Υ|Upsilon;大写 Φ|Phi;大写 Ψ|Psi;大写 Ω|Omega;纳布拉 ∇|nabla');
for (const [label, tex] of [['等于 =', '='], ['小于 <', '<'], ['大于 >', '>']]) add('relations', label, tex);
symbols('relations', '不等于 ≠|ne;小于等于 ≤|le;大于等于 ≥|ge;斜线小于等于|leqslant;斜线大于等于|geqslant;约等于 ≈|approx;渐近相等|simeq;全等 ≅|cong;恒等或同余 ≡|equiv;相似 ∼|sim;正比 ∝|propto;远小于 ≪|ll;远大于 ≫|gg;垂直 ⊥|perp;平行 ∥|parallel;整除 ∣|mid;不整除 ∤|nmid;不小于|nless;不大于|ngtr;不小于等于|nleq;不大于等于|ngeq;不相似|nsim;不全等|ncong;不平行|nparallel;前于|prec;后于|succ;前于等于|preceq;后于等于|succeq;点等于|doteq;逼近|asymp');
forms('relations', [['模同余', String.raw`«左侧:a»\equiv «右侧:b»\pmod{«模数:m»}`], ['定义等于', String.raw`«左侧:f»\coloneqq «右侧:x^2»`], ['关系否定', String.raw`\not «关系:=»`]]);
symbols('sets', '属于 ∈|in;不属于 ∉|notin;包含元素 ∋|ni;空集 ∅|emptyset;空集变体|varnothing;真子集 ⊂|subset;真超集 ⊃|supset;子集 ⊆|subseteq;超集 ⊇|supseteq;非子集|nsubseteq;非超集|nsupseteq;严格子集|subsetneq;严格超集|supsetneq;并集 ∪|cup;交集 ∩|cap;差集|setminus;任意 ∀|forall;存在 ∃|exists;不存在 ∄|nexists;所以 ∴|therefore;因为 ∵|because;非 ¬|neg;且 ∧|land;或 ∨|lor;真 ⊤|top;假 ⊥|bot;推出 ⇒|Rightarrow;等价 ⇔|Leftrightarrow;可推出|vdash;满足|models');
forms('sets', [
  ['集合定义', String.raw`\left\{«元素:x»\mid «条件:x>0»\right\}`], ['笛卡尔积', String.raw`«集合A:A»\times «集合B:B»`],
  ['补集', '«集合:A»^{c}'], ['自然数集', String.raw`\mathbb{N}`], ['整数集', String.raw`\mathbb{Z}`],
  ['有理数集', String.raw`\mathbb{Q}`], ['实数集', String.raw`\mathbb{R}`], ['复数集', String.raw`\mathbb{C}`],
]);
for (const [label, tex] of [['加号 +', '+'], ['减号 −', '-']]) add('operators', label, tex);
symbols('operators', '正负 ±|pm;负正 ∓|mp;乘 ×|times;除 ÷|div;点乘 ⋅|cdot;星乘|ast;星号|star;圆点|circ;圆乘|odot;直和 ⊕|oplus;直积 ⊗|otimes;圆减|ominus;圆除|oslash;合并|uplus;方交|sqcap;方并|sqcup;菱形|diamond;实心点|bullet;无穷 ∞|infty;省略号 …|ldots;居中省略号 ⋯|cdots;竖省略号 ⋮|vdots;斜省略号 ⋱|ddots');
forms('operators', [
  ['求积', String.raw`\prod_{«下限:i=1»}^{«上限:n»} «项:x_i»`], ['余积', String.raw`\coprod_{«下限:i=1»}^{«上限:n»} «项:X_i»`],
  ['大并集', String.raw`\bigcup_{«下限:i=1»}^{«上限:n»} «集合:A_i»`], ['大交集', String.raw`\bigcap_{«下限:i=1»}^{«上限:n»} «集合:A_i»`],
  ['大型直和', String.raw`\bigoplus_{«下限:i=1»}^{«上限:n»} «项:V_i»`], ['大型张量积', String.raw`\bigotimes_{«下限:i=1»}^{«上限:n»} «项:V_i»`],
  ['强制上下限', String.raw`\sum\limits_{«下限:i=1»}^{«上限:n»} «项:a_i»`],
]);
forms('delimiters', [
  ['圆括号', String.raw`\left(«内容:x»\right)`], ['方括号', String.raw`\left[«内容:x»\right]`],
  ['花括号', String.raw`\left\{«内容:x»\right\}`], ['绝对值', String.raw`\left\lvert «内容:x»\right\rvert`],
  ['范数', String.raw`\left\lVert «内容:x»\right\rVert`], ['内积括号', String.raw`\left\langle «内容:u,v»\right\rangle`],
  ['向上取整', String.raw`\left\lceil «内容:x»\right\rceil`], ['向下取整', String.raw`\left\lfloor «内容:x»\right\rfloor`],
  ['求值竖线', String.raw`\left.«函数:F(x)»\right|_{«下限:a»}^{«上限:b»}`], ['单边左括号', String.raw`\left\{«内容:x+y»\right.`],
  ['固定小括号', String.raw`\bigl(«内容:x»\bigr)`], ['固定中括号', String.raw`\Bigl(«内容:x»\Bigr)`],
  ['固定大括号', String.raw`\biggl(«内容:x»\biggr)`], ['固定特大括号', String.raw`\Biggl(«内容:x»\Biggr)`],
]);
symbols('arrows', '右箭头 →|rightarrow;左箭头 ←|leftarrow;双向箭头 ↔|leftrightarrow;右双箭头 ⇒|Rightarrow;左双箭头 ⇐|Leftarrow;双向双箭头 ⇔|Leftrightarrow;长右箭头|longrightarrow;长左箭头|longleftarrow;长双向箭头|longleftrightarrow;长右双箭头|Longrightarrow;长左双箭头|Longleftarrow;长双向双箭头|Longleftrightarrow;映射 ↦|mapsto;长映射|longmapsto;上箭头 ↑|uparrow;下箭头 ↓|downarrow;上下箭头 ↕|updownarrow;上双箭头|Uparrow;下双箭头|Downarrow;上下双箭头|Updownarrow;东北箭头|nearrow;东南箭头|searrow;西南箭头|swarrow;西北箭头|nwarrow;钩右箭头|hookrightarrow;钩左箭头|hookleftarrow;平衡箭头|rightleftharpoons');
forms('arrows', [['带字右箭头', String.raw`\xrightarrow[«下方:b»]{«上方:a»}`], ['带字左箭头', String.raw`\xleftarrow[«下方:b»]{«上方:a»}`], ['带字等价箭头', String.raw`\xLeftrightarrow{«说明:\text{条件}»}`]]);
for (const command of ['sin','cos','tan','cot','sec','csc','arcsin','arccos','arctan','sinh','cosh','tanh','coth','ln','log','lg','exp','max','min','sup','inf','arg','det','gcd','ker','dim','hom','deg','Pr']) add('functions', command + ' 函数', '\\' + command + '{«参数:x»}');
forms('functions', [
  ['自定义函数', String.raw`\operatorname{«函数名:rank»}(«参数:A»)`], ['指定底数对数', String.raw`\log_{«底数:2»} «参数:x»`],
  ['最大值参数', String.raw`\underset{«变量:x»}{\operatorname{arg\,max}}\;«函数:f(x)»`],
  ['最小值参数', String.raw`\underset{«变量:x»}{\operatorname{arg\,min}}\;«函数:f(x)»`],
]);
forms('calculus', [
  ['求和', String.raw`\sum_{«下限:i=1»}^{«上限:n»} «项:x_i»`], ['积分', String.raw`\int_{«下限:a»}^{«上限:b»} «函数:f(x)»\,d«变量:x»`],
  ['不定积分', String.raw`\int «函数:f(x)»\,\mathrm{d}«变量:x»`],
  ['二重积分', String.raw`\iint_{«区域:D»} «函数:f(x,y)»\,\mathrm{d}x\,\mathrm{d}y`],
  ['三重积分', String.raw`\iiint_{«区域:V»} «函数:f(x,y,z)»\,\mathrm{d}V`],
  ['闭路积分', String.raw`\oint_{«路径:C»} «函数:\mathbf{F}»\cdot\mathrm{d}\mathbf{r}`],
  ['曲面积分', String.raw`\oiint_{«曲面:S»} «函数:\mathbf{F}»\cdot\mathrm{d}\mathbf{S}`],
  ['极限', String.raw`\lim_{«趋近:x\to 0»} «函数:\frac{\sin x}{x}»`],
  ['上极限', String.raw`\limsup_{«趋近:n\to\infty»} «序列:a_n»`], ['下极限', String.raw`\liminf_{«趋近:n\to\infty»} «序列:a_n»`],
  ['导数', String.raw`\frac{\mathrm{d}«函数:y»}{\mathrm{d}«变量:x»}`],
  ['高阶导数', String.raw`\frac{\mathrm{d}^{«阶数:n»}«函数:y»}{\mathrm{d}«变量:x»^{«分母阶数:n»}}`],
  ['偏导数', String.raw`\frac{\partial «函数:f»}{\partial «变量:x»}`],
  ['混合偏导', String.raw`\frac{\partial^2 «函数:f»}{\partial «变量一:x»\,\partial «变量二:y»}`],
  ['梯度', String.raw`\nabla «函数:f»`], ['散度', String.raw`\nabla\cdot «向量场:\mathbf{F}»`],
  ['旋度', String.raw`\nabla\times «向量场:\mathbf{F}»`], ['拉普拉斯算子', String.raw`\nabla^2 «函数:f»`], ['微分', String.raw`\mathrm{d}«变量:x»`],
]);
forms('linear', [
  ['向量', String.raw`\vec{«向量:v»}`], ['粗体向量', String.raw`\mathbf{«向量:v»}`],
  ['矩阵', String.raw`\begin{pmatrix} «一一:a» & «一二:b» \\ «二一:c» & «二二:d» \end{pmatrix}`],
  ['方括号矩阵', String.raw`\begin{bmatrix} «一一:a» & «一二:b» \\ «二一:c» & «二二:d» \end{bmatrix}`],
  ['行列式', String.raw`\begin{vmatrix} «一一:a» & «一二:b» \\ «二一:c» & «二二:d» \end{vmatrix}`],
  ['转置', '{«矩阵:A»}^{\\mathsf{T}}'], ['逆矩阵', '{«矩阵:A»}^{-1}'], ['共轭转置', String.raw`{«矩阵:A»}^{\dagger}`],
  ['矩阵迹', String.raw`\operatorname{tr}(«矩阵:A»)`], ['矩阵秩', String.raw`\operatorname{rank}(«矩阵:A»)`],
  ['内积', String.raw`\langle «向量一:u»,«向量二:v»\rangle`],
  ['点积', String.raw`«向量一:\mathbf{u}»\cdot «向量二:\mathbf{v}»`], ['叉积', String.raw`«向量一:\mathbf{u}»\times «向量二:\mathbf{v}»`],
  ['一般矩阵', String.raw`\begin{pmatrix} a_{11} & \cdots & a_{1n}\\ \vdots & \ddots & \vdots\\ a_{m1} & \cdots & a_{mn}\end{pmatrix}`],
]);
forms('equations', [
  ['分段函数', String.raw`f(x)=\begin{cases} «表达式一:x^2» & «条件一:x\ge 0» \\ «表达式二:-x» & «条件二:x<0» \end{cases}`],
  ['方程组', String.raw`\begin{cases} «方程一:x+y=1» \\ «方程二:x-y=0» \end{cases}`],
  ['对齐推导', String.raw`\begin{aligned} «左侧:a+b» &= «右侧:c» \\ &= «下一步:d+e» \end{aligned}`],
  ['居中多行', String.raw`\begin{gathered} «第一行:x+y=1» \\ «第二行:x-y=0» \end{gathered}`],
  ['数组对齐', String.raw`\begin{array}{rcl} «左侧:a» & = & «右侧:b+c» \\ «下一左侧:d» & = & «下一右侧:e» \end{array}`],
  ['带编号公式', String.raw`«公式:E=mc^2»\tag{«编号:1»}`],
], true);
for (const [label, command, value] of [
  ['正体','mathrm','ABC'], ['斜体','mathit','ABC'], ['粗体','mathbf','v'], ['粗斜体','boldsymbol','\\alpha'],
  ['黑板粗体','mathbb','R'], ['花体','mathcal','F'], ['手写花体','mathscr','L'], ['哥特体','mathfrak','g'],
  ['无衬线','mathsf','ABC'], ['等宽','mathtt','ABC'],
]) add('fonts', label, '\\' + command + '{«内容:' + value + '»}');
forms('fonts', [
  ['显示样式', String.raw`{\displaystyle «公式:\sum_{i=1}^n x_i»}`], ['行内样式', String.raw`{\textstyle «公式:\sum_{i=1}^n x_i»}`],
  ['脚标样式', String.raw`{\scriptstyle «公式:x+y»}`], ['小脚标样式', String.raw`{\scriptscriptstyle «公式:x+y»}`],
]);
for (const [label, command] of [
  ['帽子','hat'], ['宽帽子','widehat'], ['波浪','tilde'], ['宽波浪','widetilde'], ['短横线','bar'],
  ['上横线','overline'], ['下横线','underline'], ['一点','dot'], ['两点','ddot'], ['三点','dddot'],
  ['左向量箭头','overleftarrow'], ['右向量箭头','overrightarrow'], ['双向量箭头','overleftrightarrow'],
  ['短音符','breve'], ['倒帽子','check'], ['锐音符','acute'], ['重音符','grave'], ['圆圈','mathring'],
]) add('accents', label, '\\' + command + '{«内容:x»}');
forms('accents', [
  ['上括号说明', String.raw`\overbrace{«内容:a+b+c»}^{«说明:n\text{ 项}»}`],
  ['下括号说明', String.raw`\underbrace{«内容:a+b+c»}_{«说明:n\text{ 项}»}`],
  ['上方文字', String.raw`\overset{\text{«说明:定义»}}{«主体:=»}`],
  ['下方文字', String.raw`\underset{\text{«说明:条件»}}{«主体:\longrightarrow»}`],
]);
forms('spacing', [
  ['中文文本', String.raw`\text{«文字:当 x 大于零时»}`],
  ['细空格', String.raw`\,`], ['中空格', String.raw`\:`], ['宽空格', String.raw`\;`],
  ['一字空格', String.raw`\quad `], ['两字空格', String.raw`\qquad `], ['负细空格', String.raw`\!`], ['普通空格', String.raw`\ `],
  ['指定宽度', String.raw`\hspace{«宽度:1em»}`], ['隐藏占位', String.raw`\phantom{«内容:x^2»}`],
  ['水平占位', String.raw`\hphantom{«内容:x»}`], ['垂直占位', String.raw`\vphantom{«内容:\frac{a}{b}»}`],
  ['百分号', String.raw`\%`], ['美元符号', String.raw`\$`, '使用独立公式，避免Markdown将美元符号识别为公式边界。'],
]);
forms('decoration', [
  ['文字颜色', String.raw`\textcolor{«颜色:#2563eb»}{«内容:x+y»}`],
  ['背景颜色', String.raw`\colorbox{«颜色:#e0f2fe»}{$«内容:x+y»$}`, '使用独立公式，盒子内含数学定界符。'],
  ['彩色边框', String.raw`\fcolorbox{«边框颜色:blue»}{«背景颜色:white»}{$«内容:x+y»$}`, '使用独立公式。'],
  ['公式方框', String.raw`\boxed{«内容:x+y=1»}`],
  ['正向取消线', String.raw`\cancel{«内容:x»}`], ['反向取消线', String.raw`\bcancel{«内容:x»}`],
  ['交叉取消线', String.raw`\xcancel{«内容:x»}`], ['带圈文字', String.raw`\textcircled{«文字:A»}`],
]);
forms('examples', [
  ['一元二次方程求根', String.raw`x=\frac{-«系数b:b»\pm\sqrt{b^2-4«系数a:a»«系数c:c»}}{2a}`],
  ['勾股定理', String.raw`«边长a:a»^2+«边长b:b»^2=«斜边:c»^2`],
  ['欧拉公式', String.raw`e^{i«角度:\theta»}=\cos\theta+i\sin\theta`],
  ['泰勒展开', String.raw`f(x)=\sum_{n=0}^{\infty}\frac{f^{(n)}(«展开点:a»)}{n!}(x-a)^n`],
  ['梯度下降', String.raw`\theta_{t+1}=\theta_t-«学习率:\eta»\nabla_{\theta} «目标函数:L(\theta_t)»`],
  ['最大似然', String.raw`\hat{\theta}=\underset{\theta}{\operatorname{arg\,max}}\sum_{i=1}^{«样本数:n»}\log p(x_i\mid\theta)`],
  ['贝叶斯公式', String.raw`P(«事件A:A»\mid «事件B:B»)=\frac{P(B\mid A)P(A)}{P(B)}`],
  ['Softmax', String.raw`\operatorname{softmax}(«向量:z»)_i=\frac{e^{z_i}}{\sum_{j=1}^{«类别数:K»}e^{z_j}}`],
  ['交叉熵', String.raw`L=-\sum_{i=1}^{«类别数:K»}«标签:y_i»\log «预测概率:\hat y_i»`],
  ['高斯分布', String.raw`p(x)=\frac{1}{\sqrt{2\pi «方差:\sigma^2»}}\exp\left(-\frac{(x-«均值:\mu»)^2}{2\sigma^2}\right)`],
  ['矩阵乘法', String.raw`(AB)_{ij}=\sum_{k=1}^{«内维度:n»}a_{ik}b_{kj}`],
  ['期望', String.raw`\mathbb{E}[«变量:X»]=\sum_x xP(X=x)`],
  ['方差', String.raw`\operatorname{Var}(«变量:X»)=\mathbb{E}[X^2]-\mathbb{E}[X]^2`],
  ['协方差', String.raw`\operatorname{Cov}(«变量X:X»,«变量Y:Y»)=\mathbb{E}[(X-\mu_X)(Y-\mu_Y)]`],
  ['复数极坐标', String.raw`z=«模长:r»(\cos «角度:\theta»+i\sin\theta)`],
  ['柯西不等式', String.raw`\left(\sum_{i=1}^{«项数:n»}a_ib_i\right)^2\le\left(\sum_{i=1}^n a_i^2\right)\left(\sum_{i=1}^n b_i^2\right)`],
  ['二项式定理', String.raw`(«第一项:a»+«第二项:b»)^{n}=\sum_{k=0}^{n}\binom{n}{k}a^{n-k}b^k`],
  ['傅里叶变换', String.raw`\hat f(«频率:\omega»)=\int_{-\infty}^{+\infty}f(t)e^{-i\omega t}\,\mathrm{d}t`],
  ['带单位量', String.raw`«数值:9.8»\,\mathrm{«单位:m\,s^{-2}»}`],
], true);
export const formulaRecipes = recipes;
export const commonFormulaLabels = new Set(['分数', '根号', '幂与下标', '求和', '积分', '极限', '矩阵', '分段函数']);
const commandAliases: Record<string, string> = {ne: 'neq', le: 'leq', ge: 'geq', land: 'wedge', lor: 'vee', rightarrow: 'to', leftarrow: 'gets'};
export function searchFormulaRecipes(query: string, category: string) {
  const terms = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
  return formulaRecipes.filter(recipe => {
    if (!terms.length && category === 'common') return commonFormulaLabels.has(recipe.label);
    if (!terms.length && recipe.category !== category) return false;
    const aliases = recipe.snippet.replace(/\\([A-Za-z]+)/g, (_match, command: string) => commandAliases[command] ? '\\' + commandAliases[command] : '');
    const literalAlias = recipe.label === '小于 <' ? '\\lt' : recipe.label === '大于 >' ? '\\gt' : '';
    const haystack = [recipe.label, recipe.snippet, aliases, literalAlias, recipe.help, formulaCategories.find(c => c[0] === recipe.category)?.[1]].join(' ').toLowerCase();
    return terms.every(term => haystack.includes(term));
  });
}
