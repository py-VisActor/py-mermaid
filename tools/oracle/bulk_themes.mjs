// Development-only configuration oracle from the fixed npm original.
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const root=path.resolve(import.meta.dirname,'../..');
const pkg=path.join(root,'.local/f011-oracle/node_modules/mermaid');
if(JSON.parse(fs.readFileSync(path.join(pkg,'package.json'),'utf8')).version!=='12.2.0')throw Error('Oracle version drift');
const {default:mermaid}=await import(pathToFileURL(path.join(pkg,'dist/mermaid.core.mjs')).href);
const arg=n=>process.argv[process.argv.indexOf(n)+1];
const cases=JSON.parse(fs.readFileSync(arg('--fixtures'),'utf8')).cases;
const rows=[];
for(const item of cases){
 if(item.group&&item.group!=='shared')continue;
 if(!item.config?.theme)continue;
 mermaid.initialize({startOnLoad:false,...item.config});
 rows.push({id:item.id,theme:item.config.theme,themeVariables:mermaid.mermaidAPI.getConfig().themeVariables});
}
fs.writeFileSync(arg('--out'),JSON.stringify({package:'mermaid@12.2.0',cases:rows},null,2)+'\n');
