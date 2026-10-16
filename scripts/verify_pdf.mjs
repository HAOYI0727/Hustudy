// Exercise the installed PDF.js renderer with self-authored pages, without a browser or network.
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {getDocument} from '../frontend/node_modules/pdfjs-dist/legacy/build/pdf.mjs';
const task=getDocument({data:new Uint8Array(await readFile('fixtures/preview_demo.pdf')),standardFontDataUrl:'./frontend/node_modules/pdfjs-dist/standard_fonts/'});
try {
  const pdf=await task.promise;
  assert.equal(pdf.numPages,2);
  const hashes=[];
  for (const pageNo of [1,2]) {
    const page=await pdf.getPage(pageNo);
    const viewport=page.getViewport({scale:1});
    const frame=pdf.canvasFactory.create(viewport.width,viewport.height);
    try {
      await page.render({canvas:frame.canvas,canvasContext:frame.context,viewport}).promise;
      const png=frame.canvas.toBuffer('image/png');
      assert.equal(png.subarray(0,8).toString('hex'),'89504e470d0a1a0a');
      assert(frame.canvas.width*frame.canvas.height<3_000_000);
      const body=(await page.getTextContent()).items.map(item=>item.str||'').join(' ');
      assert(body.includes(`Page ${pageNo}:`));
      hashes.push(createHash('sha256').update(png).digest('hex'));
    } finally { pdf.canvasFactory.destroy(frame); }
  }
  assert.notEqual(hashes[0],hashes[1]);
  await assert.rejects(pdf.getPage(3));
  console.log('PDF.js checks passed: two distinct page PNGs, matching text, image budget and invalid page rejection.');
} finally { await task.destroy(); }
