export type SelectMenuOption={index:number;value:string;label:string;disabled:boolean;group:string};
export function readSelectOptions(select:HTMLSelectElement):SelectMenuOption[]{
  return Array.from(select.options).map((option,index)=>({index,value:option.value,label:option.label,disabled:option.disabled||option.parentElement instanceof HTMLOptGroupElement&&option.parentElement.disabled,group:option.parentElement instanceof HTMLOptGroupElement?option.parentElement.label:""}));
}
export function moveSelectOption(options:SelectMenuOption[],current:number,direction:1|-1):number {
  if(!options.some(option=>!option.disabled))return -1;
  for(let distance=1;distance<=options.length;distance++){
    const index=(current+direction*distance+options.length*2)%options.length;
    if(!options[index].disabled)return index;
  }
  return -1;
}
export function matchSelectOption(options:SelectMenuOption[],query:string,current:number):number {
  const key=query.toLocaleLowerCase();
  for(let distance=1;distance<=options.length;distance++){
    const index=(current+distance+options.length)%options.length;
    if(!options[index].disabled&&options[index].label.toLocaleLowerCase().startsWith(key))return index;
  }
  return -1;
}
export function selectMenuPosition(rect:{left:number;top:number;bottom:number;width:number},viewport:{width:number;height:number},count:number){
  const margin=12,width=Math.min(Math.max(rect.width,220),440,viewport.width-margin*2);
  const above=Math.max(0,rect.top-margin-6),below=Math.max(0,viewport.height-rect.bottom-margin-6);
  const desired=Math.min(360,count*40+96),up=below<Math.min(desired,180)&&above>below;
  const height=Math.max(0,Math.min(desired,up?above:below));
  return {left:Math.max(margin,Math.min(rect.left,viewport.width-width-margin)),top:up?Math.max(margin,rect.top-height-6):rect.bottom+6,width,maxHeight:height,up};
}
