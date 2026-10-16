import {build} from 'rolldown';
import {mkdir,writeFile,readFile,readdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
const root=new URL('../',import.meta.url);
await mkdir(new URL('public/native-office/',root),{recursive:true});
await build({
  cwd:fileURLToPath(root),input:'src/features/materials/office/runtime.ts',platform:'browser',
  transform:{define:{'process.env.NODE_ENV':JSON.stringify('production'),'import.meta':'({})'}},
  output:{file:fileURLToPath(new URL('public/native-office/runtime.js',root)),format:'iife',codeSplitting:false,minify:true,sourcemap:false},
});
await writeFile(new URL('public/native-office/README.txt',root),'Generated local Office runtime. Source: src/features/materials/office/runtime.ts. Rebuild with npm run build:office. Licenses: /third-party-notices.txt\n');
console.log('Local sandboxed Office runtime built.');

// Retain complete shipped notices, including embedded dependencies in JSZip/PPTX.
const packages=['@aiden0z/pptx-renderer','docx-preview','jszip','echarts','zrender','tslib','pako','lie','immediate','readable-stream','setimmediate','core-util-is','inherits','isarray','process-nextick-args','safe-buffer','string_decoder','util-deprecate'];
const sections=['Hustudy local Office preview: unmodified upstream packages; JSZip used under its MIT option.\n'];
for(const name of packages){
  const directory=new URL(`node_modules/${name}/`,root);
  const pkg=JSON.parse(await readFile(new URL('package.json',directory),'utf8'));
  sections.push(`\n=== ${name} ${pkg.version} (${pkg.license}) ===\n`);
  for(const file of await readdir(directory))if(/license|notice|copying/i.test(file)){
    try{sections.push(`\n${file}\n`+await readFile(new URL(file,directory),'utf8'));}catch(error){if(error.code!=='EISDIR')throw error;}
  }
}
const embedded=new URL('node_modules/@aiden0z/pptx-renderer/licenses/',root);
for(const file of await readdir(embedded))sections.push(`\nPPTX embedded license: ${file}\n`+await readFile(new URL(file,embedded),'utf8'));
await writeFile(new URL('public/native-office/notices.txt',root),sections.join('\n').replace(/\r\n/g,'\n'));
