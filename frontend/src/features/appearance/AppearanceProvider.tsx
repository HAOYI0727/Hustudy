import {createContext,useContext,useEffect,useLayoutEffect,useMemo,useState,type ReactNode} from "react";
import {ConfigProvider} from "antd";
import zhCN from "antd/locale/zh_CN";
import {appearanceKey,appearanceTokens,applyAppearance,applyTypography,readAppearance,readTypography,saveAppearance,saveTypography,typographyKey,typographyTokens,validAppearance,validTypography,type Appearance,type TypographyPreference} from "./preferences";
type Context={value:Appearance;error:string;update:(value:Appearance)=>void;retry:()=>void;typography:TypographyPreference;typographyError:string;updateTypography:(value:TypographyPreference)=>void;retryTypography:()=>void};
const AppearanceContext=createContext<Context|null>(null);
export function useAppearance(){const value=useContext(AppearanceContext);if(!value)throw new Error("AppearanceProvider missing");return value;}
export function AppearanceProvider({children}:{children:ReactNode}){
  const [initial]=useState(readAppearance),[value,setValue]=useState(initial.value),[error,setError]=useState(initial.error);
  const [initialTypography]=useState(readTypography),[typography,setTypography]=useState(initialTypography.value),[typographyError,setTypographyError]=useState(initialTypography.error);
  useLayoutEffect(()=>{applyAppearance(value);applyTypography(typography)},[value,typography]);
  useEffect(()=>{
    const storage=(event:StorageEvent)=>{
      if(event.key===appearanceKey||event.key===null){const next=readAppearance();setError(next.error);if(!next.error)setValue(next.value);}
      if(event.key===typographyKey||event.key===null){const next=readTypography();setTypographyError(next.error);if(!next.error)setTypography(next.value);}
    };
    window.addEventListener("storage",storage);return()=>window.removeEventListener("storage",storage);
  },[]);
  const update=(next:Appearance)=>{if(!validAppearance(next)){setError("外观选项无效");return;}setValue(next);setError(saveAppearance(next));};
  const updateTypography=(next:TypographyPreference)=>{if(!validTypography(next)){setTypographyError("字体选项无效");return;}setTypography(next);setTypographyError(saveTypography(next));};
  const tokens=appearanceTokens(value);
  const typeTokens=typographyTokens(typography);
  const theme=useMemo(()=>({token:{colorPrimary:tokens["--accent"],colorText:tokens["--ink"],colorTextSecondary:tokens["--muted"],colorBgContainer:tokens["--surface"],colorBorder:tokens["--line"],borderRadius:10,fontSize:Number.parseInt(typeTokens["--font-size-base"],10),controlHeight:38,fontFamily:typeTokens["--font-ui"]},components:{Modal:{contentBg:tokens["--surface"]}}}),[value,typography]);
  return <AppearanceContext.Provider value={{value,error,update,retry:()=>setError(saveAppearance(value)),typography,typographyError,updateTypography,retryTypography:()=>setTypographyError(saveTypography(typography))}}><ConfigProvider locale={zhCN} theme={theme}>{children}</ConfigProvider></AppearanceContext.Provider>;
}
