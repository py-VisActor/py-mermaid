/* Evidence-viewer QA only; never launches user Chrome or a product renderer. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),http=require('node:http');
const {createRequire}=require('node:module');
const root=path.resolve(__dirname,'..');
const req=createRequire(path.join(root,'.local/f011-oracle/package.json'));
const arg=n=>{const i=process.argv.indexOf(n);return i<0?null:process.argv[i+1];};
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const same=(b,id)=>!!id&&b.length===id.bytes&&sha(b)===id.sha256;
function safe(base,name){const p=path.resolve(base,name);if(!p.startsWith(base+path.sep))throw Error('Path escapes root: '+name);return p;}
async function main(){
 const report=arg('--report'),out=arg('--out');if(!report||!out)throw Error('--report DIR --out NEWDIR required');
 const folder=path.resolve(report),output=path.resolve(out);fs.mkdirSync(output,{recursive:false});
 const qa={schema:'py-mermaid-final-capability-report-qa/v1',status:'RUNNING',functionalStatus:'NOT_REEVALUATED',errors:[],pages:[],screenshots:[],requests:[],rawAssetsVerified:0,httpAssetsVerified:0};
 const check=(ok,msg)=>{if(!ok)qa.errors.push(msg);};let server,browser;
 try{
  const manifestBytes=fs.readFileSync(path.join(folder,'manifest.json')),manifest=JSON.parse(manifestBytes);
  check(manifest.schema==='py-mermaid-final-capability-report/v1','Unexpected manifest schema');
  check(manifest.status==='REVIEW_COMPLETE_RELEASE_BLOCKED','Review status was upgraded');
  check(manifest.pageSize===12&&manifest.functionalStatus==='NOT_REEVALUATED','Report inferred new acceptance');
  qa.candidateRun=manifest.candidateRun;qa.sourceTreeSha256=manifest.sourceTreeSha256;
  const summaryBytes=fs.readFileSync(safe(folder,manifest.summary.path));
  check(same(summaryBytes,manifest.summary),'Summary copy SHA differs');
  check(same(fs.readFileSync(safe(root,manifest.summary.originalPath)),manifest.summary),'Original summary changed');
  const summary=JSON.parse(summaryBytes);
  check(summary.status===manifest.status&&summary.sourceTreeSha256===manifest.sourceTreeSha256&&summary.candidateRun===manifest.candidateRun,'Summary identity/status differs');
  const normalize=rows=>[...rows].map(r=>({id:r.id,status:r.status,group:r.group})).sort((a,b)=>a.id.localeCompare(b.id));
  const equalRows=(a,b)=>JSON.stringify(normalize(a))===JSON.stringify(normalize(b));
  check(equalRows(summary.items,manifest.items),'Summary item ID/status/group altered');
  check(manifest.itemCount===summary.items.length&&new Set(manifest.items.map(i=>i.id.toLowerCase())).size===manifest.items.length,'Missing/duplicate items');
  const expectedEvidence=new Map();
  for(const entry of [...(summary.evidence||[]),...summary.items.flatMap(i=>i.evidence||[])]){
   const original=path.resolve(root,entry.path);safe(root,path.relative(root,original));
   const key=path.relative(root,original).split(path.sep).join('/');
   if(expectedEvidence.has(key))check(JSON.stringify(expectedEvidence.get(key))===JSON.stringify({bytes:entry.bytes,sha256:entry.sha256}),'Conflicting evidence '+key);
   expectedEvidence.set(key,{bytes:entry.bytes,sha256:entry.sha256});
  }
  const observedEvidence=new Set();
  for(const [name,id]of Object.entries(manifest.assets)){
   const bytes=fs.readFileSync(safe(folder,name));check(same(bytes,id),'Copied asset SHA differs '+name);
   check(same(fs.readFileSync(safe(root,id.originalPath)),id),'Original asset SHA differs '+name);
   const expected=expectedEvidence.get(id.originalPath);check(same(bytes,expected),'Asset not bound to summary '+name);
   observedEvidence.add(id.originalPath);qa.rawAssetsVerified++;
  }
  check(observedEvidence.size===expectedEvidence.size&&[...expectedEvidence.keys()].every(k=>observedEvidence.has(k)),'Evidence denominator differs');
  const index=fs.readFileSync(path.join(folder,'index.html'));check(same(index,manifest.index),'Index SHA differs');
  check(index.toString().includes('仍有缺失，暂停正式发布')&&index.toString().includes('不生成新验收'),'Release blocking notice missing');
  qa.negativeControls={changedStatusRejected:!equalRows(summary.items,[{...manifest.items[0],status:'FALSE_PASS'},...manifest.items.slice(1)]),missingItemRejected:!equalRows(summary.items,manifest.items.slice(1)),changedSummaryHashRejected:!same(summaryBytes,{...manifest.summary,sha256:'0'.repeat(64)})};
  check(Object.values(qa.negativeControls).every(Boolean),'In-memory status/hash mutation controls failed');
  let base;
  if(arg('--url')){base=new URL(arg('--url'));if(!['127.0.0.1','localhost','[::1]'].includes(base.hostname))throw Error('Only loopback report URL is allowed');base=new URL('.',base).href;}
  else{
   server=http.createServer((request,response)=>{try{
    const pathname=decodeURIComponent(new URL(request.url,'http://127.0.0.1').pathname);
    const file=safe(folder,pathname==='/'?'index.html':'.'+pathname);
    const types={'.html':'text/html; charset=utf-8','.json':'application/json; charset=utf-8','.log':'text/plain; charset=utf-8','.txt':'text/plain; charset=utf-8'};
    response.writeHead(200,{'Content-Type':types[path.extname(file)]||'application/octet-stream'});response.end(fs.readFileSync(file));
   }catch(error){response.writeHead(404);response.end('not found');}});
   await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));base='http://127.0.0.1:'+server.address().port+'/';
  }
  qa.url=base;const baseURL=new URL(base);
  const fetchCheck=async(name,id)=>{const url=new URL(name,base);if(url.origin!==baseURL.origin)throw Error('External HTTP evidence URL blocked');const res=await fetch(url,{redirect:'error'});const bytes=Buffer.from(await res.arrayBuffer());check(res.ok&&same(bytes,id),'HTTP status/SHA differs '+name);qa.httpAssetsVerified++;};
  await fetchCheck('manifest.json',{bytes:manifestBytes.length,sha256:sha(manifestBytes)});
  await fetchCheck('summary.json',manifest.summary);await fetchCheck('index.html',manifest.index);
  for(const [name,id]of Object.entries(manifest.assets))await fetchCheck(name,id);
  browser=await req('playwright').chromium.launch({headless:true});qa.browser=browser.version();qa.browserPolicy='Existing bundled Chromium; isolated temporary profile; never user Chrome';
  const page=await browser.newPage({viewport:{width:1440,height:1000},deviceScaleFactor:1});
  page.on('pageerror',e=>qa.errors.push('pageerror '+e.message));page.on('request',r=>qa.requests.push(r.url()));
  await page.route('**/*',route=>{const u=new URL(route.request().url());if(u.origin!==baseURL.origin){qa.errors.push('External request blocked '+u.href);return route.abort();}if(u.pathname.endsWith('/favicon.ico'))return route.fulfill({status:204,body:''});return route.continue();});
  const links=new Set();const pageEntries=[{path:'index.html',items:0},...manifest.pages];
  check(manifest.pages.every(p=>p.items>0&&p.items<=12),'Page contains more than12 items');
  for(const entry of pageEntries){
   if(entry.path!=='index.html')await fetchCheck(entry.path,entry);
   const expected=manifest.items.filter(i=>i.page===entry.path);
   check(entry.items===expected.length,'Page item denominator differs '+entry.path);
   for(const width of [1440,390]){
    await page.setViewportSize({width,height:width===390?844:1000});await page.goto(new URL(entry.path,base).href,{waitUntil:'domcontentloaded'});
    const actual=await page.locator('.case').evaluateAll(nodes=>nodes.map(n=>({id:n.dataset.case,status:n.dataset.status,group:n.dataset.group,anchor:n.id})));
    check(JSON.stringify(actual)===JSON.stringify(expected.map(i=>({id:i.id,status:i.status,group:i.group,anchor:i.anchor}))),'DOM item/status/group mismatch '+entry.path+' '+width);
    check(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),'Horizontal overflow '+entry.path+' '+width);
    for(const href of await page.locator('a[href]').evaluateAll(nodes=>nodes.map(n=>n.href)))links.add(href);
    if(expected.length){await page.locator('.case details').first().locator('summary').click();check(await page.locator('.case details').first().getAttribute('open')!==null,'Details failed');check(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),'Opened details overflow '+entry.path+' '+width);}
    const file=entry.path.replace(/\.html$/,'')+'-'+width+'.png';await page.screenshot({path:path.join(output,file),fullPage:true});qa.screenshots.push(file);
   }
   qa.pages.push({path:entry.path,items:expected.length,viewports:[1440,390]});
  }
  // Every generated hyperlink must resolve to an exact manifest-bound file.
  const known=new Map([['index.html',manifest.index],['summary.json',manifest.summary],['manifest.json',{bytes:manifestBytes.length,sha256:sha(manifestBytes)}],...manifest.pages.map(p=>[p.path,p]),...Object.entries(manifest.assets)]);
  for(const href of links){const u=new URL(href);check(u.origin===baseURL.origin,'External link');const prefix=baseURL.pathname;check(u.pathname.startsWith(prefix),'Link escapes report URL');const name=decodeURIComponent(u.pathname.slice(prefix.length));const id=known.get(name);check(!!id,'Unrecorded link '+name);if(id)await fetchCheck(name,id);}
  qa.itemCount=manifest.items.length;qa.allLinksVerified=links.size;
 }catch(error){qa.errors.push(String(error.stack||error));}
 finally{if(browser)await browser.close();if(server)await new Promise(resolve=>server.close(resolve));qa.status=qa.errors.length?'FAIL':'PASS';fs.writeFileSync(path.join(output,'viewer.json'),JSON.stringify(qa,null,2)+'\n');}
 console.log(JSON.stringify({status:qa.status,items:qa.itemCount,pages:qa.pages.length,errors:qa.errors}));process.exitCode=qa.errors.length?1:0;
}
main().catch(error=>{console.error(error.stack);process.exitCode=1;});
