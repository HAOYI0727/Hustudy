import {createContext,useContext,useEffect,useLayoutEffect,useMemo,useState,type ReactNode} from "react";
import {ConfigProvider} from "antd";
import zhCN from "antd/locale/zh_CN";
import {appearanceKey,appearanceTokens,applyAppearance,readAppearance,saveAppearance,validAppearance,type Appearance} from "./preferences";
import {fontFamilies} from "./typography";
type Context={value:Appearance;error:string;update:(value:Appearance)=>void;retry:()=>void};
const AppearanceContext=createContext<Context|null>(null);
export function useAppearance(){const value=useContext(AppearanceContext);if(!value)throw new Error("AppearanceProvider missing");return value;}
export function AppearanceProvider({children}:{children:ReactNode}){
  const [initial]=useState(readAppearance),[value,setValue]=useState(initial.value),[error,setError]=useState(initial.error);
  useLayoutEffect(()=>applyAppearance(value),[value]);
  useEffect(()=>{
    const storage=(event:StorageEvent)=>{if(event.key!==appearanceKey&&event.key!==null)return;const next=readAppearance();setError(next.error);if(!next.error)setValue(next.value);};
    window.addEventListener("storage",storage);return()=>window.removeEventListener("storage",storage);
  },[]);
  const update=(next:Appearance)=>{if(!validAppearance(next)){setError("外观选项无效");return;}setValue(next);setError(saveAppearance(next));};
  const tokens=appearanceTokens(value);
  const theme=useMemo(()=>({token:{colorPrimary:tokens["--accent"],colorText:tokens["--ink"],colorTextSecondary:tokens["--muted"],colorBgContainer:tokens["--surface"],colorBorder:tokens["--line"],borderRadius:10,fontSize:14,controlHeight:38,fontFamily:fontFamilies.ui},components:{Modal:{contentBg:tokens["--surface"]}}}),[value]);
  return <AppearanceContext.Provider value={{value,error,update,retry:()=>setError(saveAppearance(value))}}><ConfigProvider locale={zhCN} theme={theme}>{children}</ConfigProvider></AppearanceContext.Provider>;
}
