import {expect,test} from "vitest";
import {moveSelectOption,matchSelectOption,selectMenuPosition,type SelectMenuOption} from "../../src/components/selectMenu";
const options:SelectMenuOption[]=[{index:0,value:"a",label:"Alpha",disabled:false,group:""},{index:1,value:"b",label:"Beta",disabled:true,group:""},{index:2,value:"c",label:"Charlie",disabled:false,group:"课程"},{index:3,value:"d",label:"Alpine",disabled:false,group:"课程"}];
test("键盘循环跳过禁用项，Home/End及全部禁用不会误选",()=>{
 expect(moveSelectOption(options,0,1)).toBe(2);expect(moveSelectOption(options,2,-1)).toBe(0);expect(moveSelectOption(options,3,1)).toBe(0);expect(moveSelectOption(options,0,-1)).toBe(3);expect(moveSelectOption(options,-1,1)).toBe(0);
 expect(moveSelectOption(options.map(o=>({...o,disabled:true})),0,1)).toBe(-1);expect(moveSelectOption([],0,1)).toBe(-1);
});
test("文字定位从当前项之后查找、忽略大小写/禁用并保持原顺序",()=>{
 expect(matchSelectOption(options,"al",0)).toBe(3);expect(matchSelectOption(options,"AL",3)).toBe(0);expect(matchSelectOption(options,"be",0)).toBe(-1);expect(matchSelectOption(options,"missing",0)).toBe(-1);expect(matchSelectOption([],"a",-1)).toBe(-1);
});
test("下拉按视口约束宽度、贴右边时回收、底部自动向上展开",()=>{
 const below=selectMenuPosition({left:100,top:80,bottom:116,width:280},{width:1200,height:800},30);expect(below).toMatchObject({left:100,top:122,width:280,maxHeight:360,up:false});
 const above=selectMenuPosition({left:1100,top:680,bottom:720,width:250},{width:1200,height:760},30);expect(above.up).toBe(true);expect(above.left+above.width).toBeLessThanOrEqual(1188);expect(above.top+above.maxHeight).toBeLessThan(680);
 const narrow=selectMenuPosition({left:4,top:50,bottom:90,width:500},{width:320,height:740},8);expect(narrow.width).toBe(296);expect(narrow.left).toBe(12);
 const short=selectMenuPosition({left:100,top:80,bottom:116,width:280},{width:1200,height:800},4);expect(short.maxHeight).toBeGreaterThanOrEqual(250);
});
test("矮视口返回真实剩余高度，调用者可使用原生降级而非溢出",()=>{
 const small=selectMenuPosition({left:10,top:40,bottom:80,width:150},{width:800,height:160},10);expect(small.maxHeight).toBeLessThan(100);expect(small.maxHeight).toBeGreaterThanOrEqual(0);
});
