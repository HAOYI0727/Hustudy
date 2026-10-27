import {describe,expect,it} from 'vitest';
import {changePackageSelection,freezePackageSelection,packageSelection,safePackageFilename,selectedPackageCount} from '../../src/features/packages/packageSelection';
import type {PackageItem} from '../../src/api/client';

const items:PackageItem[]=[{id:'a',category:'notes',title:'笔记A'},{id:'b',category:'notes',title:'笔记B'},{id:'f',category:'folders',title:'空目录'},{id:'p',category:'assets',title:'图片'}];
describe('标准包自选范围',()=>{
  it('全部选择保留空目录与未归档笔记，重复项去重',()=>{
    const selection=packageSelection([...items,items[0]]);
    expect(selection.notes).toEqual(['a','b']);expect(selection.folders).toEqual(['f']);expect(selectedPackageCount(selection)).toBe(4);
  });
  it('局部全选和取消不改变其他类别或筛选外的选择',()=>{
    const original=packageSelection(items);
    const next=changePackageSelection(original,[items[0]],false);
    expect(next.notes).toEqual(['b']);expect(next.assets).toEqual(['p']);expect(original.notes).toEqual(['a','b']);
    expect(changePackageSelection(next,[items[0]],true).notes).toEqual(['b','a']);
  });
  it('冻结请求按固定类别复制和排序，后续修改选择不会改变原请求',()=>{
    const original=packageSelection(items),frozen=freezePackageSelection(original);
    original.notes!.push('c');original.assets!.splice(0,1);
    expect(frozen.notes).toEqual(['a','b']);expect(frozen.assets).toEqual(['p']);expect(frozen.documents).toEqual([]);
    expect(freezePackageSelection({notes:['b','a','a']})).toEqual(freezePackageSelection({notes:['a','b']}));
  });
  it('下载文件名不携带目录、控制字符或无界长度',()=>{
    expect(safePackageFilename('../学习/资料:课.zip')).toBe('.._学习_资料_课.zip');
    expect(safePackageFilename('')).toBe('Hustudy标准数据包.zip');
    expect(safePackageFilename('我的笔记.ZIP')).toBe('我的笔记.zip');
    expect(safePackageFilename('CON.zip')).toBe('_CON.zip');
    expect(safePackageFilename('课本. .zip')).toBe('课本.zip');
    expect(Array.from(safePackageFilename('课'.repeat(300))).length).toBe(104);
  });
});
