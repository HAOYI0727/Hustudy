import {afterEach,beforeEach,expect,test,vi} from "vitest";
import {accentPresets,moduleNames,appearanceKey,appearanceTokens,applyAppearance,contrastRatio,defaultAppearance,mixColor,readAppearance,readableAccent,saveAppearance,validAppearance} from "../../src/features/appearance/preferences";
let store:Map<string,string>;
beforeEach(()=>{store=new Map();vi.stubGlobal("localStorage",{getItem:(key:string)=>store.get(key)??null,setItem:(key:string,value:string)=>store.set(key,value)});});
afterEach(()=>vi.unstubAllGlobals());
test("外观只保存已知设备偏好，无用户/资料/凭据",()=>{
 expect(readAppearance()).toEqual({value:defaultAppearance,error:""});
 const changed={...defaultAppearance,accent:"teal" as const,surface:"paper" as const,navigation:"dark" as const,density:"compact" as const,width:"focused" as const};
 expect(saveAppearance(changed)).toBe("");expect(readAppearance().value).toEqual(changed);
 expect(JSON.parse(store.get(appearanceKey)!)).toEqual({version:1,value:changed});expect(store.size).toBe(1);
});
test.each([null,[],{...defaultAppearance,accent:"external"},{...defaultAppearance,customColor:"url(https://unsafe)"},{...defaultAppearance,customColor:"#abc"},{...defaultAppearance,navigation:"system"},{...defaultAppearance,width:999},{...defaultAppearance,token:"secret"},{...defaultAppearance,density:"tiny"}])("未知/注入选项拒绝写入",value=>{
 expect(validAppearance(value)).toBe(false);expect(saveAppearance(value as never)).not.toBe("");expect(store.size).toBe(0);
});
test.each(["","bad json",'{"version":2,"value":{}}',JSON.stringify({version:1,value:defaultAppearance,extra:1}),"x".repeat(2049)])("损坏记录回默认，不自动覆盖",raw=>{
 store.set(appearanceKey,raw);expect(readAppearance().error).toContain("默认样式");expect(readAppearance().value).toEqual(defaultAppearance);expect(store.get(appearanceKey)).toBe(raw);
});
test("私密模式或配额失败明确报告，不假称已保存",()=>{
 saveAppearance(defaultAppearance);const original=store.get(appearanceKey);
 vi.stubGlobal("localStorage",{getItem:(key:string)=>store.get(key)??null,setItem:()=>{throw new Error("quota");}});
 expect(saveAppearance({...defaultAppearance,accent:"rose"})).toContain("未能保存");expect(store.get(appearanceKey)).toBe(original);
 vi.stubGlobal("localStorage",{getItem:()=>{throw new Error("private");}});expect(readAppearance().error).not.toBe("");
});
test("色彩计算采用线性相对亮度，混合边界可预测",()=>{
 expect(contrastRatio("#000000","#ffffff")).toBe(21);expect(contrastRatio("#ffffff","#ffffff")).toBe(1);expect(mixColor("#000000","#ffffff",.5)).toBe("#808080");
 expect(readableAccent("#000000","#ffffff")).toBe("#000000");
});
test("六种预设与极端自定色，主按钮/选中/链接小字达到计算对比度门槛",()=>{
 const colors=[...accentPresets.map(p=>p.color),"#ffffff","#ffff00","#00ff00","#00ffff","#ff00ff","#000000","#cccccc","#ffdddd"];
 for(const color of colors){const tokens=appearanceTokens({...defaultAppearance,accent:"custom",customColor:color});expect(tokens["--brand"]).toBe(color);expect(contrastRatio(tokens["--accent"],"#ffffff")).toBeGreaterThanOrEqual(4.5);expect(contrastRatio(tokens["--accent-ink"],tokens["--accent-soft"])).toBeGreaterThanOrEqual(4.5);}
});
test("三个明亮基调和两种导航均保持正文/导航计算可读，不改变状态色",()=>{
 for(const surface of ["cloud","paper","mist"] as const)for(const navigation of ["light","dark"] as const){const tokens=appearanceTokens({...defaultAppearance,surface,navigation});expect(contrastRatio(tokens["--ink"],tokens["--surface"])).toBeGreaterThanOrEqual(4.5);expect(contrastRatio(tokens["--muted"],tokens["--surface"])).toBeGreaterThanOrEqual(4.5);expect(contrastRatio(tokens["--nav-muted"],tokens["--nav-bg"])).toBeGreaterThanOrEqual(4.5);expect(Object.keys(tokens).some(k=>/danger|success|warning/.test(k))).toBe(false);}
});
test("应用只设置界面令牌/数据属性，不包含CSS/URL或变更内容",()=>{
 const props=new Map<string,string>(),dataset:Record<string,string>={};const setAttribute=vi.fn();
 vi.stubGlobal("document",{documentElement:{style:{setProperty:(key:string,value:string)=>props.set(key,value)},dataset},querySelector:()=>({setAttribute})});
 applyAppearance({...defaultAppearance,surface:"paper",navigation:"dark",width:"focused",density:"compact"});
 expect(dataset).toEqual({surface:"paper",navigation:"dark",width:"focused",density:"compact"});expect(props.get("--content-width")).toBe("1240px");expect(props.get("--panel-space")).toBe("18px");expect(setAttribute).toHaveBeenCalledWith("content",props.get("--canvas"));expect([...props.values()].some(v=>v.includes("url("))).toBe(false);
});

test("所有模块随同一主色联动，三基调/预设/极端自定色可读，旧偏好不迁移",()=>{
 for(const surface of ["cloud","paper","mist"] as const)for(const customColor of [...accentPresets.map(p=>p.color),"#ffffff","#000000","#ffff00","#00ff00"]){
  const tokens=appearanceTokens({...defaultAppearance,surface,accent:"custom",customColor});
  for(const name of moduleNames){
   expect(tokens[`--${name}-color`]).toBe(tokens["--accent"]);
   for(const role of ["wash","tint","line","ink"])expect(tokens[`--${name}-${role}`]).toBe(tokens[`--material-${role}`]);
   expect(contrastRatio(tokens[`--${name}-color`],"#ffffff")).toBeGreaterThanOrEqual(4.5);
   for(const role of ["wash","tint"])expect(contrastRatio(tokens[`--${name}-ink`],tokens[`--${name}-${role}`])).toBeGreaterThanOrEqual(4.5);
   expect(contrastRatio(tokens["--ink"],tokens[`--${name}-wash`])).toBeGreaterThanOrEqual(4.5);
  }
 }
 expect(Object.keys(defaultAppearance)).toHaveLength(6);
});
