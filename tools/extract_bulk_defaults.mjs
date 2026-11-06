// Mechanical fixed-package configuration extraction; no diagram parsing/rendering.
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const root=path.resolve(import.meta.dirname,'..');
const pkg=path.join(root,'.local/f011-oracle/node_modules/mermaid');
const metadata=JSON.parse(fs.readFileSync(path.join(pkg,'package.json'),'utf8'));
if(metadata.version!=='12.2.0')throw Error('Wrong fixed Mermaid package');
const {default:mermaid}=await import(pathToFileURL(path.join(pkg,'dist/mermaid.core.mjs')).href);
const config=JSON.parse(JSON.stringify(mermaid.mermaidAPI.getConfig()));
function target(value){
 if(Array.isArray(value))return value.map(target);
 if(value&&typeof value==='object'){
  const out={};for(const [key,item] of Object.entries(value)){
   if(key==='defaultRenderer'&&typeof item==='string'&&item.toLowerCase().includes('dagre'))continue;
   out[key]=key==='layout'&&typeof item==='string'&&item.toLowerCase().includes('dagre')?'elk':target(item);
  }return out;
 }return value;
}
const output=path.join(root,'src/py_mermaid/data/diagram_defaults.json');
fs.mkdirSync(path.dirname(output),{recursive:true});
fs.writeFileSync(output,JSON.stringify({upstreamVersion:'12.2.0',upstreamCommit:'1fb7869866dd619168d840291c9c54b4f129758b',source:'fixed npm defaultConfig (functions omitted; native derived accessors)',config:target(config)},null,2)+'\n');
console.log(JSON.stringify({version:metadata.version,keys:Object.keys(config).length,output}));
