import type {DocumentMetadata,DocumentOrganizeChange} from "../../api/client";

export const materialTags=(value:string)=>Array.from(new Set(value.split(/[,，]/).map(tag=>tag.trim()).filter(Boolean)));
export function organizedTags(current:string[],change:DocumentOrganizeChange):string[]{
  if(change.tags_mode==="clear")return [];
  if(change.tags_mode==="replace")return [...change.tags];
  if(change.tags_mode==="add")return Array.from(new Set([...current,...change.tags]));
  if(change.tags_mode==="remove")return current.filter(tag=>!change.tags.includes(tag));
  return [...current];
}
export function organizeError(items:DocumentMetadata[],change:DocumentOrganizeChange){
  if(!items.length||items.length>100)return "请选择1–100份资料";
  if(change.category===undefined&&change.tags_mode==="keep")return "请设置分类或标签操作";
  if(change.category!==undefined&&(!change.category.trim()||Array.from(change.category.trim()).length>40))return "分类需要1–40个字符";
  if(["add","remove","replace"].includes(change.tags_mode)&&!change.tags.length)return "请填写需要整理的标签";
  if(change.tags.length>12||change.tags.some(tag=>!tag||Array.from(tag).length>32))return "最多12个标签，每个1–32个字符";
  const full=items.find(item=>organizedTags(item.tags,change).length>12);
  return full?`「${full.name}」整理后会超过12个标签，请减少新增标签或改用替换`:"";
}
