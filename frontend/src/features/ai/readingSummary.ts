import type {AIAnswer, SourceCitation, StudyReport} from "../../api/client";

export function matchingReadingTopics(topics:StudyReport["topics"],versionId:string,query:string,page:number|null=null){
  const key=query.trim().toLocaleLowerCase();
  return topics.filter(topic=>{
    const text=[topic.name,topic.explanation,topic.concept_group||"",...topic.misconceptions,...topic.labels.map(label=>label.reason)].join("\n").toLocaleLowerCase();
    return (!key||text.includes(key))&&(page===null||readingPages(topic.citations,versionId).some(row=>row.page===page));
  });
}

export function readingSummaryGoal(name:string):string {
  return `请针对当前正在阅读的课件《${Array.from(name).slice(0,120).join("")}》整理全面的知识点总结和可用于撰写学习笔记的内容。
先通读本次提供的全部正文，沿课件页序识别主题，将连续或分散出现的同一知识点合并讲解，不要仅总结开头，也不要机械地一页一个知识点。
每个知识点说明定义、核心原理、适用条件、概念关系与易错点；原文出现的公式、代码或步骤须保留关键符号和条件，不补造不存在的结论。
每个知识点的evidence选择真实原文摘录，涉及不同页时尽量提供各页的相关依据，供页面呈现“第1–3页对应某知识点”这类可核对的目录。不要自行编造页号或把不连续页面写成连续范围。
给出适合整理笔记的层次、例题、自测和复习建议，明确哪些属于AI建议。仅覆盖实际输入文字；图片/图表未提取、缺页或分批时说明局限，不声称已理解整份原件或完成跨批融合。`;
}

export function belongsToReadingVersion(answer:AIAnswer, versionId:string):boolean {
  const coverage=answer.result.coverage?.versions;
  const citations=answer.result.citations||[];
  if(coverage?.length&&!(coverage.length===1&&coverage[0].version_id===versionId))return false;
  if(citations.some(source=>source.version_id!==versionId))return false;
  return Boolean(coverage?.length||citations.some(source=>source.version_id===versionId));
}

export function readingPages(sources:SourceCitation[], versionId:string) {
  const pages=new Map<number,SourceCitation>();
  for(const source of sources){
    if(source.version_id!==versionId||source.availability!=="active"||!source.locator||!["slide","page"].includes(source.locator.type))continue;
    if(!/^[1-9]\d*$/.test(source.locator.value))continue;
    const page=Number(source.locator.value);
    if(Number.isSafeInteger(page)&&!pages.has(page))pages.set(page,source);
  }
  return [...pages].sort(([a],[b])=>a-b).map(([page,source])=>({page,source}));
}

export function readingPageLabel(pages:number[]):string {
  const sorted=[...new Set(pages)].sort((a,b)=>a-b);
  if(!sorted.length)return "暂无可核对页码";
  const ranges:string[]=[];
  let start=sorted[0],end=start;
  for(const page of sorted.slice(1)){
    if(page===end+1){end=page;continue;}
    ranges.push(start===end?String(start):`${start}–${end}`);start=end=page;
  }
  ranges.push(start===end?String(start):`${start}–${end}`);
  return `第${ranges.join("、")}页`;
}
