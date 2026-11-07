/* Fixed-source closure observations, development only. Never Python expected. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),cp=require('node:child_process');
const {createRequire}=require('node:module');
const root=path.resolve(__dirname,'../..');
const req=createRequire(path.join(root,'.local/f011-oracle/package.json'));
const arg=n=>{const i=process.argv.indexOf(n);return i<0?null:process.argv[i+1];};
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const identity=p=>{const b=fs.readFileSync(p);return{path:p,bytes:b.length,sha256:sha(b)};};
const get=(data,keys)=>keys.reduce((value,key)=>value[key],data);
async function timed(promise){
 let timer;
 try{return await Promise.race([promise,new Promise((resolve,reject)=>{timer=setTimeout(()=>reject(Error('Fixed-source observation timed out after 20s')),20000);})]);}
 finally{clearTimeout(timer);}
}
async function main(){
 const fixtures=path.resolve(arg('--fixtures')||path.join(root,'tests/closure/cases-A.json'));
 if(!arg('--out'))throw Error('--fixtures FILE --out NEWDIR required');
 const out=path.resolve(arg('--out'));if(fs.existsSync(out))throw Error('New output directory required');
 cp.execFileSync(process.execPath,[path.join(root,'tools/oracle/bulk_capture.cjs'),'--verify-only','--out',out],{stdio:'inherit'});
 const sourceIdentity=JSON.parse(fs.readFileSync(path.join(out,'identity.json'),'utf8'));
 const input=JSON.parse(fs.readFileSync(fixtures,'utf8'));fs.copyFileSync(fixtures,path.join(out,'fixtures.json'));
 const {chromium}=req('playwright');const browser=await chromium.launch({headless:true});
 const result={schema:'py-mermaid-closure-A-source/v1',fixture:identity(fixtures),sourceIdentity,
  browserPolicy:'Bundled isolated Playwright Chromium; not user Chrome',cases:[],errors:[],geometryControls:[]};
 try{
  for(const item of input.cases){
   const page=await browser.newPage({viewport:{width:1200,height:900},deviceScaleFactor:1});
   const row={id:item.id,source:item.source,config:item.config,accepted:false,errors:[]};
   try{
    const zen=path.join(root,'.local/bulk-sources/zenuml/package/dist');
    await page.route('**/*',route=>{
     const url=new URL(route.request().url());
     if(url.origin==='http://closure-a.local'&&url.pathname==='/index.html')return route.fulfill({contentType:'text/html',body:'<!doctype html><html><head><base href="http://closure-a.local/zen/"></head><body></body></html>'});
     if(url.origin==='http://closure-a.local'&&url.pathname.startsWith('/zen/')){
      const file=path.resolve(zen,decodeURIComponent(url.pathname.slice(5)));
      if(file.startsWith(zen+path.sep)&&fs.existsSync(file)&&fs.statSync(file).isFile())return route.fulfill({body:fs.readFileSync(file),contentType:file.endsWith('.woff2')?'font/woff2':'application/javascript'});
     }
     return route.abort();
    });
    // Zen UMD needs a nonopaque local origin for localStorage initialization.
    // It is a separate fixed upstream core, not a registered Mermaid detector.
    await page.goto('http://closure-a.local/index.html');await page.addScriptTag({path:path.join(root,'.local/f011-oracle/node_modules/mermaid/dist/mermaid.js')});
    if(item.kind==='zenuml')await page.addScriptTag({path:path.join(zen,'zenuml.js')});
    const observed=await timed(page.evaluate(async item=>{
     mermaid.initialize({startOnLoad:false,...item.config});
     const pure=(value,seen=new WeakSet())=>{
      if(value===null||typeof value!=='object')return typeof value==='function'?undefined:value;
      if(seen.has(value))return{$ref:true};seen.add(value);
      if(value instanceof Map)return Object.fromEntries([...value].map(([k,v])=>[k,pure(v,seen)]));
      if(value instanceof Set)return [...value].map(v=>pure(v,seen));
      if(Array.isArray(value))return value.map(v=>pure(v,seen));
      return Object.fromEntries(Object.entries(value).filter(([,v])=>typeof v!=='function').map(([k,v])=>[k,pure(v,seen)]));
     };
     try{
      if(item.kind==='zenuml'){
       globalThis.__closureZen=await zenuml.renderToSvg(item.source.replace(/^\s*zenuml/,''));
       return {accepted:true,snapshot:{}};
      }
      const diagram=await mermaid.mermaidAPI.getDiagramFromText(item.source),snapshot={};
      for(const name of ['getDomains','getTransitions','getDiagramTitle','getAccTitle','getAccDescription','getData']){
       if(typeof diagram.db[name]==='function')snapshot[name]=pure(diagram.db[name]());
      }
      return {accepted:true,snapshot};
     }catch(error){return {accepted:false,parseError:String(error)};}
    },item));
    Object.assign(row,observed);
    if(row.accepted!==(item.expect!=='syntax_error'))row.errors.push('SOURCE_ACCEPTANCE_EXPECTATION_MISMATCH');
    if(row.accepted){
     for(const check of item.sourceChecks||[]){
      try{const actual=get(row.snapshot,check.path);if(JSON.stringify(actual)!==JSON.stringify(check.equals))row.errors.push('SOURCE_VALUE_EXPECTATION_MISMATCH '+JSON.stringify({path:check.path,expected:check.equals,actual}));}
      catch(error){row.errors.push('SOURCE_VALUE_PROBE_ERROR '+String(error));}
     }
     if(item.commentExpected||item.geometryControl){
      const rendered=await timed(page.evaluate(async item=>{
       let svg;
       if(item.kind==='zenuml'){
        const original=globalThis.__closureZen;
        svg=`<svg xmlns="http://www.w3.org/2000/svg" width="${original.width}" height="${original.height}" viewBox="${original.viewBox}">${original.innerSvg}</svg>`;
       }else ({svg}=await mermaid.render('closure_'+item.id.replace(/[^\w]/g,'_'),item.source));
       document.body.innerHTML=svg;await document.fonts.ready;
       const element=document.querySelector('svg');element.style.background='white';
       let comment=null,geometry=null;
       if(item.commentExpected){
        const text=element.querySelector('text.comment-text');if(!text)throw Error('Source comment-text missing');
        comment={visible:text.textContent,italic:!!text.querySelector('[font-style="italic"]')};
       }
       if(item.geometryControl){
        const rect=[...element.querySelectorAll('rect')].find(r=>r.parentElement.textContent.includes('Shell')&&r.parentElement.querySelector(':scope > rect')===r);
        if(!rect)throw Error('Source C4 boundary rect missing');
        const label=[...rect.parentElement.querySelectorAll('text,foreignObject')].find(t=>t.textContent.trim()==='Shell');
        if(!label)throw Error('Source C4 Shell label missing');
        const box=rect.getBBox(),textBox=label.getBBox();
        geometry={x:box.x,y:box.y,width:box.width,height:box.height,labelRelativeTop:textBox.y-box.y,imageCount:element.querySelectorAll('image').length};
       }
       return {svg,comment,geometry};
      },item));
      Object.assign(row,{comment:rendered.comment,geometry:rendered.geometry});
      fs.writeFileSync(path.join(out,item.id+'.svg'),rendered.svg);
      await page.locator('body > svg').screenshot({path:path.join(out,item.id+'.png')});
      if(item.commentExpected&&(row.comment.visible!==item.commentExpected.visible||row.comment.italic!==item.commentExpected.italic))row.errors.push('SOURCE_COMMENT_EXPECTATION_MISMATCH');
     }
    }
   }catch(error){row.toolError=String(error.stack||error);row.errors.push('SOURCE_TOOL_ERROR');}
   finally{await page.close();}
   fs.writeFileSync(path.join(out,item.id+'.json'),JSON.stringify(row,null,2)+'\n');result.cases.push(row);
  }
 }finally{await browser.close();}
 const baseline=result.cases.find(c=>c.id==='CLOSURE-A-c4-boundary-base')?.geometry;
 const sprite=result.cases.find(c=>c.id==='CLOSURE-A-c4-boundary-unknown-sprite')?.geometry;
 const geometry={id:'source-boundary-unknown-sprite48',baseline,sprite,errors:[]};
 if(!baseline||!sprite)geometry.errors.push('SOURCE_C4_GEOMETRY_MISSING');
 else{
  if(Math.abs(sprite.labelRelativeTop-baseline.labelRelativeTop-48)>.05)geometry.errors.push('SOURCE_LABEL_RESERVATION_NOT48');
  if(Math.abs(sprite.width-baseline.width)>.05||Math.abs(sprite.height-baseline.height)>.05)geometry.errors.push('SOURCE_BOUNDARY_EXTENT_CHANGED');
  if(sprite.imageCount!==0)geometry.errors.push('SOURCE_UNEXPECTED_SPRITE_IMAGE');
 }
 result.geometryControls.push(geometry);
 result.errors=[...result.cases.flatMap(row=>row.errors.map(error=>({id:row.id,error}))),...geometry.errors.map(error=>({id:geometry.id,error}))];
 result.status=result.errors.length?'FAIL':'PASS';
 fs.writeFileSync(path.join(out,'results.json'),JSON.stringify(result,null,2)+'\n');
 console.log(JSON.stringify({status:result.status,cases:result.cases.length,errors:result.errors}));process.exitCode=result.errors.length?1:0;
}
main().catch(error=>{console.error(error.stack);process.exitCode=1;});
