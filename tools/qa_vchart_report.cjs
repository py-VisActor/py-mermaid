/* Existing Playwright Chromium; reads raw report bytes, never renders charts. */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),http=require('node:http');
const {createRequire}=require('node:module');
const root=path.resolve(__dirname,'..');
const req=createRequire(path.join(root,'.local/f011-oracle/package.json'));
const arg=n=>{const i=process.argv.indexOf(n);return i<0?null:process.argv[i+1];};
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const same=(b,id)=>b.length===id.bytes&&sha(b)===id.sha256;
async function main(){
 const report=arg('--report'),out=arg('--out');if(!report||!out)throw Error('--report DIR --out NEWDIR required');
 const folder=path.resolve(report),output=path.resolve(out);fs.mkdirSync(output,{recursive:false});
 const manifest=JSON.parse(fs.readFileSync(path.join(folder,'manifest.json'),'utf8'));
 const qa={schema:'py-mermaid-vchart-report-qa/v1',status:'RUNNING',purpose:manifest.purpose,
   functionalStatus:'NOT_REEVALUATED',sourceRun:manifest.sourceRun,errors:[],pages:[],screenshots:[],requests:[],rawAssetsVerified:0};
 const check=(ok,msg)=>{if(!ok)qa.errors.push(msg);};
 let browser,server;
 try{
  check(manifest.pageSize===12,'pageSize must be12');
  check(manifest.cases.length===335,'complete225+68+42 case denominator');
  const counts=Object.fromEntries(['supplier','bridge','mermaid'].map(g=>[g,manifest.cases.filter(c=>c.group===g).length]));
  check(JSON.stringify(counts)===JSON.stringify({supplier:225,bridge:68,mermaid:42}),'group denominators');
  check(new Set(manifest.cases.map(c=>c.group+':'+c.id.toLowerCase())).size===335,'duplicate case ID');
  const index=fs.readFileSync(path.join(folder,'index.html'));check(same(index,manifest.index),'index SHA drift');
  check(!index.toString().includes('<article class="case"'),'index must not inline335 cards');
  check(index.toString().includes('PyPI')&&index.toString().includes('invalid-publisher'),'PyPIblocked scope absent');
  if(manifest.purpose==='REHEARSAL_OLD_CANDIDATE_NOT_ACCEPTANCE')check(index.toString().includes('旧候选报告预演'),'rehearsal label missing');
  let png=0,svg=0;
  for(const [relative,id]of Object.entries(manifest.assets)){
   const absolute=path.resolve(folder,relative);check(absolute.startsWith(folder+path.sep),'asset escapes report');
   const bytes=fs.readFileSync(absolute);check(same(bytes,id),'raw file fingerprint '+relative);
   check(same(fs.readFileSync(id.sourcePath),id),'raw source copy differs '+relative);
   if(relative.endsWith('.png')||relative.endsWith('.svg')){
    check(!!id.originalRunProof,'image lacks original closedRun binding '+relative);
    const proof=id.originalRunProof;
    if(proof){check(same(bytes,proof),'raw originalRun image differs '+relative);check(same(fs.readFileSync(path.join(proof.run,'run.json')),proof.manifest),'originalRun manifest drift');}
   }
   if(relative.endsWith('.png'))png++;if(relative.endsWith('.svg'))svg++;qa.rawAssetsVerified++;
  }
  // Mutation controls operate on metadata/bytes in memory, never on originals.
  const first=Object.keys(manifest.assets)[0],firstBytes=fs.readFileSync(path.join(folder,first));
  qa.negativeControls={changedHashRejected:!same(firstBytes,{...manifest.assets[first],sha256:'0'.repeat(64)}),
    missingCaseRejected:manifest.cases.slice(1).length!==335,
    repeatedCaseRejected:new Set([...manifest.cases,manifest.cases[0]].map(c=>c.group+':'+c.id)).size!==manifest.cases.length+1};
  check(Object.values(qa.negativeControls).every(Boolean),'report fault control failed');
  if(!arg('--url'))server=http.createServer((request,response)=>{
   try{
    const name=decodeURIComponent(new URL(request.url,'http://127.0.0.1').pathname);
    const target=path.resolve(folder,'.'+name);if(!target.startsWith(folder+path.sep)&&target!==folder)throw Error('path escape');
    const file=target===folder?path.join(folder,'index.html'):target;
    const types={'.html':'text/html; charset=utf-8','.json':'application/json','.png':'image/png','.svg':'image/svg+xml','.pdf':'application/pdf'};
    response.writeHead(200,{'Content-Type':types[path.extname(file)]||'application/octet-stream'});response.end(fs.readFileSync(file));
   }catch(error){response.writeHead(404);response.end('not found');}
  });
  if(server)await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const base=arg('--url')?new URL('.',arg('--url')).href:'http://127.0.0.1:'+server.address().port+'/';qa.url=base;
  const httpIndex=Buffer.from(await(await fetch(new URL('index.html',base))).arrayBuffer());
  check(same(httpIndex,manifest.index),'HTTP index fingerprint differs');
  qa.receiptsVerified=0;
  for(const receipt of Object.values(manifest.attachments||{})){
   const bytes=fs.readFileSync(path.join(folder,receipt.path));check(same(bytes,receipt),'receipt file fingerprint');
   const served=Buffer.from(await(await fetch(new URL(receipt.path,base))).arrayBuffer());check(same(served,receipt),'receipt HTTP fingerprint');qa.receiptsVerified++;
  }
  const queue=Object.entries(manifest.assets);qa.httpRawAssetsVerified=0;
  await Promise.all(Array.from({length:12},async()=>{
   while(queue.length){const [name,id]=queue.pop(),response=await fetch(new URL(name,base));
    check(response.ok,'raw asset HTTP '+name);const bytes=Buffer.from(await response.arrayBuffer());
    check(same(bytes,id),'raw asset HTTP fingerprint '+name);qa.httpRawAssetsVerified++;
   }
  }));
  browser=await req('playwright').chromium.launch({headless:true});
  qa.browser=browser.version();qa.browserPolicy='Existing bundled Playwright Chromium, isolated temporary profile; not user Chrome';
  const page=await browser.newPage({viewport:{width:1440,height:1000},deviceScaleFactor:1});
  page.on('pageerror',e=>qa.errors.push('pageerror '+e.message));
  await page.route('**/*',route=>{
   const u=route.request().url();if(new URL(u).origin!==new URL(base).origin){qa.errors.push('external request '+u);return route.abort();}
   if(u.endsWith('/favicon.ico'))return route.fulfill({status:204,body:''});return route.continue();
  });
  page.on('request',r=>qa.requests.push(r.url()));
  await page.goto(base,{waitUntil:'domcontentloaded'});
  check(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),'desktop index overflow');
  check(await page.locator('a[href$=".html"]').count()===manifest.pages.length,'index links/page denominator');
  const firstHref=await page.locator('a[href$=".html"]').first().getAttribute('href');
  await page.locator('a[href$=".html"]').first().click();await page.waitForURL(new URL(firstHref,base).href);
  await page.locator('nav a[href="index.html"]').first().click();await page.waitForURL(new URL('index.html',base).href);
  await page.screenshot({path:path.join(output,'index-desktop.png'),fullPage:true});qa.screenshots.push('index-desktop.png');
  for(const entry of manifest.pages){
   const bytes=Buffer.from(await(await fetch(new URL(entry.path,base))).arrayBuffer());
   check(same(bytes,entry.report),'HTTP page fingerprint '+entry.path);
   await page.goto(new URL(entry.path,base).href,{waitUntil:'domcontentloaded'});
   const cases=manifest.cases.filter(c=>c.page===entry.path);
   check(cases.length===entry.cases&&cases.length<=12,'page count '+entry.path);
   check(await page.locator('.case').count()===cases.length,'DOM card count '+entry.path);
   const actual=await page.locator('.case').evaluateAll(nodes=>nodes.map(n=>({id:n.dataset.case,status:n.dataset.status,group:n.dataset.group,anchor:n.id})));
   check(JSON.stringify(actual)===JSON.stringify(cases.map(c=>({id:c.id,status:c.status,group:c.group,anchor:c.anchor}))),'case/status preservation '+entry.path);
   await page.locator('img').evaluateAll(async images=>{for(const i of images)i.loading='eager';await Promise.all(images.map(i=>i.decode()));});
   check(await page.locator('img').evaluateAll(imgs=>imgs.every(i=>i.naturalWidth>0&&i.naturalHeight>0)),'broken image '+entry.path);
   check(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),'desktop overflow '+entry.path);
   qa.pages.push({path:entry.path,cases:cases.length,images:await page.locator('img').count()});
  }
  for(const group of ['supplier','bridge','mermaid']){
   const entry=manifest.pages.find(p=>p.group===group);await page.goto(new URL(entry.path,base).href,{waitUntil:'domcontentloaded'});
   await page.locator('.case img').first().evaluate(i=>i.decode());
   await page.locator('.case').first().screenshot({path:path.join(output,group+'-desktop.png')});qa.screenshots.push(group+'-desktop.png');
   await page.setViewportSize({width:390,height:844});
   check(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),'mobile overflow '+group);
   await page.locator('.case').first().screenshot({path:path.join(output,group+'-mobile.png')});qa.screenshots.push(group+'-mobile.png');
   await page.locator('.case details').first().locator('summary').click();
   check(await page.locator('.case details').first().getAttribute('open')!==null,'details not interactive '+group);
   check(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),'mobile raw-details overflow '+group);
   await page.setViewportSize({width:1440,height:1000});
  }
  await page.goto(base,{waitUntil:'domcontentloaded'});await page.setViewportSize({width:390,height:844});
  check(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),'mobile index overflow');
  await page.screenshot({path:path.join(output,'index-mobile.png'),fullPage:true});qa.screenshots.push('index-mobile.png');
  qa.rawPNGVerified=png;qa.rawSVGVerified=svg;qa.caseCount=manifest.cases.length;
 }catch(error){qa.errors.push(String(error.stack||error));}
 finally{
  if(browser)await browser.close();if(server)await new Promise(resolve=>server.close(resolve));
  qa.status=qa.errors.length?'FAIL':'PASS';fs.writeFileSync(path.join(output,'viewer.json'),JSON.stringify(qa,null,2)+'\n');
 }
 console.log(JSON.stringify({status:qa.status,cases:qa.caseCount,pages:qa.pages.length,rawAssetsVerified:qa.rawAssetsVerified,errors:qa.errors}));
 process.exitCode=qa.errors.length?1:0;
}
main().catch(e=>{console.error(e.stack);process.exitCode=1;});
