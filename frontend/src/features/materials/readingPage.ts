type Locator = {locator_type:string;locator_value:string};
export type ReadingCursor = {versionId:string;view:"native"|"pdf";page:number};

export function sourceReadingPage({versionId,view,kind,cursor,chunks}:{versionId:string;view:string;kind:"pptx"|"pdf"|"docx"|undefined;cursor:ReadingCursor|null;chunks:Locator[]}):number|null {
  if(!versionId)return null;
  if(view==="text"){
    if(chunks.length!==1)return null;
    const source=chunks[0];
    if(!((kind==="pptx"&&source.locator_type==="slide")||(kind==="pdf"&&source.locator_type==="page")))return null;
    if(!/^[1-9]\d*$/.test(source.locator_value))return null;
    const page=Number(source.locator_value);
    return Number.isSafeInteger(page)?page:null;
  }
  if(!cursor||cursor.versionId!==versionId||cursor.view!==view||!Number.isSafeInteger(cursor.page)||cursor.page<1)return null;
  return (view==="native"&&kind==="pptx")||(view==="pdf"&&(kind==="pptx"||kind==="pdf"))?cursor.page:null;
}
