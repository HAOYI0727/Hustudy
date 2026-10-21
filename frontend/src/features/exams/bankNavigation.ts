// One decision belongs to one navigation event, regardless of how many drafts listen.
const decisions=new WeakMap<Event,boolean>();
export function confirmBankLeave(event:Event){
 if(event.defaultPrevented)return false;
 let allowed=decisions.get(event);
 if(allowed===undefined){
  allowed=window.confirm("还有未保存的题目校正、标签或其他草稿，放弃这些修改并离开？取消可返回继续修改。");
  decisions.set(event,allowed);
 }
 if(!allowed)event.preventDefault();
 return allowed;
}
