/* Fixed-source closure observations, never a production dependency.
 * --fixtures FILE --out NEWDIR [--timezone UTC] [--browser]
 * Requires --experimental-vm-modules for the independently pinned old helper.
 */
'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),cp=require('node:child_process'),vm=require('node:vm');
const {createRequire}=require('node:module');
const root=path.resolve(__dirname,'../..'),dep=path.join(root,'.local/f011-oracle');
const arg=n=>{const i=process.argv.indexOf(n);return i<0?null:process.argv[i+1];};
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const MAP='8b844955879bad4b284a9603827b8268f11ecb57cd0fbf2f338c24e2afa99679';
const BUNDLE='ffd1a76f0553952a344c68a9b1502dd5cfb6faab72541307b74679c5abc9cec8';
const save=(p,v)=>fs.writeFileSync(p,JSON.stringify(v,null,2)+'\n');
function serialized(d){return Number.isFinite(+d)?{local:[d.getFullYear(),d.getMonth()+1,d.getDate(),d.getHours(),d.getMinutes(),d.getSeconds(),d.getMilliseconds()],epochMs:+d}:null;}
function date(a){const d=new Date(0);d.setFullYear(a[0],(a[1]||1)-1,a[2]||1);d.setHours(a[3]||0,a[4]||0,a[5]||0,a[6]||0);return d;}
async function main(){
 const fixtures=path.resolve(arg('--fixtures')||''),out=path.resolve(arg('--out')||'');if(!arg('--fixtures')||!arg('--out'))throw Error('--fixtures and --out required');
 fs.mkdirSync(out,{recursive:false});const doc=JSON.parse(fs.readFileSync(fixtures,'utf8'));
 const bundlePath=path.join(dep,'node_modules/mermaid/dist/mermaid.js'),mapPath=bundlePath+'.map';
 const bundle=fs.readFileSync(bundlePath),mapBytes=fs.readFileSync(mapPath);if(sha(bundle)!==BUNDLE||sha(mapBytes)!==MAP)throw Error('Fixed bundle/map source drift');
 const timezone=arg('--timezone')||'UTC';process.env.TZ=timezone;
 const legacy=path.join(root,'tests/branch_verification/oracle_b.cjs');
 cp.execFileSync(process.execPath,[...process.execArgv,legacy,'--fixtures',fixtures,'--out',path.join(out,'values')],{env:{...process.env,TZ:timezone},stdio:'inherit'});
 const map=JSON.parse(mapBytes),used=[];
 function umd(ending){const indices=map.sources.map((n,i)=>n.includes('/dayjs@1.11.21/')&&n.endsWith(ending)?i:-1).filter(i=>i>=0);if(indices.length!==1)throw Error('Source module not unique '+ending);const i=indices[0],source=map.sourcesContent[i],module={exports:{}};used.push({path:map.sources[i],sha256:sha(Buffer.from(source))});vm.runInNewContext(source,{module,exports:module.exports,Date,Math});return module.exports;}
 const dayjs=umd('dayjs/dayjs.min.js');for(const name of ['isoWeek','customParseFormat','advancedFormat','duration'])dayjs.extend(umd('dayjs/plugin/'+name+'.js'));
 const extras=[];
 for(const row of doc.sourceProbes){
  const oldTZ=process.env.TZ;process.env.TZ=row.timezone||timezone;let value=null,error=null;
  try{
   if(row.kind==='browserFallback'){const d=new Date(row.input.value.trim());value=Number.isFinite(+d)&&d.getFullYear()>=-10000&&d.getFullYear()<=10000?serialized(d):null;}
   else if(row.kind==='dayAdd'){const base=dayjs(date(row.input.date)),calendar=base.add(1,'day'),elapsed=base.add(24,'hour');value={base:serialized(base.toDate()),calendar:serialized(calendar.toDate()),elapsed:serialized(elapsed.toDate()),calendarHours:(+calendar-+base)/3600000,calendarLocalHour:calendar.hour(),elapsedLocalHour:elapsed.hour()};}
   else throw Error('Unknown source operation '+row.kind);
  }catch(e){error={name:e.name,message:String(e.message),stack:String(e.stack)};}
  extras.push({id:row.id,kind:row.kind,input:row.input,timezone:process.env.TZ,value,error});process.env.TZ=oldTZ;
 }
 save(path.join(out,'source-extra.json'),{schema:'py-mermaid-closure-B-source/v1',fixtureSha256:sha(fs.readFileSync(fixtures)),identity:{commit:'1fb7869866dd619168d840291c9c54b4f129758b',bundleSha256:BUNDLE,mapSha256:MAP,modules:used,legacyOracleSha256:sha(fs.readFileSync(legacy))},timezone,rows:extras});
 if(!process.argv.includes('--browser'))return;
 const needle='graph = await elk.layout(elkGraph);';const source=bundle.toString('utf8');if(source.split(needle).length!==2)throw Error('ELK observation boundary changed');
 // Observation only: copy the actual immutable request before the real call.
 // Every original algorithm/option/return/exception statement remains intact.
 const inserted='globalThis.__closureElkInputs.push(JSON.parse(JSON.stringify(elkGraph))); '+needle+' globalThis.__closureElkOutputs.push(JSON.parse(JSON.stringify(graph)));';
 const instrumented=source.replace(needle,inserted);
 const identity={bundleSha256:BUNDLE,mapSha256:MAP,instrumentedSha256:sha(Buffer.from(instrumented)),needle,inserted,change:'Only JSON snapshots immediately before/after actual elk.layout; no algorithm replacement'};
 const req=createRequire(path.join(dep,'package.json')),browser=await req('playwright').chromium.launch({headless:true});
 const results=[];
 try{for(const item of doc.cases){
  const page=await browser.newPage({viewport:{width:1600,height:1200},deviceScaleFactor:1,timezoneId:item.closure?.timezone||timezone,locale:'en-US'});
  const blocked=[];await page.route('**/*',route=>{if(route.request().url()==='http://closure.local/')return route.fulfill({contentType:'text/html',body:'<div id="host"></div>'});blocked.push(route.request().url());return route.abort();});
  await page.goto('http://closure.local/');await page.addScriptTag({content:instrumented});
  let result;
  try{
   result=await page.evaluate(async item=>{
    try{
    globalThis.__closureElkInputs=[];globalThis.__closureElkOutputs=[];
    mermaid.initialize({startOnLoad:false,...item.config});const diagram=await mermaid.mermaidAPI.getDiagramFromText(item.source);
    const data=diagram.db.getData?.();
    let snapshot=data?{nodes:data.nodes?.map(n=>({id:n.id,label:n.label,parentId:n.parentId,isGroup:n.isGroup,shape:n.shape,metadata:n.metadata})),edges:data.edges?.map(e=>({id:e.id,start:e.start,end:e.end})),direction:data.direction}:null;
    if(item.kind==='gantt'){
     const dateValue=d=>d&&Number.isFinite(+d)?{local:[d.getFullYear(),d.getMonth()+1,d.getDate(),d.getHours(),d.getMinutes(),d.getSeconds(),d.getMilliseconds()],epochMs:+d}:null;
     snapshot={tasks:diagram.db.getTasks().map(t=>({id:t.id,start:dateValue(t.startTime),end:dateValue(t.endTime)}))};
    }
    const svg=await mermaid.render('closure_'+item.id.replace(/[^A-Za-z0-9_]/g,'_'),item.source);document.getElementById('host').innerHTML=svg.svg;await document.fonts.ready;
    const root=document.querySelector('#host svg');if(!root)throw Error('Original did not return SVG');
    const box=e=>{const b=e.getBBox();return {x:b.x,y:b.y,width:b.width,height:b.height};};
    const groups=[...root.querySelectorAll('g')].filter(e=>/branch|commit|tag/.test(e.getAttribute('class')||''));
    const labels=groups.map(e=>({classes:e.getAttribute('class'),transform:e.getAttribute('transform'),box:box(e),text:e.textContent,children:[...e.children].map(c=>({tag:c.tagName,classes:c.getAttribute('class'),transform:c.getAttribute('transform'),x:c.getAttribute('x'),y:c.getAttribute('y'),width:c.getAttribute('width'),height:c.getAttribute('height'),text:c.textContent,box:box(c)}))}));
    const texts=[...root.querySelectorAll('text,foreignObject')].map(e=>({text:e.textContent,box:box(e),classes:e.getAttribute('class')}));
    const rootRect=root.getBoundingClientRect();
    const primitive=e=>{
      const s=getComputedStyle(e),r=e.getBoundingClientRect();
      const numeric={};for(const k of ['cx','cy','r','rx','ry','x1','y1','x2','y2','x','y','width','height'])
        if(e.hasAttribute(k))numeric[k]=e.getAttribute(k);
      return {tag:e.tagName.toLowerCase(),classes:e.getAttribute('class')||'',text:e.textContent,
        fill:s.fill,stroke:s.stroke,strokeWidth:s.strokeWidth,opacity:s.opacity,
        fillOpacity:s.fillOpacity,strokeOpacity:s.strokeOpacity,numeric,
        screenBox:{x:r.x-rootRect.x,y:r.y-rootRect.y,width:r.width,height:r.height}};
    };
    const publicPaint={
      ticks:[...root.querySelectorAll('.tick text')].map(primitive),
      cherries:[...root.querySelectorAll('.commit-cherry-pick')].filter(e=>['circle','line'].includes(e.tagName.toLowerCase())).map(primitive),
      collapsed:[...root.querySelectorAll('.flow-collapsed,.collapsed-indicator,.collapsed-separator')].map(primitive)
    };
    return {snapshot,elkInputs:globalThis.__closureElkInputs,elkOutputs:globalThis.__closureElkOutputs,labels,texts,publicPaint,svg:root.outerHTML};
    }catch(error){return {sourceException:{name:String(error?.name||'Error'),message:String(error?.message||error),stack:String(error?.stack||'')}};}
   },item);
   if(result.sourceException){const error=new Error(result.sourceException.message);error.name=result.sourceException.name;error.stack=result.sourceException.stack;throw error;}
   const file=path.join(out,item.id);fs.writeFileSync(file+'.svg',result.svg);delete result.svg;await page.locator('#host svg').screenshot({path:file+'.png'});
   result={id:item.id,source:item.source,config:item.config,timezone:item.closure?.timezone||timezone,status:'CAPTURED',...result,blockedRequests:blocked};
  }catch(error){result={id:item.id,source:item.source,config:item.config,status:'SOURCE_ERROR',error:{name:error.name,message:String(error.message),stack:String(error.stack)},blockedRequests:blocked};}
  save(path.join(out,item.id+'.json'),result);results.push({id:item.id,status:result.status});await page.close();
 }}finally{await browser.close();}
 save(path.join(out,'browser-manifest.json'),{schema:'py-mermaid-closure-B-browser/v1',fixtureSha256:sha(fs.readFileSync(fixtures)),identity,results});
 if(results.some(r=>r.status!=='CAPTURED'))process.exitCode=1;
}
main().catch(error=>{console.error(error.stack);process.exitCode=1;});
