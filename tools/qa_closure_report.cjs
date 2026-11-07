/* Read-only isolated viewer QA. No product rendering, no user browser. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),http=require('node:http');
const {createRequire}=require('node:module');
const root=path.resolve(__dirname,'..'),req=createRequire(path.join(root,'.local/f011-oracle/package.json'));
const arg=n=>{const i=process.argv.indexOf(n);return i<0?null:process.argv[i+1];};
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const same=(bytes,id)=>!!id&&bytes.length===id.bytes&&sha(bytes)===id.sha256;
function safe(base,name){const p=path.resolve(base,name);if(!p.startsWith(base+path.sep))throw Error('Path escape '+name);return p;}
async function main(){
 const report=arg('--report'),out=arg('--out');if(!report||!out)throw Error('--report DIR --out NEWDIR required');
 const folder=path.resolve(report),output=path.resolve(out);fs.mkdirSync(output,{recursive:false});
 const qa={schema:'py-mermaid-closure-report-qa/v1',status:'RUNNING',functionalStatus:'NOT_REEVALUATED',errors:[],screenshots:[],pages:[],rawAssetsVerified:0,httpAssetsVerified:0};
 const check=(ok,m)=>{if(!ok)qa.errors.push(m);};let browser,server;
 try{
  const mb=fs.readFileSync(path.join(folder,'manifest.json')),m=JSON.parse(mb);
  check(m.schema==='py-mermaid-closure-report/v1','Invalid schema');
  check(m.status==='REPORT_CREATED_NOT_NEW_ACCEPTANCE'&&m.functionalStatus==='NOT_REEVALUATED','Report invented acceptance');
  check(m.pageSize===12&&m.caseCount===m.items.length&&new Set(m.items.map(r=>r.id)).size===m.caseCount,'Invalid denominator');
  qa.candidateRun=m.candidateRun;qa.sourceTreeSha256=m.sourceTreeSha256;
  const expectedRows=m.items.map(r=>({id:r.id,status:r.status,page:r.page,anchor:r.anchor}));
  check(m.pages.every(p=>p.items>0&&p.items<=12),'Page size exceeds12');
  for(const [name,id] of Object.entries(m.assets)){
   const bytes=fs.readFileSync(safe(folder,name));check(same(bytes,id),'Local SHA '+name);
   if(!id.derived)check(same(fs.readFileSync(safe(root,id.originalPath)),id),'Original SHA '+name);
   else{
    check(id.caseId&&name.endsWith('.source'),'Unexpected derived attachment');
    const fixture=Object.entries(m.assets).find(([n,v])=>!v.derived&&v.originalPath&&v.originalPath.endsWith('.json')&&(()=>{try{return JSON.parse(fs.readFileSync(safe(folder,n))).cases?.some(c=>c.id===id.caseId&&typeof c.source==='string');}catch{return false;}})());
    check(!!fixture,'No immutable source fixture for '+id.caseId);
    if(fixture){const c=JSON.parse(fs.readFileSync(safe(folder,fixture[0]))).cases.find(c=>c.id===id.caseId);check(bytes.equals(Buffer.from(c.source,'utf8')),'Source text changed '+id.caseId);}
   }
   qa.rawAssetsVerified++;
  }
  check(same(fs.readFileSync(path.join(folder,'index.html')),m.index),'Index SHA');
  for(const p of m.pages)check(same(fs.readFileSync(safe(folder,p.path)),p),'Page SHA '+p.path);
  const first=Object.entries(m.assets)[0],buf=fs.readFileSync(safe(folder,first[0]));const changed=Buffer.concat([buf,Buffer.from('mutation')]);
  const sameRows=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
  qa.negativeControls={changedAttachmentRejected:!same(changed,first[1]),missingIDRejected:!sameRows(expectedRows,expectedRows.slice(1)),changedStatusRejected:!sameRows(expectedRows,expectedRows.map((r,i)=>i?r:{...r,status:'FALSE_PASS'})),alteredPageHashRejected:!same(fs.readFileSync(path.join(folder,'index.html')),{...m.index,sha256:'0'.repeat(64)})};
  check(Object.values(qa.negativeControls).every(Boolean),'Mutation controls failed');
  server=http.createServer((request,response)=>{try{const name=decodeURIComponent(new URL(request.url,'http://localhost').pathname);const file=safe(folder,name==='/'?'index.html':'.'+name);const ext=path.extname(file);response.writeHead(200,{'Content-Type':({'.html':'text/html; charset=utf-8','.png':'image/png','.svg':'image/svg+xml','.json':'application/json; charset=utf-8','.source':'text/plain; charset=utf-8'})[ext]||'application/octet-stream'});response.end(fs.readFileSync(file));}catch{response.writeHead(404);response.end('not found');}});
  await new Promise(r=>server.listen(0,'127.0.0.1',r));let base='http://127.0.0.1:'+server.address().port+'/';if(arg('--url')){const selected=new URL(arg('--url'));if(!['127.0.0.1','localhost','[::1]'].includes(selected.hostname)||selected.protocol!=='http:')throw Error('Only loopback HTTP report URLs are allowed');base=new URL('.',selected).href;}qa.url=base;
  const known=new Map([['manifest.json',{sha256:sha(mb),bytes:mb.length}],['index.html',m.index],...m.pages.map(p=>[p.path,p]),...Object.entries(m.assets)]);
  async function fetchCheck(name,id){const response=await fetch(new URL(name,base),{redirect:'error'});const bytes=Buffer.from(await response.arrayBuffer());check(response.ok&&same(bytes,id),'HTTP SHA '+name);qa.httpAssetsVerified++;}
  for(const [name,id]of known)await fetchCheck(name,id);
  browser=await req('playwright').chromium.launch({headless:true});qa.browser=browser.version();qa.browserPolicy='Bundled Chromium isolated temporary context; never user Chrome';
  const page=await browser.newPage({viewport:{width:1440,height:1000},deviceScaleFactor:1});
  page.on('pageerror',e=>qa.errors.push(e.message));
  await page.route('**/*',route=>{const u=new URL(route.request().url());if(u.origin!==new URL(base).origin){qa.errors.push('External request '+u.href);return route.abort();}if(u.pathname==='/favicon.ico')return route.fulfill({status:204,body:''});return route.continue();});
  const links=new Set();
  for(const entry of [{path:'index.html',items:0},...m.pages]){
   const expected=expectedRows.filter(r=>r.page===entry.path);check(entry.items===expected.length,'Page count '+entry.path);
   for(const width of [1440,390]){
    await page.setViewportSize({width,height:width===390?844:1000});await page.goto(new URL(entry.path,base).href,{waitUntil:'domcontentloaded'});
    await page.locator('img').evaluateAll(async nodes=>{
     await Promise.all(nodes.map(async n=>{
      // Changing lazy to eager schedules a request. Decode only after its
      // load event, and retain a named failure rather than a timing race.
      await new Promise((resolve,reject)=>{
       if(n.complete&&n.naturalWidth>0){resolve();return;}
       const finish=error=>{clearTimeout(timer);n.removeEventListener('load',loaded);n.removeEventListener('error',failed);error?reject(error):resolve();};
       const loaded=()=>n.naturalWidth>0?finish():failed();
       const failed=()=>finish(new Error('Image failed to load: '+n.src));
       const timer=setTimeout(()=>finish(new Error('Image load timeout: '+n.src)),30000);
       n.addEventListener('load',loaded,{once:true});n.addEventListener('error',failed,{once:true});n.loading='eager';
       if(n.complete&&n.naturalWidth>0)loaded();
      });
      try{await n.decode();}catch(error){throw new Error('Image failed to decode: '+n.src+' '+error);}
     }));
    });
    const actual=await page.locator('.case').evaluateAll(nodes=>nodes.map(n=>({id:n.dataset.case,status:n.dataset.status,anchor:n.id})));
    check(sameRows(actual,expected.map(({id,status,anchor})=>({id,status,anchor}))),'DOM ID/status mismatch '+entry.path+' '+width);
    check(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),'Overflow '+entry.path+' '+width);
    for(const url of await page.locator('a[href]').evaluateAll(ns=>ns.map(n=>n.href)))links.add(url);
    if(expected.length){await page.locator('details summary').first().click();check(await page.locator('details').first().getAttribute('open')!==null,'Details failed');check(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),'Details overflow');}
    const target=entry.path.replace('.html','')+'-'+width+'.png';await page.screenshot({path:path.join(output,target),fullPage:true});qa.screenshots.push({path:target,sha256:sha(fs.readFileSync(path.join(output,target)))});
   }
   qa.pages.push({path:entry.path,items:expected.length,viewports:[1440,390]});
  }
  for(const href of links){const u=new URL(href);check(u.origin===new URL(base).origin,'External hyperlink');const name=decodeURIComponent(u.pathname.slice(new URL(base).pathname.length));check(known.has(name),'Unbound hyperlink '+name);if(known.has(name))await fetchCheck(name,known.get(name));}
  qa.caseCount=m.caseCount;qa.linksVerified=links.size;
 }catch(e){qa.errors.push(String(e.stack||e));}
 finally{if(browser)await browser.close();if(server)await new Promise(r=>server.close(r));qa.status=qa.errors.length?'FAIL':'PASS';fs.writeFileSync(path.join(output,'viewer.json'),JSON.stringify(qa,null,2)+'\n');}
 console.log(JSON.stringify({status:qa.status,cases:qa.caseCount,errors:qa.errors}));process.exitCode=qa.errors.length?1:0;
}
main().catch(e=>{console.error(e.stack);process.exitCode=1;});
