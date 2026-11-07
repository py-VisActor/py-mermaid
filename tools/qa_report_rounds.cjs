/* Read-only paged report QA: full file/image inventory plus browser navigation. */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {createRequire}=require('node:module');
const root=path.resolve(__dirname,'..'),req=createRequire(path.join(root,'.local/f011-oracle/package.json'));
const arg=name=>{const i=process.argv.indexOf(name);return i<0?null:process.argv[i+1];};
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
async function main(){
 const url=arg('--url'),reportPath=arg('--report'),out=arg('--out');
 if(!url||!reportPath||!out)throw Error('--url --report --out required');
 fs.mkdirSync(out,{recursive:false});
 const report=JSON.parse(fs.readFileSync(reportPath,'utf8'));
 const qa={schema:'py-mermaid-report-rounds-qa/v1',status:'RUNNING',errors:[],pages:[],requests:[],screenshots:[],sourceTreeSha256:report.sourceTreeSha256};
 const check=(ok,message)=>{if(!ok)qa.errors.push(message);};
 let browser;
 try{
  const home=Buffer.from(await (await fetch(url)).arrayBuffer());
  check(sha(home)===report.report.sha256,'Index fingerprint differs');
  check(home.length===report.report.bytes,'Index length differs');
  check(!home.toString('utf8').includes('<article class="case"'),'Index contains full case cards');
  const base=new URL('.',url),seen=new Set(),images=new Map();let png=0,svg=0;
  for(const entry of report.pages){
   const response=await fetch(new URL(entry.path,base));check(response.status===200,'Page HTTP '+entry.path);
   const raw=Buffer.from(await response.arrayBuffer()),text=raw.toString('utf8');
   check(sha(raw)===entry.report.sha256&&raw.length===entry.report.bytes,'Page fingerprint '+entry.path);
   const cases=[...text.matchAll(/<article id="case-([^"]+)" class="case" data-status="([^"]+)"/g)];
   check(cases.length===entry.caseIds.length&&cases.length<=report.pageSize,'Page denominator '+entry.path);
   for(const [,id,status] of cases){check(!seen.has(id),'Duplicate case '+id);seen.add(id);check(entry.caseStatuses[id]===status,'Case status changed '+id);}
   for(const [,mime,encoded] of text.matchAll(/(?:src|href)="data:image\/(png|svg\+xml);base64,([^"]+)"/g)){
    const b=Buffer.from(encoded,'base64'),key=mime+':'+sha(b)+':'+b.length;images.set(key,(images.get(key)||0)+1);mime==='png'?png++:svg++;
   }
   qa.pages.push({path:entry.path,cases:cases.length,bytes:raw.length});
  }
  check(seen.size===report.caseCount,'Complete case denominator');
  const original=JSON.parse(fs.readFileSync(path.resolve(root,report.sourceReport.metadata.path),'utf8')),expected=new Map();
  for(const [name,identity] of Object.entries(original.rawEmbeddedArtifacts)){
   const mime=name.endsWith('.png')?'png':name.endsWith('.svg')?'svg+xml':null;if(!mime)continue;
   const key=mime+':'+identity.sha256+':'+identity.bytes;expected.set(key,(expected.get(key)||0)+1);
  }
  check(JSON.stringify([...images].sort())===JSON.stringify([...expected].sort()),'Exact original embedded bytes/count differ');
  check(png===report.rawPNGVerified&&svg===report.rawSVGVerified,'Image counts differ');
  qa.rawPNGVerified=png;qa.rawSVGVerified=svg;qa.uniqueCases=seen.size;qa.indexBytes=home.length;
  for(const item of report.history){const r=await fetch(new URL(item.href,base));check(r.status===200,'Historical link '+item.title);await r.body.cancel();}
  browser=await req('playwright').chromium.launch({channel:'chrome',headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:1000},deviceScaleFactor:1});
  await page.route('**/favicon.ico',r=>r.fulfill({status:204,body:''}));
  page.on('pageerror',e=>qa.errors.push('pageerror '+e.message));
  page.on('console',m=>{if(m.type()==='error')qa.errors.push('console '+m.text());});
  page.on('request',r=>{if(!r.url().startsWith('data:'))qa.requests.push(r.url());});
  await page.goto(url,{waitUntil:'domcontentloaded'});
  check(await page.locator('.rounds .panel').count()===report.rounds.length,'Round cards');
  check(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),'Index desktop overflow');
  await page.screenshot({path:path.join(out,'index-desktop.png'),fullPage:true});qa.screenshots.push('index-desktop.png');
  const lookupCase=report.pages[0].caseIds[0];await page.locator('#lookup').fill(lookupCase);
  check(await page.locator('#lookup-results a').count()>0,'Global lookup has no results');
  await page.locator('#lookup-results a').first().click();
  check(await page.locator('#case-'+lookupCase).count()===1,'Global lookup destination');
  for(const round of report.rounds){
   const roundPages=report.pages.filter(p=>p.roundId===round.id);
   await page.goto(new URL(round.href,base).href,{waitUntil:'domcontentloaded'});
   check(await page.locator('.page-select option').count()===round.pageCount,'Round page jump count');
   await page.locator('.page-select').selectOption(path.basename(roundPages.at(-1).path));
   await page.waitForURL(new URL(roundPages.at(-1).path,base).href);
   for(const entry of [roundPages[0],roundPages.at(-1)]){
    await page.goto(new URL(entry.path,base).href,{waitUntil:'domcontentloaded'});
    check(await page.locator('.case').count()===entry.caseIds.length,'Browser page denominator');
    const first=entry.caseIds[0];await page.locator('#search').fill(first+' ');
    check(await page.locator('.case:not(.hidden)').count()===1,'Page exact search '+first);
    await page.locator('.case:not(.hidden) img:visible').evaluateAll(async imgs=>{
     for(const image of imgs)image.loading='eager';
     await Promise.all(imgs.map(i=>i.decode()));
    });
    for(const profile of await page.locator('#backend option').allTextContents()){
     await page.selectOption('#backend',profile);
     check(await page.locator('[data-profile]:not(.hidden)').evaluateAll((els,p)=>els.every(e=>e.dataset.profile===p),profile),'Backend switch '+profile);
    }
    check(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),'Desktop page overflow '+entry.path);
   }
  }
  await page.goto(new URL(report.pages[0].path,base).href,{waitUntil:'domcontentloaded'});
  await page.locator('#search').fill(report.pages[0].caseIds[0]+' ');
  await page.screenshot({path:path.join(out,'case-desktop.png'),fullPage:true});qa.screenshots.push('case-desktop.png');
  await page.setViewportSize({width:390,height:844});
  check(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),'Case mobile overflow');
  await page.screenshot({path:path.join(out,'case-mobile.png'),fullPage:true});qa.screenshots.push('case-mobile.png');
  await page.goto(url,{waitUntil:'domcontentloaded'});
  check(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),'Index mobile overflow');
  await page.screenshot({path:path.join(out,'index-mobile.png'),fullPage:true});qa.screenshots.push('index-mobile.png');
  check(qa.requests.every(u=>new URL(u).origin===new URL(url).origin),'External resource request');
 }catch(error){qa.errors.push(String(error.stack||error));}
 finally{if(browser)await browser.close();qa.status=qa.errors.length?'FAIL':'PASS';fs.writeFileSync(path.join(out,'viewer.json'),JSON.stringify(qa,null,2)+'\n');}
 console.log(JSON.stringify({status:qa.status,pages:qa.pages.length,cases:qa.uniqueCases,indexBytes:qa.indexBytes,rawPNG:qa.rawPNGVerified,rawSVG:qa.rawSVGVerified,errors:qa.errors}));
 if(qa.status!=='PASS')process.exitCode=1;
}
main().catch(e=>{console.error(e.stack||e);process.exitCode=1;});
