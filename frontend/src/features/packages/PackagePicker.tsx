import {useEffect, useMemo, useState} from 'react';
import type {PackageItem, PackageSelection} from '../../api/client';
import {changePackageSelection, PACKAGE_CATEGORIES, PACKAGE_SELECTION_LIMIT, packageSelection, selectedPackageCount} from './packageSelection';

export function PackagePicker({items,selection,onChange,disabled}:{items:PackageItem[];selection:PackageSelection;onChange:(selection:PackageSelection)=>void;disabled:boolean}) {
  const [query,setQuery]=useState(''),[category,setCategory]=useState(''),[page,setPage]=useState(0);
  const visible=useMemo(()=>items.filter(item=>(!category||item.category===category)&&`${item.title} ${item.detail||''}`.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase())),[items,query,category]);
  useEffect(()=>setPage(0),[items,query,category]);
  const pages=Math.max(1,Math.ceil(visible.length/40));
  return <section className="package-picker" aria-label="选择数据包内容">
    <div className="package-selection-heading"><h3>选择内容</h3><strong aria-live="polite">已选 {selectedPackageCount(selection)} / {items.length} 项</strong></div>
    {selectedPackageCount(selection)>PACKAGE_SELECTION_LIMIT&&<p role="alert">每次最多选择3000项。请取消部分选择后再预览，不会自动截断范围。</p>}
    <div className="package-actions"><button type="button" className="secondary" disabled={disabled} onClick={()=>onChange(packageSelection(items))}>全选可识别内容</button><button type="button" className="text-button" disabled={disabled} onClick={()=>onChange({})}>取消全部选择</button></div>
    <div className="package-categories" aria-label="按类型选择">{PACKAGE_CATEGORIES.map(({key,label})=>{
      const rows=items.filter(item=>item.category===key);if(!rows.length)return null;
      const count=rows.filter(item=>selection[key]?.includes(item.id)).length;
      return <label key={key}><input type="checkbox" aria-label={`选择全部${label}`} disabled={disabled} checked={count===rows.length} ref={element=>{if(element)element.indeterminate=count>0&&count<rows.length;}} onChange={event=>onChange(changePackageSelection(selection,rows,event.target.checked))}/><span>{label}<small>{count} / {rows.length}</small></span></label>;
    })}</div>
    <div className="package-search"><label>查找条目<input aria-label="查找数据包条目" maxLength={160} value={query} onChange={event=>setQuery(event.target.value)} placeholder="名称或目录" disabled={disabled}/></label><label>显示类型<select aria-label="数据包条目类型" value={category} onChange={event=>setCategory(event.target.value)} disabled={disabled}><option value="">全部类型</option>{PACKAGE_CATEGORIES.filter(({key})=>items.some(item=>item.category===key)).map(({key,label})=><option key={key} value={key}>{label}</option>)}</select></label></div>
    <div className="package-actions"><button type="button" className="text-button" disabled={disabled||!visible.length} onClick={()=>onChange(changePackageSelection(selection,visible,true))}>选择当前结果</button><button type="button" className="text-button" disabled={disabled||!visible.length} onClick={()=>onChange(changePackageSelection(selection,visible,false))}>取消当前结果</button><span className="hint">匹配 {visible.length} 项</span></div>
    <ul className="package-items" aria-label="数据包条目">{visible.slice(page*40,(page+1)*40).map(item=><li key={item.category+':'+item.id}><label><input type="checkbox" aria-label={`选择条目：${item.title}`} checked={selection[item.category]?.includes(item.id)||false} disabled={disabled} onChange={event=>onChange(changePackageSelection(selection,[item],event.target.checked))}/><span><strong>{item.title}</strong><small>{PACKAGE_CATEGORIES.find(row=>row.key===item.category)?.label}{item.detail?' · '+item.detail:''}</small></span></label></li>)}</ul>
    {!visible.length&&<p className="hint">{items.length?'没有匹配的条目。':'暂无可导入或导出的条目。'}</p>}
    {pages>1&&<nav className="package-pages" aria-label="数据包条目分页"><button type="button" className="secondary" disabled={disabled||page===0} onClick={()=>setPage(value=>value-1)}>上一页</button><span>{page+1} / {pages} 页</span><button type="button" className="secondary" disabled={disabled||page+1>=pages} onClick={()=>setPage(value=>value+1)}>下一页</button></nav>}
  </section>;
}
