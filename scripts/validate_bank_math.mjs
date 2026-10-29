import {createRequire} from 'node:module';
const require=createRequire(new URL('../frontend/package.json',import.meta.url));
const katex=require('katex');
let input='';
for await (const part of process.stdin) input+=part;
const expressions=JSON.parse(input);
const errors=[];
for(const [index,expression] of expressions.entries()){
 try{katex.renderToString(expression,{throwOnError:true,strict:'error',trust:false,maxExpand:1000});}
 catch{errors.push(index);}
}
process.stdout.write(JSON.stringify(errors));
