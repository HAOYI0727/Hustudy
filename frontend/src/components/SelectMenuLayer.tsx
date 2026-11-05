import {useEffect,useLayoutEffect,useRef,useState} from "react";
import {createPortal} from "react-dom";
import {Icon} from "./Icon";
import {matchSelectOption,moveSelectOption,readSelectOptions,selectMenuPosition,type SelectMenuOption} from "./selectMenu";
type Menu={select:HTMLSelectElement;options:SelectMenuOption[];active:number;label:string;attrs:Map<string,string|null>;scrolls:Map<EventTarget,string>;position:ReturnType<typeof selectMenuPosition>};
const id="hustudy-select-menu";
const attributes=["aria-expanded","aria-controls","aria-activedescendant","data-select-open"];
/** Progressive decoration of the existing select: it remains the sole form/value owner. */
export default function SelectMenuLayer(){
  const [menu,setMenu]=useState<Menu|null>(null),current=useRef<Menu|null>(null),popover=useRef<HTMLDivElement>(null);
  const setActive=(index:number)=>{const value=current.current;if(!value||index<0)return;const next={...value,active:index};current.current=next;setMenu(next);};
  const close=(focus=false)=>{
    const previous=current.current;current.current=null;
    if(popover.current?.matches(":popover-open"))popover.current.hidePopover();
    if(previous){for(const [name,value]of previous.attrs){if(value===null)previous.select.removeAttribute(name);else previous.select.setAttribute(name,value);}
      if(focus&&previous.select.isConnected&&!previous.select.matches(":disabled")&&!previous.select.closest('[inert], [aria-hidden="true"]'))previous.select.focus({preventScroll:true});}
    setMenu(null);
  };
  const choose=(index:number)=>{
    const value=current.current;if(!value)return;
    const fresh=readSelectOptions(value.select),option=fresh[index];
    if(!value.select.isConnected||value.select.matches(":disabled")||!option||option.disabled||JSON.stringify(fresh)!==JSON.stringify(value.options)){close();return;}
    const changed=value.select.selectedIndex!==index;
    close(true);
    if(changed){value.select.selectedIndex=index;value.select.dispatchEvent(new Event("input",{bubbles:true}));value.select.dispatchEvent(new Event("change",{bubbles:true}));}
  };
  useEffect(()=>{
    const eligible=(element:EventTarget|null):element is HTMLSelectElement=>element instanceof HTMLSelectElement&&element.isConnected&&!element.matches(':disabled, [multiple], [data-native-select]')&&element.size<=1&&!element.closest('[inert], [aria-hidden="true"]')&&!!element.closest(".app-shell, .notes-dialog")&&innerWidth>=768&&window.matchMedia("(hover:hover) and (pointer:fine)").matches&&typeof HTMLElement.prototype.showPopover==="function"&&element.getBoundingClientRect().height>0;
    const show=(select:HTMLSelectElement)=>{
      close();const options=readSelectOptions(select);if(!options.length)return false;
      const attrs=new Map(attributes.map(name=>[name,select.getAttribute(name)]));
      const label=select.getAttribute("aria-label")||Array.from(select.labels||[]).map(label=>{const copy=label.cloneNode(true) as HTMLElement;copy.querySelectorAll("select,input,textarea,button").forEach(node=>node.remove());return copy.textContent?.trim();}).filter(Boolean).join(" ")||"选项";
      const position=selectMenuPosition(select.getBoundingClientRect(),{width:innerWidth,height:innerHeight},options.length);
      if(position.maxHeight<100)return false;
      const selected=options[select.selectedIndex];
      const scrolls=new Map<EventTarget,string>([[document,`${window.scrollX}:${window.scrollY}`]]);
      for(let node=select.parentElement;node;node=node.parentElement)scrolls.set(node,`${node.scrollLeft}:${node.scrollTop}`);
      const next={select,options,attrs,scrolls,label:label.slice(0,120),active:selected&&!selected.disabled?select.selectedIndex:moveSelectOption(options,-1,1),position};
      current.current=next;setMenu(next);select.focus({preventScroll:true});return true;
    };
    const pointer=(event:PointerEvent)=>{
      if(popover.current?.contains(event.target as Node))return;
      if(eligible(event.target)&&event.button===0){if(current.current?.select===event.target){event.preventDefault();close(true);}else if(show(event.target))event.preventDefault();}
      else if(current.current)close();
    };
    let typed="",lastTyped=0;
    const keyboard=(event:KeyboardEvent)=>{
      const value=current.current;
      if(!value){if(eligible(event.target)&&["ArrowDown","ArrowUp","Enter"," ","Home","End"].includes(event.key)&&!event.ctrlKey&&!event.metaKey){if(!show(event.target))return;event.preventDefault();if(event.key==="Home")setActive(moveSelectOption(readSelectOptions(event.target),-1,1));if(event.key==="End")setActive(moveSelectOption(readSelectOptions(event.target),0,-1));}return;}
      if(event.key==="Escape"){event.preventDefault();event.stopPropagation();close(true);return;}
      if(event.key==="Tab"){close();return;}
      if(event.target!==value.select)return;
      if(["ArrowDown","ArrowUp","Home","End","Enter"," "].includes(event.key)){
        event.preventDefault();event.stopPropagation();
        if(event.key==="Enter"||event.key===" ")choose(value.active);
        else setActive(moveSelectOption(value.options,event.key==="Home"?-1:event.key==="End"?0:value.active,event.key==="ArrowUp"||event.key==="End"?-1:1));
      }else if(event.key.length===1&&!event.ctrlKey&&!event.metaKey&&!event.altKey){
        event.preventDefault();const now=Date.now();typed=now-lastTyped<700?typed+event.key:event.key;lastTyped=now;
        const match=matchSelectOption(value.options,typed,value.active);setActive(match<0?matchSelectOption(value.options,event.key,value.active):match);
      }
    };
    const scroll=(event:Event)=>{const menu=current.current;if(!menu||!event.target||popover.current?.contains(event.target as Node))return;const before=menu.scrolls.get(event.target);const after=event.target===document?`${window.scrollX}:${window.scrollY}`:event.target instanceof HTMLElement?`${event.target.scrollLeft}:${event.target.scrollTop}`:"";if(before!==undefined&&before!==after)close();};
    const resize=()=>close();
    const changed=(event:Event)=>{if(event.target===current.current?.select)close();};
    const focus=(event:FocusEvent)=>{if(current.current&&event.target!==current.current.select&&!popover.current?.contains(event.target as Node))close();};
    const modalClose=(event:Event)=>{if(current.current&&event.target===current.current.select.closest("dialog"))close();};
    const unauthorized=()=>close();
    document.addEventListener("pointerdown",pointer,true);document.addEventListener("keydown",keyboard,true);document.addEventListener("scroll",scroll,true);document.addEventListener("change",changed,true);document.addEventListener("focusin",focus,true);document.addEventListener("close",modalClose,true);
    window.addEventListener("resize",resize);window.addEventListener("popstate",resize);window.addEventListener("hustudy:before-navigate",resize);window.addEventListener("hustudy:unauthorized",unauthorized);
    return()=>{document.removeEventListener("pointerdown",pointer,true);document.removeEventListener("keydown",keyboard,true);document.removeEventListener("scroll",scroll,true);document.removeEventListener("change",changed,true);document.removeEventListener("focusin",focus,true);document.removeEventListener("close",modalClose,true);window.removeEventListener("resize",resize);window.removeEventListener("popstate",resize);window.removeEventListener("hustudy:before-navigate",resize);window.removeEventListener("hustudy:unauthorized",unauthorized);close();};
  },[]);
  useLayoutEffect(()=>{
    if(!menu||!popover.current||current.current?.select!==menu.select)return;
    const control=menu.select;
    control.setAttribute("aria-expanded","true");control.setAttribute("aria-controls",id);control.setAttribute("data-select-open","true");
    if(menu.active>=0)control.setAttribute("aria-activedescendant",`${id}-${menu.active}`);
    try{if(!popover.current.matches(":popover-open"))popover.current.showPopover();}catch{close();return;}
    const item=popover.current.querySelector<HTMLElement>(`[data-option-index="${menu.active}"]`),list=popover.current.querySelector<HTMLElement>(".select-menu-options");
    if(item&&list){if(item.offsetTop<list.scrollTop)list.scrollTop=item.offsetTop;else if(item.offsetTop+item.offsetHeight>list.scrollTop+list.clientHeight)list.scrollTop=item.offsetTop+item.offsetHeight-list.clientHeight;}
  },[menu]);
  useEffect(()=>{
    if(!menu?.select)return;
    const control=menu.select;
    const options=new MutationObserver(()=>close());options.observe(control,{attributes:true,attributeFilter:["disabled","multiple","size","label","value","selected"],childList:true,subtree:true,characterData:true});
    const removal=new MutationObserver(()=>{if(!control.isConnected||control.matches(":disabled"))close();});removal.observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:["disabled"]});
    return()=>{options.disconnect();removal.disconnect();};
  },[menu?.select]);
  if(!menu)return null;
  return createPortal(<div ref={popover} id={id} popover="manual" className="select-menu" style={{left:menu.position.left,top:menu.position.top,width:menu.position.width,maxHeight:menu.position.maxHeight}}>
    <div className="select-menu-heading"><span>{menu.label}</span><small>{menu.options.filter(option=>!option.hidden).length} 项</small></div>
    <div className="select-menu-options" role="listbox" aria-label={`${menu.label}的选项`}>{menu.options.map((option,index)=><div key={index} hidden={option.hidden}>
      {option.group&&(index===0||menu.options[index-1].group!==option.group)&&<div className="select-menu-group">{option.group}</div>}
      <button type="button" tabIndex={-1} id={`${id}-${index}`} data-option-index={index} role="option" aria-selected={menu.select.selectedIndex===index} aria-disabled={option.disabled} disabled={option.disabled} className={menu.active===index?"is-active":""} onPointerDown={event=>event.preventDefault()} onPointerMove={()=>{if(!option.disabled&&current.current?.active!==index)setActive(index);}} onClick={()=>choose(index)}><span>{option.label||"（空选项）"}</span>{menu.select.selectedIndex===index?<Icon name="check" size={15}/>:<span className="select-menu-check-space"/>}</button>
    </div>)}</div><div className="select-menu-help">↑ ↓ 选择 <span>Enter 确认 · Esc 取消</span></div>
  </div>,menu.select.closest("dialog")||document.body);
}
