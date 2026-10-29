import {useEffect,useState} from 'react';
import type {PackageSelection,PackageSelectionPreview} from '../../api/client';
import {PACKAGE_CATEGORIES} from './packageSelection';

export function PackageFinalItems({preview,original}:{preview:PackageSelectionPreview;original:PackageSelection}) {
  const [page,setPage]=useState(0);
  useEffect(()=>setPage(0),[preview]);
  const items=preview.items.filter(item=>preview.selection[item.category]?.includes(item.id));
  const pages=Math.max(1,Math.ceil(items.length/40)),current=Math.min(page,pages-1);
  return <details><summary>查看最终条目（{items.length} 项）</summary>
    <ul className="package-final-items">{items.slice(current*40,(current+1)*40).map(item=><li key={item.category+':'+item.id}>{item.title}<small> · {PACKAGE_CATEGORIES.find(category=>category.key===item.category)?.label}{!original[item.category]?.includes(item.id)?' · 关联依赖':''}</small></li>)}</ul>
    {pages>1&&<nav className="package-pages" aria-label="最终条目分页"><button type="button" className="secondary" disabled={current===0} onClick={()=>setPage(value=>value-1)}>上一页</button><span>{current+1} / {pages} 页</span><button type="button" className="secondary" disabled={current+1>=pages} onClick={()=>setPage(value=>value+1)}>下一页</button></nav>}
  </details>;
}
