/** Runs only in a sandboxed, opaque-origin iframe. Never receives credentials. */
import { PptxViewer, RECOMMENDED_ZIP_LIMITS } from '@aiden0z/pptx-renderer';
import { renderAsync } from 'docx-preview';

const channel = document.documentElement.dataset.channel!;
const stage = document.getElementById('office-stage')!;
let viewer: PptxViewer | undefined;
let pages: HTMLElement[] = [];
let kind = '', page = 1, count = 0, currentZoom = 100, started = false;
let queue = Promise.resolve();
const post = (type:string, extra:Record<string,unknown>={}) => parent.postMessage({channel,type,...extra},'*');
const failure = () => post('error');
function state() { post('state',{page,count,zoom:currentZoom}); }
async function navigate(target:number,zoom:number) {
  page = Math.max(1,Math.min(count,target));currentZoom=zoom;
  if (viewer) {
    await viewer.goToSlide(page-1);
    await viewer.setZoom(zoom);
  } else {
    pages.forEach((node,index)=>{node.style.display = index===page-1 ? '' : 'none';});
    const width = pages[page-1]?.offsetWidth || 800;
    const ratio = Math.min(1,Math.max(.25,(innerWidth-32)/width))*(zoom/100);
    // Zoom changes layout as well as visual size, keeping narrow views scrollable.
    stage.style.zoom=String(ratio);
    scrollTo(0,0);
  }
  await document.fonts.ready;
  state();
}
window.addEventListener('message',event=>{
  const data=event.data;
  if(event.source!==parent || !data || data.channel!==channel)return;
  if(data.type==='open' && !started && data.buffer instanceof ArrayBuffer && ['pptx','docx'].includes(data.kind)) {
    started=true; kind=data.kind;
    queue=queue.then(async()=>{
      if(data.buffer.byteLength>30*1024*1024)throw new Error('resource limit');
      if(kind==='pptx') {
        viewer=await PptxViewer.open(data.buffer,stage,{
          renderMode:'slide',fitMode:'contain',lazySlides:true,lazyMedia:true,pdfjs:false,
          zipLimits:{...RECOMMENDED_ZIP_LIMITS,maxEntries:10000,maxTotalUncompressedBytes:100*1024*1024,maxEntryUncompressedBytes:30*1024*1024,maxMediaBytes:80*1024*1024,maxConcurrency:2},
          onNodeError:()=>post('degraded'),
        });
        count=viewer.slideCount;
      } else {
        await renderAsync(data.buffer,stage,document.getElementById('office-styles')!,{
          inWrapper:true,breakPages:true,ignoreLastRenderedPageBreak:false,
          renderAltChunks:false,renderComments:false,renderChanges:false,useBase64URL:true,
        });
        pages=Array.from(stage.querySelectorAll<HTMLElement>('section.docx'));
        count=pages.length;
      }
      if(!count || count>2000)throw new Error('invalid page count');
      await navigate(Number.isInteger(data.page)?data.page:1,100);
    }).catch(failure);
  } else if (data.type==='navigate' && started && count && Number.isInteger(data.page) && Number.isFinite(data.zoom) && data.zoom>=50 && data.zoom<=200) {
    queue=queue.then(()=>navigate(data.page,data.zoom)).catch(failure);
  }
});
// Document-authored links cannot navigate this frame or open external windows.
document.addEventListener('click',event=>{if((event.target as Element)?.closest?.('a'))event.preventDefault();},true);
window.addEventListener('keydown',event=>{
  if(event.key==='Escape'){post('escape');return;}
  if(kind!=='pptx' || !count || getSelection()?.toString())return;
  if(['ArrowRight','PageDown','ArrowLeft','PageUp'].includes(event.key)) {
    event.preventDefault();
    queue=queue.then(()=>navigate(page+(['ArrowRight','PageDown'].includes(event.key)?1:-1),currentZoom)).catch(failure);
  }
});
window.addEventListener('resize',()=>{if(kind==='docx'&&count)queue=queue.then(()=>navigate(page,currentZoom)).catch(failure);});
window.addEventListener('pagehide',()=>viewer?.destroy());
post('boot');
