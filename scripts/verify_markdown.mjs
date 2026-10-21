// Render the actual preview component and check hostile content without a browser/network.
import { createRequire } from 'node:module';
import { mkdtemp, readFile, writeFile, rm, readdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { resolve, join, dirname } from 'node:path';
import { pathToFileURL } from 'node:url';
import assert from 'node:assert/strict';
const frontend = resolve('frontend');
const require = createRequire(join(frontend,'package.json'));
import { execFileSync } from 'node:child_process';
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const scratch = await mkdtemp(join(frontend,'.markdown-check-'));
try {
  // Invoke the JS entry directly; Windows .bin uses a .cmd shim.
  execFileSync(process.execPath, [join(frontend,'node_modules/typescript/bin/tsc'),
    join(frontend,'src/components/knowledge.tsx'), join(frontend,'src/features/ai/AIAnswerPreview.tsx'), '--noCheck', '--jsx', 'react-jsx',
    '--target','es2020','--module','esnext','--moduleResolution','bundler',
    '--rootDir',join(frontend,'src'),'--outDir',scratch
  ]);
  // Compile the real transitive component tree for native Node ESM. Browser-only
  // styles are irrelevant to this HTML safety check; no production sources change.
  for (const name of await readdir(scratch,{recursive:true})) {
    if (!name.endsWith('.js')) continue;
    const file=join(scratch,name);
    const compiled=(await readFile(file,'utf8'))
      .replace(/import\s+(['"])[^'"\n]+\.css\1\s*;?/g,'')
      .replace(/\bfrom\s+(['"])(\.{1,2}\/[^'"]+)\1/g,(all,quote,target)=>
        existsSync(resolve(dirname(file),target+'.js')) ? `from ${quote}${target}.js${quote}` : all);
    await writeFile(file,compiled);
  }
  const {NotePreview} = await import(pathToFileURL(join(scratch,'components/knowledge.js')));
  const id='11111111-1111-1111-1111-111111111111';
  const render = content => renderToStaticMarkup(React.createElement(NotePreview,{content,token:'test',notes:[{id,title:'改名后的概念'}],onNote:()=>{}}));
  const hostile=render('<script>alert(1)</script>\n\n[x](javascript:alert(1))\n\n![track](https://example.invalid/tracker.png)');
  assert(!hostile.includes('<script') && !hostile.includes('href="javascript:') && !hostile.includes('<img'));
  assert(render(`[[note:${id}|旧名称]]`).includes('改名后的概念'));
  assert(render('[[note:22222222-2222-2222-2222-222222222222|已删除]]').includes('目标笔记已删除'));
  assert(render(`![[asset:${id}|课程图]]`).includes('正在加载图片'));
  assert(render('|列|\n|---|\n|值|').includes('<table>'));
  const {AIAnswerPreview} = await import(pathToFileURL(join(scratch,'features/ai/AIAnswerPreview.js')));
  const ai = renderToStaticMarkup(React.createElement(AIAnswerPreview,{content:
    '<script>alert(1)</script>\n\n[x](javascript:alert(1))\n\n[外部链接](https://example.invalid/?private=quote)\n\n![track](https://example.invalid/tracker.png)\n\n|列|\n|---|\n|值|'}));
  assert(!ai.includes('<script') && !ai.includes('<img') && !ai.includes('href='));
  assert(ai.includes('<table>') && ai.includes('外部链接'));
  console.log('Markdown checks passed: HTML/script, unsafe URL, external image, rename/deletion, asset and GFM table.');
  console.log('AI answer checks passed: HTML removed, generated links/images inert, GFM table preserved.');
} finally { await rm(scratch,{recursive:true,force:true}); }
