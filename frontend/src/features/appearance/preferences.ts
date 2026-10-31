import {fontFamilies,fontPresets,type FontPreset} from "./typography";
export const accentPresets=[
  {id:"iris",name:"鸢尾紫",color:"#6255c5"},
  {id:"ocean",name:"远山蓝",color:"#2965bc"},
  {id:"teal",name:"松石青",color:"#157a78"},
  {id:"forest",name:"森林绿",color:"#42734b"},
  {id:"rose",name:"莓果粉",color:"#ad476e"},
  {id:"amber",name:"暖琥珀",color:"#a56522"},
] as const;
export const moduleNames=["material","ai","notes","exam","review"] as const;
export type Appearance={accent:typeof accentPresets[number]["id"]|"custom";customColor:string;surface:"cloud"|"paper"|"mist";navigation:"light"|"dark";density:"comfortable"|"compact";width:"wide"|"focused"};
export const defaultAppearance:Appearance={accent:"ocean",customColor:"#2965bc",surface:"cloud",navigation:"dark",density:"comfortable",width:"wide"};
export const appearanceKey="hustudy-appearance:v1";
export const FONT_SIZE_MIN=12;
export const FONT_SIZE_MAX=18;
export const FONT_SIZE_STEP=1;
export type TypographyPreference={font:FontPreset;size:number};
export const defaultTypography:TypographyPreference={font:"heiti",size:14};
export const typographyKey="hustudy-typography:v1";
const hex=(value:unknown):value is string=>typeof value==="string"&&/^#[\da-f]{6}$/i.test(value);
export function validAppearance(value:unknown):value is Appearance {
  if(!value||typeof value!=="object"||Array.isArray(value))return false;
  const row=value as Appearance;
  return Object.keys(row).length===6&&Object.keys(row).every(k=>Object.prototype.hasOwnProperty.call(defaultAppearance,k))&&
    [...accentPresets.map(p=>p.id),"custom"].includes(row.accent)&&hex(row.customColor)&&["cloud","paper","mist"].includes(row.surface)&&
    ["light","dark"].includes(row.navigation)&&["comfortable","compact"].includes(row.density)&&["wide","focused"].includes(row.width);
}
export function validTypography(value:unknown):value is TypographyPreference {
  if(!value||typeof value!=="object"||Array.isArray(value))return false;
  const row=value as Record<string,unknown>;
  return Object.keys(row).length===2&&Object.keys(row).every(k=>Object.prototype.hasOwnProperty.call(defaultTypography,k))&&
    Object.keys(fontPresets).includes(String(row.font))&&typeof row.size==="number"&&Number.isInteger(row.size)&&row.size>=FONT_SIZE_MIN&&row.size<=FONT_SIZE_MAX;
}
export function readAppearance():{value:Appearance;error:string} {
  try {
    const raw=localStorage.getItem(appearanceKey);
    if(raw===null)return {value:{...defaultAppearance},error:""};
    if(new Blob([raw]).size>2048)throw new Error("size");
    const stored=JSON.parse(raw) as {version:number;value:unknown};
    if(!stored||typeof stored!=="object"||Object.keys(stored).length!==2||stored.version!==1||!validAppearance(stored.value))throw new Error("invalid");
    return {value:stored.value,error:""};
  }catch{return {value:{...defaultAppearance},error:"本机外观偏好暂不可读，当前使用默认样式；原记录保留。"};}
}
export function readTypography():{value:TypographyPreference;error:string} {
  try{
    const raw=localStorage.getItem(typographyKey);
    if(raw===null)return {value:{...defaultTypography},error:""};
    if(new Blob([raw]).size>1024)throw new Error("size");
    const stored=JSON.parse(raw) as {version:number;value:unknown};
    if(!stored||typeof stored!=="object"||Object.keys(stored).length!==2||stored.version!==1)throw new Error("invalid");
    if(validTypography(stored.value))return {value:stored.value,error:""};
    // The first local-only release used descriptive aliases.  Migrate only
    // those known values; arbitrary records still fall back safely.
    const legacy=stored.value as {font?:unknown;scale?:unknown;size?:unknown};
    const fontMap:Record<string,FontPreset>={heiti:"heiti",songti:"songti",kaiti:"kaiti",balanced:"heiti",clear:"heiti",book:"songti"};
    const legacySizes:Record<string,number>={small:13,medium:14,large:15};
    const size=typeof legacy?.size==="number"?legacy.size:(typeof legacy?.scale==="string"?legacySizes[legacy.scale]:undefined);
    const mapped=typeof legacy?.font==="string"&&fontMap[legacy.font]&&typeof size==="number"
      ? {font:fontMap[legacy.font],size}:null;
    if(!mapped||!validTypography(mapped))throw new Error("invalid");
    return {value:mapped,error:""};
  }catch{return {value:{...defaultTypography},error:"本机字体偏好暂不可读，当前使用默认字体；原记录保留。"};}
}
export function saveAppearance(value:Appearance):string {
  if(!validAppearance(value))return "外观选项无效，未保存";
  try{localStorage.setItem(appearanceKey,JSON.stringify({version:1,value}));return "";}
  catch{return "已应用于本次使用，但未能保存到浏览器；请检查存储空间后重试。";}
}
export function saveTypography(value:TypographyPreference):string {
  if(!validTypography(value))return "字体选项无效，未保存";
  try{localStorage.setItem(typographyKey,JSON.stringify({version:1,value}));return "";}
  catch{return "已应用字体设置，但未能保存到浏览器；请检查存储空间后重试。";}
}
const rgb=(value:string)=>[1,3,5].map(start=>parseInt(value.slice(start,start+2),16));
const toHex=(values:number[])=>"#"+values.map(v=>Math.round(v).toString(16).padStart(2,"0")).join("");
export function mixColor(a:string,b:string,amount:number):string {const x=rgb(a),y=rgb(b);return toHex(x.map((v,i)=>v*(1-amount)+y[i]*amount));}
export function contrastRatio(a:string,b:string):number {
  const luminance=(color:string)=>rgb(color).map(v=>{const c=v/255;return c<=0.04045?c/12.92:((c+0.055)/1.055)**2.4;}).reduce((sum,v,i)=>sum+v*[0.2126,0.7152,0.0722][i],0);
  const x=luminance(a),y=luminance(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);
}
/** Darken for readable controls; the requested original remains available for decoration. */
export function readableAccent(color:string,background:string):string {
  for(let i=0;i<=100;i++){const candidate=mixColor(color,"#000000",i/100);if(contrastRatio(candidate,background)>=4.5)return candidate;}
  return "#000000";
}
export function appearanceTokens(value:Appearance):Record<string,string>{
  const brand=value.accent==="custom"?value.customColor:accentPresets.find(p=>p.id===value.accent)!.color;
  const accent=readableAccent(brand,"#ffffff"),soft=mixColor(accent,"#ffffff",.93),ink=readableAccent(accent,soft);
  const surfaces={cloud:{canvas:"#f5f6fa",panel:"#ffffff",subtle:"#f8f9fc",line:"#e4e7ef",ink:"#293248",muted:"#626d82"},paper:{canvas:"#f5f2eb",panel:"#fffefa",subtle:"#f9f6ef",line:"#e5dfd4",ink:"#34332e",muted:"#706b5f"},mist:{canvas:"#edf3f3",panel:"#fdffff",subtle:"#f3f8f8",line:"#dce6e7",ink:"#293b42",muted:"#5c7179"}}[value.surface];
  const dark=value.navigation==="dark";
  const modules:Record<string,string>={};
  // Keep domain aliases for existing tools, with one shared hue across the whole site.
  for(const name of moduleNames){
    const wash=mixColor(accent,surfaces.panel,.90);
    modules[`--${name}-color`]=accent;
    modules[`--${name}-wash`]=wash;
    modules[`--${name}-tint`]=mixColor(accent,surfaces.panel,.97);
    modules[`--${name}-line`]=mixColor(accent,surfaces.panel,.80);
    modules[`--${name}-ink`]=readableAccent(accent,wash);
  }
  return {
    ...modules,
    "--font-ui":fontFamilies.ui,"--font-reading":fontFamilies.reading,"--font-reflection":fontFamilies.reflection,
    "--brand":brand,"--accent":accent,"--primary":accent,"--accent-strong":mixColor(accent,"#000000",.16),"--accent-soft":soft,"--accent-ink":ink,"--accent-border":mixColor(accent,"#ffffff",.72),"--accent-glow":mixColor(accent,"#ffffff",.84),
    "--canvas":surfaces.canvas,"--surface":surfaces.panel,"--surface-muted":surfaces.subtle,"--line":surfaces.line,"--border":surfaces.line,"--ink":surfaces.ink,"--muted":surfaces.muted,"--text-muted":surfaces.muted,
    "--nav-bg":dark?"#1e293b":surfaces.panel,"--nav-ink":dark?"#d5deec":surfaces.ink,"--nav-muted":dark?"#b3bfd3":surfaces.muted,"--nav-line":dark?"#344157":surfaces.line,"--nav-hover":dark?"#2b3850":surfaces.subtle,"--nav-selected-bg":dark?accent:soft,"--nav-selected-ink":dark?"#ffffff":ink,
    "--content-width":value.width==="focused"?"1240px":"1560px","--panel-space":value.density==="compact"?"18px":"24px","--row-space":value.density==="compact"?"11px":"16px","--workspace-gap":value.density==="compact"?"16px":"24px","--shadow-card":"0 2px 8px #25334c03,0 10px 32px #25334c03",
  };
}
export function typographyTokens(value:TypographyPreference):Record<string,string>{
  const families=fontPresets[value.font].families;
  return {"--font-ui":families.ui,"--font-reading":families.reading,"--font-reflection":families.reflection,"--font-size-base":`${value.size}px`};
}
export function applyAppearance(value:Appearance):void {
  const root=document.documentElement;
  for(const [key,setting] of Object.entries(appearanceTokens(value)))root.style.setProperty(key,setting);
  root.dataset.surface=value.surface;root.dataset.navigation=value.navigation;root.dataset.density=value.density;root.dataset.width=value.width;
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content",appearanceTokens(value)["--canvas"]);
}
export function applyTypography(value:TypographyPreference):void {
  const root=document.documentElement;
  for(const [key,setting] of Object.entries(typographyTokens(value)))root.style.setProperty(key,setting);
  root.dataset.fontPreset=value.font;root.dataset.fontSize=String(value.size);
  root.style.fontSize=typographyTokens(value)["--font-size-base"];
}
