/* Read-only round-six report QA; bundled isolated Playwright, no product calls. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),http=require('node:http');
const {createRequire}=require('node:module');
const root=path.resolve(__dirname,'..');
const req=createRequire(path.join(root,'.local/f011-oracle/package.json'));
const arg=name=>{const i=process.argv.indexOf(name);return i<0?null:process.argv[i+1];};
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const same=(bytes,id)=>!!id&&bytes.length===id.bytes&&sha(bytes)===id.sha256;
const counts={supplier:225,representative:68,example:8};
const safe=(folder,name)=>{const p=path.resolve(folder,name);if(!p.startsWith(folder+path.sep))throw Error('Path escapes report: '+name);return p;};

async function main(){
 const report=arg('--report'),out=arg('--out');
 if(!report||!out)throw Error('--report DIR --out NEWDIR required');
 const folder=path.resolve(report),output=path.resolve(out);
 fs.mkdirSync(output,{recursive:false});
 const qa={schema:'py-mermaid-vchart-dsl-report-qa/v1',status:'RUNNING',functionalStatus:'NOT_REEVALUATED',
  errors:[],transportRetries:[],pages:[],screenshots:[],requests:[],rawAssetsVerified:0,httpRawAssetsVerified:0,receiptsVerified:0};
 const check=(ok,msg)=>{if(!ok)qa.errors.push(msg);};
 let browser,server;
 try{
  const manifest=JSON.parse(fs.readFileSync(path.join(folder,'manifest.json'),'utf8'));
  qa.sourceRun=manifest.sourceRun;qa.sourceTreeSha256=manifest.sourceTreeSha256;qa.purpose=manifest.purpose;
  check(manifest.schema==='py-mermaid-vchart-dsl-report/v1','Wrong report schema');
  check(manifest.pageSize===12,'Page size must be12');
  check(manifest.cases.length===301,'Full 225+68+8 case denominator');
  check(new Set(manifest.cases.map(c=>c.group+':'+c.id.toLowerCase())).size===301,'Duplicate case IDs');
  for(const [group,count]of Object.entries(counts))check(manifest.cases.filter(c=>c.group===group).length===count,'Group denominator '+group);
  const run=JSON.parse(fs.readFileSync(path.join(manifest.sourceRun.run,'run.json'),'utf8'));
  check(run.status!=='RUNNING'&&!!run.finishedAtUtc,'Matrix source Run must be closed');
  check(same(fs.readFileSync(path.join(manifest.sourceRun.run,'run.json')),manifest.sourceRun.manifest),'Source Run manifest drift');
  check(run.source.sourceTreeSha256===manifest.sourceTreeSha256,'Report / Run source mismatch');
  const matrixBytes=fs.readFileSync(path.join(folder,manifest.sourceResult.path));
  check(same(matrixBytes,manifest.sourceResult),'Matrix copy hash differs');
  check(same(matrixBytes,manifest.sourceRun)&&same(matrixBytes,run.artifacts[manifest.sourceRun.path]),'Matrix not bound to original Run artifact');
  const matrix=JSON.parse(matrixBytes);
  check(matrix.source.sourceTreeSha256===manifest.sourceTreeSha256,'Matrix source mismatch');
  const actualRows=matrix.cases.map(c=>({id:c.id,group:c.group,status:c.status,type:c.type}));
  const renderedRows=manifest.cases.map(c=>({id:c.id,group:c.group,status:c.status,type:c.type}));
  const sorted=rows=>[...rows].sort((a,b)=>(a.group+':'+a.id).localeCompare(b.group+':'+b.id));
  const rowsEqual=(left,right)=>JSON.stringify(sorted(left))===JSON.stringify(sorted(right));
  check(rowsEqual(actualRows,renderedRows),'Raw matrix case/status/type changed by report');
  const index=fs.readFileSync(path.join(folder,'index.html'));
  check(same(index,manifest.index),'Index fingerprint differs');
  check(!index.toString().includes('<article class="case"'),'Index must remain a group landing page');
  check(index.toString().includes('PyPI')&&index.toString().includes('0.1.1'),'Formal PyPI dependency marker absent');
  check(!index.toString().includes('invalid-publisher'),'Historical PyPI blocked text leaked into new round');
  check(index.toString().includes('22')&&index.toString().includes('301'),'Scope / overlapping denominator explanation absent');
  for(const [name,id]of Object.entries(manifest.assets)){
   const bytes=fs.readFileSync(safe(folder,name));
   check(same(bytes,id),'Asset SHA differs '+name);
   check(same(fs.readFileSync(id.sourcePath),id),'Original raw bytes differ '+name);
   const proof=id.originalRunProof;check(!!proof,'Asset lacks closed Run proof '+name);
   if(proof){
    check(same(bytes,proof),'Original Run proof bytes differ '+name);
    check(proof.sourceTreeSha256===manifest.sourceTreeSha256,'Asset candidate mismatch '+name);
    check(same(fs.readFileSync(path.join(proof.run,'run.json')),proof.manifest),'Asset Run manifest changed '+name);
    check(same(bytes,run.artifacts[proof.path]),'Artifact not recorded in source Run '+name);
   }
   qa.rawAssetsVerified++;
  }
  const sample=Object.entries(manifest.assets)[0];if(!sample)throw Error('Report has no raw assets');
  const sampleBytes=fs.readFileSync(safe(folder,sample[0]));
  qa.negativeControls={changedRawHashRejected:!same(sampleBytes,{...sample[1],sha256:'0'.repeat(64)}),
   missingCaseRejected:!rowsEqual(actualRows,renderedRows.slice(1)),
   changedStatusRejected:!rowsEqual(actualRows,[{...renderedRows[0],status:'MUTATED'},...renderedRows.slice(1)])};
  check(Object.values(qa.negativeControls).every(Boolean),'In-memory mutation controls failed');
  server=http.createServer((request,response)=>{
   try{
    const name=decodeURIComponent(new URL(request.url,'http://127.0.0.1').pathname);
    const file=safe(folder,name==='/'?'index.html':'.'+name);
    const types={'.html':'text/html; charset=utf-8','.json':'application/json','.vchart':'text/plain; charset=utf-8','.png':'image/png','.svg':'image/svg+xml','.pdf':'application/pdf','.jpg':'image/jpeg','.webp':'image/webp'};
    response.writeHead(200,{'Content-Type':types[path.extname(file)]||'application/octet-stream'});response.end(fs.readFileSync(file));
   }catch(error){response.writeHead(404);response.end('not found');}
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const base=arg('--url')?new URL('.',arg('--url')).href:'http://127.0.0.1:'+server.address().port+'/';qa.url=base;
  const fetchCheck=async(name,id)=>{
   // Retry only interrupted read-only transport. A received status/hash mismatch
   // remains a hard QA failure. Retain every retry and its cause in the receipt.
   let response,bytes;
   for(let attempt=1;attempt<=3;attempt++){
    try{response=await fetch(new URL(name,base));bytes=Buffer.from(await response.arrayBuffer());break;}
    catch(error){
     qa.transportRetries.push({name,attempt,error:String(error),cause:String(error.cause||'')});
     if(attempt===3)throw error;
     await new Promise(resolve=>setTimeout(resolve,250*attempt));
    }
   }
   check(response.ok,'HTTP failed '+name);check(same(bytes,id),'HTTP bytes differ '+name);
  };
  await fetchCheck('index.html',manifest.index);await fetchCheck(manifest.sourceResult.path,manifest.sourceResult);
  for(const receipt of Object.values(manifest.attachments||{})){
   const bytes=fs.readFileSync(safe(folder,receipt.path));check(same(bytes,receipt),'Receipt file SHA differs');
   check(same(fs.readFileSync(receipt.sourcePath),receipt),'Original receipt SHA differs');
   const value=JSON.parse(bytes);check(value.sourceTreeSha256===manifest.sourceTreeSha256,'Receipt source mismatch');
   check(path.resolve(root,value.candidateRun||value.baselineRun)===path.resolve(manifest.sourceRun.run),'Receipt candidate mismatch');
   await fetchCheck(receipt.path,receipt);qa.receiptsVerified++;
  }
  const queue=Object.entries(manifest.assets);
  await Promise.all(Array.from({length:4},async()=>{while(queue.length){const [name,id]=queue.pop();await fetchCheck(name,id);qa.httpRawAssetsVerified++;}}));
  browser=await req('playwright').chromium.launch({headless:true});
  qa.browser=browser.version();qa.browserPolicy='Existing bundled Playwright Chromium; isolated temporary profile; no user Chrome';
  const page=await browser.newPage({viewport:{width:1440,height:1000},deviceScaleFactor:1});
  page.on('pageerror',error=>qa.errors.push('pageerror '+error.message));
  page.on('request',request=>qa.requests.push(request.url()));
  await page.route('**/*',route=>{
   const url=new URL(route.request().url());
   if(url.origin!==new URL(base).origin){qa.errors.push('External request '+url.href);return route.abort();}
   if(url.pathname.endsWith('/favicon.ico'))return route.fulfill({status:204,body:''});return route.continue();
  });
  for(const width of [1440,390]){
   await page.setViewportSize({width,height:width===390?844:1000});
   await page.goto(base,{waitUntil:'domcontentloaded'});
   check(await page.locator('a[href$=".html"]').count()===manifest.pages.length,'Index page-link count');
   check(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),'Index horizontal overflow '+width);
   const filename='index-'+width+'.png';await page.screenshot({path:path.join(output,filename),fullPage:true});qa.screenshots.push(filename);
  }
  for(const entry of manifest.pages){
   check(entry.cases<=12&&entry.cases>0,'Page denominator '+entry.path);
   await fetchCheck(entry.path,entry.report);
   const expected=manifest.cases.filter(c=>c.page===entry.path);
   for(const width of [1440,390]){
    await page.setViewportSize({width,height:width===390?844:1000});
    await page.goto(new URL(entry.path,base).href,{waitUntil:'domcontentloaded'});
    const actual=await page.locator('.case').evaluateAll(nodes=>nodes.map(n=>({id:n.dataset.case,status:n.dataset.status,group:n.dataset.group,anchor:n.id})));
    check(JSON.stringify(actual)===JSON.stringify(expected.map(c=>({id:c.id,status:c.status,group:c.group,anchor:c.anchor}))),'Case/status DOM differs '+entry.path+' '+width);
    await page.locator('img').evaluateAll(async images=>{for(const i of images)i.loading='eager';await Promise.all(images.map(i=>i.decode()));});
    check(await page.locator('img').evaluateAll(images=>images.every(i=>i.naturalWidth>0&&i.naturalHeight>0)),'Broken image '+entry.path);
    check(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),'Page overflow '+entry.path+' '+width);
    await page.locator('.case details').first().locator('summary').click();
    check(await page.locator('.case details').first().getAttribute('open')!==null,'Details failed '+entry.path);
    check(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),'Details overflow '+entry.path+' '+width);
    if(entry.path.endsWith('-01.html')){
     const filename=entry.group+'-'+width+'.png';await page.locator('.case').first().screenshot({path:path.join(output,filename)});qa.screenshots.push(filename);
    }
   }
   qa.pages.push({path:entry.path,cases:expected.length,viewports:[1440,390]});
  }
  qa.caseCount=manifest.cases.length;
 }catch(error){qa.errors.push(String(error.stack||error));}
 finally{
  if(browser)await browser.close();if(server)await new Promise(resolve=>server.close(resolve));
  qa.status=qa.errors.length?'FAIL':'PASS';fs.writeFileSync(path.join(output,'viewer.json'),JSON.stringify(qa,null,2)+'\n');
 }
 console.log(JSON.stringify({status:qa.status,cases:qa.caseCount,pages:qa.pages.length,rawAssetsVerified:qa.rawAssetsVerified,errors:qa.errors}));
 process.exitCode=qa.errors.length?1:0;
}
main().catch(error=>{console.error(error.stack);process.exitCode=1;});
