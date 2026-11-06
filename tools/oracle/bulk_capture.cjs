/* Development-only raw oracle for the fixed retained static batch. */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),cp=require('node:child_process');
const {createRequire,stripTypeScriptTypes}=require('node:module');
const root=path.resolve(__dirname,'../..'),dep=path.join(root,'.local/f011-oracle');
const req=createRequire(path.join(dep,'package.json'));
const pkg=path.join(dep,'node_modules/mermaid'),upstream=path.join(root,'.local/upstream-mermaid');
const zen=path.join(root,'.local/bulk-sources/zenuml/package/dist');
const sha=x=>crypto.createHash('sha256').update(x).digest('hex');
const tidyModules=new Map();
function tidyIdentity(){
 const records=[];
 for(const name of ['layouts','render','layout']){
  const relative=`packages/mermaid-layout-tidy-tree/src/${name}.ts`;
  const canonical=cp.execFileSync('git',['-C',upstream,'show','HEAD:'+relative]);
  const checkout=fs.readFileSync(path.join(upstream,relative));
  const checkoutEol=checkout.equals(canonical)?'canonical bytes':'Git Windows CRLF checkout; canonical git blob used for compilation';
  if(!checkout.equals(canonical)&&checkout.toString('utf8').replace(/\r\n/g,'\n')!==canonical.toString('utf8'))throw Error('Tidy canonical checkout drift: '+relative);
  let compiled=stripTypeScriptTypes(canonical.toString('utf8'),{mode:'strip',sourceUrl:relative});
  // Import resolution only. Layout and rendering statements are untouched.
  compiled=compiled.replace(/(from\s*)['"]non-layered-tidy-tree-layout['"]/g,"$1'../tidy-dep/index.js'");
  tidyModules.set(`http://bulk-oracle.local/tidy/${name}.js`,compiled);
  records.push({path:relative,canonicalSha256:sha(canonical),checkoutSha256:sha(checkout),checkoutEol,transportSha256:sha(compiled),transformation:'Node native TypeScript type erasure of canonical git blob; bare package URL resolution only'});
 }
 const dependency=[];
 for(const [name,expected] of Object.entries({algorithm:'c2ec0ef1a36b6ef35d20e2d94637967d205a8afc78947d54807e77495f7294d4',helpers:'e00183b0c1b8f9c84f55ebd9bb7cdc77c3a476bd102b4efb9583064f6b761345',index:'27befdfc33e387d3d0e0260292be51145dbb0d79025a07688a8aec932007d112'})){
  const relative=`.local/bulk-sources/non-layered-tidy-tree-layout-2.0.2/package/src/${name}.js`,raw=fs.readFileSync(path.join(root,relative));
  if(sha(raw)!==expected)throw Error('Tidy dependency source drift: '+relative);
  for(const suffix of ['', '.js'])tidyModules.set(`http://bulk-oracle.local/tidy-dep/${name}${suffix}`,raw);
  dependency.push({path:relative,sha256:expected,transformation:'None; extensionless original ES module imports served as JavaScript'});
 }
 return {package:'@mermaid-js/layout-tidy-tree@1.0.1',sources:records,dependency:{package:'non-layered-tidy-tree-layout@2.0.2',sources:dependency},compiler:process.version,note:'Original fixed source plugin, explicitly registered; never substitute COSE fallback for requested tidy-tree.'};
}
const save=(p,v)=>fs.writeFileSync(p,JSON.stringify(v,(_k,x)=>typeof x==='number'&&!Number.isFinite(x)?{$jsNumber:String(x)}:x,2)+'\n');
async function timed(promise,ms){let timer;try{return await Promise.race([promise,new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('Official case timeout '+ms+'ms')),ms)})])}finally{clearTimeout(timer)}}
function identity(){
 const head=cp.execFileSync('git',['-C',upstream,'rev-parse','HEAD'],{encoding:'utf8'}).trim();
 if(head!=='1fb7869866dd619168d840291c9c54b4f129758b')throw Error('Upstream commit drift');
 const meta=JSON.parse(fs.readFileSync(path.join(pkg,'package.json'),'utf8'));
 if(meta.version!=='12.2.0')throw Error('Mermaid oracle package drift');
 const map=JSON.parse(fs.readFileSync(path.join(pkg,'dist/mermaid.js.map'),'utf8'));
 const verified=[],generated=[],notCanonical=[],schemaTransforms=[];
 const tracked=new Set(cp.execFileSync('git',['-C',upstream,'ls-tree','-r','--name-only','HEAD'],{encoding:'utf8'}).trim().split('\n'));
 for(let i=0;i<map.sources.length;i++){
  const name=map.sources[i];if(!name.startsWith('../src/'))continue;
  const relative='packages/mermaid/src/'+name.slice(7);
  if(!tracked.has(relative)){notCanonical.push(relative);continue;}
  const canonical=cp.execFileSync('git',['-C',upstream,'show','HEAD:'+relative]);
  let expected=canonical.toString('utf8'),transformation='canonical git blob';
  if(relative==='packages/mermaid/src/schemas/config.schema.yaml'){
   // Esbuild's source map stores getDefaults(schema), not YAML text. Do not
   // claim byte equality or silently relabel this transformed source as raw.
   const lock=JSON.parse(fs.readFileSync(path.join(root,'references/upstream.lock.json'),'utf8'));
   if(sha(canonical)!==lock.sha256[relative])throw Error('Canonical schema drift');
   if(!map.sourcesContent[i].startsWith('export default {'))throw Error('Unrecognized schema build transport');
   const defaults=JSON.parse(map.sourcesContent[i].replace(/^export default /,'').replace(/;\s*$/,''));
   schemaTransforms.push({path:relative,canonicalSha256:sha(canonical),artifactSourceSha256:sha(map.sourcesContent[i]),
    transformation:'.build/jsonSchema.ts:getDefaults / AJV useDefaults',rawByteComparable:false,
    buildScriptSha256:sha(cp.execFileSync('git',['-C',upstream,'show','HEAD:.build/jsonSchema.ts'])),
    generatedDefaults:defaults,note:'Canonical schema and generated artifact separately identified; not counted as byte-equal source.'});
   continue;
  }
  if(relative.endsWith('.jison')){
   const parser=new (req('jison').Generator)(expected,{moduleType:'js','token-stack':true});
   expected=parser.generate({moduleMain:'() => {}'})+' \n\tparser.parser = parser;\n\texport { parser };\n\texport default parser;\n\t';
   transformation='fixed .build/jisonTransformer.ts / jison@0.4.18';
  }
  if(map.sourcesContent[i]!==expected)throw Error('Oracle canonical source mismatch: '+relative);
  const record={path:relative,canonicalSha256:sha(canonical),artifactSourceSha256:sha(map.sourcesContent[i]),transformation};
  verified.push(record);if(transformation!=='canonical git blob')generated.push(relative);
 }
 if(verified.length<100)throw Error('Incomplete Mermaid source map identity');
 const lock=JSON.parse(fs.readFileSync(path.join(dep,'package-lock.json'),'utf8'));
 const zm=JSON.parse(fs.readFileSync(path.join(zen,'../package.json'),'utf8'));
 if(zm.version!=='3.49.2')throw Error('ZenUML oracle drift');
 const zenMap=JSON.parse(fs.readFileSync(path.join(zen,'zenuml.js.map'),'utf8'));
 const zenSource=path.join(root,'.local/bulk-sources/zenuml/source'),zenVerified=[],zenReact=[];
 for(let i=0;i<zenMap.sources.length;i++){
  const name=zenMap.sources[i];if(!name.startsWith('../src/'))continue;
  const relative=name.slice(3).split('?')[0],canonical=fs.readFileSync(path.join(zenSource,relative));
  const artifact=zenMap.sourcesContent[i];
  if(name.endsWith('?react')){zenReact.push({path:relative,canonicalSha256:sha(canonical),artifactSourceSha256:sha(artifact),
    transformation:'Vite SVGR React component; excluded browser/UI host mechanism, not original raw SVG'});continue;}
  const decoded=name.endsWith('?raw')?JSON.parse(artifact.replace(/^export default /,'').replace(/;\s*$/,'')):artifact;
  if(decoded!==canonical.toString('utf8'))throw Error('ZenUML source-map mismatch: '+relative);
  zenVerified.push({path:relative,canonicalSha256:sha(canonical),artifactSourceSha256:sha(artifact),transformation:name.endsWith('?raw')?'Vite raw JSON string module':'canonical git-head archive file'});
 }
 const parserRoot=path.join(dep,'node_modules/@mermaid-js/parser'),parserPackage=JSON.parse(fs.readFileSync(path.join(parserRoot,'package.json'),'utf8'));
 if(parserPackage.version!=='2.0.1')throw Error('Locked parser package drift');
 const parserSources=[],parserGenerated=[],parserSeen=new Set();
 function parserMaps(directory){return fs.readdirSync(directory,{withFileTypes:true}).flatMap(e=>e.isDirectory()?parserMaps(path.join(directory,e.name)):e.name.endsWith('.map')?[path.join(directory,e.name)]:[])}
 for(const file of parserMaps(path.join(parserRoot,'dist'))){
  const sourceMap=JSON.parse(fs.readFileSync(file,'utf8'));
  for(let i=0;i<sourceMap.sources.length;i++){
   const name=sourceMap.sources[i];if(!name.includes('/src/')||name.includes('/node_modules/'))continue;
   const relative='packages/parser/src/'+name.split('/src/')[1];if(parserSeen.has(relative))continue;parserSeen.add(relative);
   const actual=sourceMap.sourcesContent[i];
   if(!tracked.has(relative)){parserGenerated.push({path:relative,artifactSourceSha256:sha(actual),transformation:'Generated Langium/runtime platform module; not a canonical tracked source file'});continue;}
   const canonical=cp.execFileSync('git',['-C',upstream,'show','HEAD:'+relative]);
   if(canonical.toString('utf8')!==actual)throw Error('Parser package source mismatch: '+relative);
   parserSources.push({path:relative,canonicalSha256:sha(canonical),artifactSourceSha256:sha(actual)});
  }
 }
 return {commit:head,package:'mermaid@12.2.0',bundleSha256:sha(fs.readFileSync(path.join(pkg,'dist/mermaid.js'))),
  npmIntegrity:lock.packages['node_modules/mermaid'].integrity,sources:verified,generated,notCanonical,schemaTransforms,
  parser:{package:'@mermaid-js/parser@2.0.1',sources:parserSources,generatedRuntimeModules:parserGenerated},
  zenuml:{package:'@zenuml/core@3.49.2',gitHead:'213c239587ffa1f3dbb54d8b64468c3038ced55d',
    bundleSha256:sha(fs.readFileSync(path.join(zen,'zenuml.js'))),
    sources:zenVerified,reactHostTransforms:zenReact,
    note:'Direct original core renderToSvg; fixed Mermaid plugin wrapper source hashes retained separately. No reimplementation of the oracle layout.'},tidyTree:tidyIdentity(),node:process.version};
}

async function main(){
 const arg=n=>{let i=process.argv.indexOf(n);return i<0?null:process.argv[i+1]};
 const out=path.resolve(arg('--out')||'');if(!arg('--out'))throw Error('--out required');
 fs.mkdirSync(out,{recursive:false});const sourceIdentity=identity();save(path.join(out,'identity.json'),sourceIdentity);
 if(process.argv.includes('--verify-only'))return;
 const fixture=JSON.parse(fs.readFileSync(arg('--fixtures'),'utf8'));
 const {chromium}=req('playwright');const browser=await chromium.launch({channel:'chrome',headless:true});
 const manifest={identity:sourceIdentity,browser:browser.version(),fixtureSha256:sha(fs.readFileSync(arg('--fixtures'))),cases:[]};
 try{for(const item of fixture.cases){
  if(item.expect==='excluded_by_static_scope'){manifest.cases.push({id:item.id,status:'excluded'});continue;}
  const page=await browser.newPage({viewport:{width:1600,height:1200},deviceScaleFactor:1,timezoneId:'Asia/Shanghai',locale:'en-US'});
  const network=[],pageErrors=[];page.on('pageerror',error=>pageErrors.push(String(error)));
  const documentHtml='<!doctype html><html><head><base href="http://bulk-oracle.local/zen/"></head><body style="margin:0;background:white"><div id="host"></div></body></html>';
  await page.route('**/*',route=>{
   const url=route.request().url(),image=item.browserResources?.images?.find(x=>x.id===url);
   if(url==='http://bulk-oracle.local/index.html')return route.fulfill({body:documentHtml,contentType:'text/html'});
   if(tidyModules.has(url))return route.fulfill({body:tidyModules.get(url),contentType:'application/javascript'});
   if(image)return route.fulfill({body:Buffer.from(image.dataBase64,'base64'),contentType:image.mime||'image/png'});
   if(url.startsWith('http://bulk-oracle.local/zen/')){
    const target=path.resolve(zen,decodeURIComponent(new URL(url).pathname.slice('/zen/'.length)));
    if(target.startsWith(zen+path.sep)&&fs.existsSync(target)&&fs.statSync(target).isFile())return route.fulfill({body:fs.readFileSync(target),contentType:target.endsWith('.js')||target.endsWith('.mjs')?'application/javascript':target.endsWith('.woff2')?'font/woff2':'application/octet-stream'});
   }
   network.push(url);return route.abort();
  });
  // A real intercepted origin is required by top-level ZenUML modules that
  // read localStorage. setContent on about:blank leaves an opaque origin and
  // stops the UMD factory before it exposes renderToSvg.
  await page.goto('http://bulk-oracle.local/index.html');
  try{
   await page.addScriptTag({path:path.join(pkg,'dist/mermaid.js')});
   await page.evaluate(async()=>{
    const {default:loaders}=await import('http://bulk-oracle.local/tidy/layouts.js');
    globalThis.__bulkTidyLoads=0;
    mermaid.registerLayoutLoaders(loaders.map(definition=>({...definition,loader:async()=>{
     globalThis.__bulkTidyLoads++;return definition.loader();
    }})));
   });
   if(item.kind==='zenuml')await page.addScriptTag({path:path.join(zen,'zenuml.js')});
   if(item.kind==='zenuml'&&!await page.evaluate(()=>typeof globalThis.zenuml?.renderToSvg==='function'))throw Error('ZenUML UMD initialization failed: '+pageErrors.join('; '));
   for(const font of item.browserResources?.fonts||[]){
    const data=fs.readFileSync(path.resolve(root,font.path));
    if(font.sha256&&sha(data)!==font.sha256)throw Error('Font SHA mismatch');
    await page.addStyleTag({content:`@font-face{font-family:${JSON.stringify(font.family)};src:url(data:font/ttf;base64,${data.toString('base64')})}`});
   }
   const result=await timed(page.evaluate(async item=>{
    try{
    const host=document.getElementById('host');mermaid.initialize({startOnLoad:false,...item.config});
    const packs={};for(const icon of item.browserResources?.icons||[]){
     const split=icon.id.indexOf(':');if(split<1)continue;const prefix=icon.id.slice(0,split),name=icon.id.slice(split+1);
     const svg=new DOMParser().parseFromString(icon.svg,'image/svg+xml').documentElement;
     const vb=(svg.getAttribute('viewBox')||'0 0 24 24').split(/[ ,]+/).map(Number);
     (packs[prefix]??={prefix,icons:{}}).icons[name]={body:svg.innerHTML,width:vb[2],height:vb[3]};
    }
    mermaid.registerIconPacks(Object.entries(packs).map(([name,icons])=>({name,icons})));
    let entries=0,references=new WeakMap(),nextReference=1;
    const pure=(value,seen=new Set(),depth=0)=>{
     if(depth===0){entries=0;references=new WeakMap();nextReference=1;}
     if(value===null||typeof value!=='object')return typeof value==='function'?undefined:value;
     if(depth>16)return {$truncated:'depth16'};
     if(++entries>20000)return {$truncated:'entryBudget20000'};
     if(references.has(value))return {$ref:references.get(value)};
     references.set(value,nextReference++);
     if(value instanceof Element)return {$dom:value.tagName};if(value instanceof Date)return {$date:value.toISOString()};
     seen.add(value);let r;
     if(value instanceof Map)r=Object.fromEntries([...value].map(([k,v])=>[k,pure(v,seen,depth+1)]));
     else if(value instanceof Set)r=[...value].map(v=>pure(v,seen,depth+1));
     else if(Array.isArray(value))r=value.map(v=>pure(v,seen,depth+1));
     else {r={};for(const key of Object.keys(value)){if(typeof value[key]!=='function')r[key]=pure(value[key],seen,depth+1);}}
     return r;
    };
    let diagram,snapshot={},originalOutput=null,transport={kind:'svg'},renderConfig=null;
    if(item.kind==='zenuml'){
     const original=await zenuml.renderToSvg(item.source.replace(/^\s*zenuml/,''));
     host.innerHTML=`<svg xmlns="http://www.w3.org/2000/svg" width="${original.width}" height="${original.height}" viewBox="${original.viewBox}">${original.innerSvg}</svg>`;
     snapshot={zenumlCore:pure(Object.fromEntries(Object.entries(original).filter(([k])=>k!=='innerSvg')))};
    }else{
     diagram=await mermaid.mermaidAPI.getDiagramFromText(item.source);
     for(const name of ['getData','getClasses','getRelations','getStates','getRootDoc','getActors','getMessages','getSections','getTasks','getItems','getCommits','getBranches','getSubGraphs','getVertices','getEdges','getDirection','getDiagramTitle','getAccTitle','getAccDescription']){
      if(typeof diagram.db[name]!=='function')continue;
      try{snapshot[name]=pure(diagram.db[name]());}catch(error){snapshot[name]={$getterError:String(error)}}
     }
     // render() clears diagram scope in finally. Observe its actual scoped
     // configuration when the original renderer creates its SVG/iframe, while
     // forwarding every DOM call and leaving all layout/paint untouched.
     const createNS=Document.prototype.createElementNS,create=Document.prototype.createElement;
     Document.prototype.createElementNS=function(namespace,name,...args){
      if(!renderConfig&&namespace==='http://www.w3.org/2000/svg'&&String(name).toLowerCase()==='svg')renderConfig=pure(mermaid.mermaidAPI.getConfig());
      return createNS.call(this,namespace,name,...args);
     };
     Document.prototype.createElement=function(name,...args){
      if(!renderConfig&&String(name).toLowerCase()==='iframe')renderConfig=pure(mermaid.mermaidAPI.getConfig());
      return create.call(this,name,...args);
     };
     let output;
     try{output=await mermaid.render('bulk_'+item.id.replace(/[^a-zA-Z0-9_]/g,'_'),item.source);}
     finally{Document.prototype.createElementNS=createNS;Document.prototype.createElement=create;}
     host.innerHTML=output.svg;
     if(!host.querySelector('svg')){
      const frame=host.querySelector('iframe'),encoded=frame?.getAttribute('src')?.match(/^data:text\/html[^,]*;base64,(.*)$/s);
      if(!encoded)throw Error('No SVG or recognized sandbox transport');
      originalOutput=output.svg;const template=document.createElement('template');
      template.innerHTML=new TextDecoder().decode(Uint8Array.from(atob(encoded[1]),c=>c.charCodeAt(0)));
      const svg=template.content.querySelector('svg');if(!svg)throw Error('Sandbox without SVG');
      host.replaceChildren(svg);transport={kind:'sandbox-iframe-base64',unwrappedForScreenshot:true};
     }
    }
    await document.fonts.ready;for(const img of host.querySelectorAll('img'))await img.decode();
    for(const animation of document.getAnimations()){animation.pause();animation.currentTime=0;}
    const svg=host.querySelector('svg'),rect=svg.getBoundingClientRect();
    const box=e=>{const b=e.getBoundingClientRect();return {x:b.x-rect.x,y:b.y-rect.y,width:b.width,height:b.height}};
    const shapes=[...svg.querySelectorAll('path,rect,circle,ellipse,polygon,polyline,line,image')].filter(e=>!e.closest('defs,clipPath,mask')).map(e=>{
     const s=getComputedStyle(e);return {tag:e.tagName,id:e.id,classes:e.getAttribute('class'),box:box(e),d:e.getAttribute('d'),
      points:e.getAttribute('points'),fill:s.fill,stroke:s.stroke,strokeWidth:s.strokeWidth,opacity:s.opacity,display:s.display,
      visibility:s.visibility,filter:s.filter,strokeDasharray:s.strokeDasharray,markerStart:e.getAttribute('marker-start'),markerEnd:e.getAttribute('marker-end')};
    });
    const texts=[...svg.querySelectorAll('text,foreignObject')].filter(e=>!e.closest('defs')).map(e=>{
     const s=getComputedStyle(e);return {text:e.tagName==='foreignObject'?(e.innerText||e.textContent):e.textContent,box:box(e),fontFamily:s.fontFamily,fontSize:s.fontSize,fontWeight:s.fontWeight,textAnchor:s.textAnchor,dominantBaseline:s.dominantBaseline,fill:s.fill,display:s.display,visibility:s.visibility};
    });
    return {kind:diagram?.type||item.kind,snapshot,config:renderConfig||pure(mermaid.mermaidAPI.getConfig()),transport,originalOutput,
     configurationCapture:renderConfig?'read-only observation at original SVG/iframe creation':'unscoped core configuration (ZenUML core does not consume Mermaid palette)',
     snapshotSerialization:{maximumDepth:16,maximumEntries:20000,referenceMarkers:true},
     layoutLoaders:{tidyTreeRegistered:true,tidyTreeInvocations:globalThis.__bulkTidyLoads},
     svg:svg.outerHTML,shapes,texts,viewport:{width:rect.width,height:rect.height}};
    }catch(error){
     // Return only explicit scalar grammar-location fields. Letting Playwright
     // serialize Mermaid's thrown parser object can itself overflow on yy/AST.
     const hash=error?.hash,loc=hash?.loc;
     return {$captureError:{message:String(error?.message||error),name:String(error?.name||'Error'),stack:String(error?.stack||''),
      hash:hash?{text:String(hash.text??''),token:String(hash.token??''),line:hash.line,
       expected:Array.isArray(hash.expected)?hash.expected.map(String):undefined,
       loc:loc?{first_line:loc.first_line,last_line:loc.last_line,first_column:loc.first_column,last_column:loc.last_column}:undefined}:undefined}};
    }
   },item),60000);
   if(result.$captureError){const error=Error(result.$captureError.message);error.sourceError=result.$captureError;throw error;}
   if(item.kind==='mindmap'&&result.config?.layout==='tidy-tree'&&!result.layoutLoaders?.tidyTreeInvocations)
    throw Error('Oracle transport failed to invoke the explicitly requested canonical tidy-tree provider');
   fs.writeFileSync(path.join(out,item.id+'.svg'),result.svg);delete result.svg;
   if(result.originalOutput)fs.writeFileSync(path.join(out,item.id+'.sandbox.html'),result.originalOutput);delete result.originalOutput;
   result.blockedRequests=network;result.pageErrors=pageErrors;save(path.join(out,item.id+'.json'),result);
   await page.locator('#host > svg').screenshot({path:path.join(out,item.id+'.png'),timeout:30000});
   manifest.cases.push({id:item.id,kind:item.kind,expect:item.expect,status:'captured',blockedRequests:network});
  }catch(error){
   const result={id:item.id,kind:item.kind,status:'error',expect:item.expect,message:String(error),stack:error.stack,sourceError:error.sourceError,blockedRequests:network,pageErrors};
   save(path.join(out,item.id+'.error.json'),result);manifest.cases.push(result);
  }finally{await page.close();}
  save(path.join(out,'manifest.partial.json'),manifest);
  console.log(JSON.stringify(manifest.cases.at(-1)));
 }}finally{await browser.close();save(path.join(out,'manifest.json'),manifest);}
}
main().catch(error=>{console.error(error.stack||error);process.exitCode=1});
