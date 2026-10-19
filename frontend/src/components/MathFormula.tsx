import {useMemo} from 'react';
import {renderFormula} from './mathRendering';
import 'katex/dist/katex.min.css';
import './mathFormula.css';

export function MathFormula({source, display = false}: {source: string; display?: boolean}) {
  const result = useMemo(() => renderFormula(source, display), [source, display]);
  return result.error
    ? <span className="math-error" title={result.error}><span>公式待修正</span><code>{source}</code></span>
    : <span className={display ? 'note-math note-math-block' : 'note-math'} dangerouslySetInnerHTML={{__html: result.html}}/>;
}
