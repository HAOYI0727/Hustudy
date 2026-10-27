import type {PackageCategory, PackageItem, PackageSelection} from '../../api/client';

export const PACKAGE_CATEGORIES: {key:PackageCategory;label:string}[] = [
  {key:'notes',label:'笔记'},{key:'folders',label:'笔记文件夹'},{key:'assets',label:'图片'},
  {key:'documents',label:'课程资料'},{key:'topics',label:'知识标签'},{key:'past_papers',label:'题库'},
  {key:'exam_papers',label:'练习与作答记录'},{key:'ai_results',label:'已完成AI结果'},
  {key:'reports',label:'学习报告'},{key:'blueprints',label:'组卷蓝图'},
];
export const PACKAGE_MAX_BYTES=100*1024*1024;
export const PACKAGE_SELECTION_LIMIT=3000;
export function packageSelection(items:readonly PackageItem[]):PackageSelection {
  const selected:PackageSelection={};
  for(const item of items){const ids=selected[item.category]||(selected[item.category]=[]);if(!ids.includes(item.id))ids.push(item.id);}
  return selected;
}
export function selectedPackageCount(selection:PackageSelection):number {
  return Object.values(selection).reduce((count,ids)=>count+(ids?.length||0),0);
}
export function changePackageSelection(selection:PackageSelection,items:readonly PackageItem[],checked:boolean):PackageSelection {
  const next:PackageSelection={};
  for(const {key} of PACKAGE_CATEGORIES)next[key]=[...(selection[key]||[])];
  for(const item of items){const ids=next[item.category]||[];next[item.category]=checked?[...new Set([...ids,item.id])]:ids.filter(id=>id!==item.id);}
  return next;
}
export function freezePackageSelection(selection:PackageSelection):PackageSelection {
  return Object.fromEntries(PACKAGE_CATEGORIES.map(({key})=>[key,[...new Set(selection[key]||[])].sort()]));
}
export function safePackageFilename(filename:string):string {
  const clean=filename.normalize('NFC').replace(/[\u0000-\u001f<>:"/\\|?*]/g,'_').replace(/[. ]+$/g,'').trim();
  let title=Array.from(clean.replace(/\.zip$/i,'')).slice(0,100).join('').replace(/[. ]+$/g,'')||'Hustudy标准数据包';
  if(/^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(title))title='_'+title;
  return title+'.zip';
}
