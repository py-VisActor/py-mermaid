/* Read-only local viewer QA; pinned development browser, no installation. */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {createRequire}=require('node:module');
const root=path.resolve(__dirname,'..');
const req=createRequire(path.join(root,'.local/f011-oracle/package.json'));
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const arg=name=>{const i=process.argv.indexOf(name);return i<0?null:process.argv[i+1];};
const counter=values=>{const result={};for(const value of values)result[value]=(result[value]||0)+1;return result;};

async function main(){
 const url=arg('--url'),input=arg('--report'),directory=arg('--out');
 if(!url||!input||!directory)throw Error('--url LOCAL_REPORT_URL --report REPORT_JSON --out NEW_DIRECTORY required');
 const report=JSON.parse(fs.readFileSync(input,'utf8')),out=path.resolve(directory);
 fs.mkdirSync(out,{recursive:false});
 const qa={schema:'py-mermaid-bulk-viewer-qa/v1',url,sourceTreeSha256:report.sourceTreeSha256,
  reportJsonSha256:sha(fs.readFileSync(input)),errors:[],samples:[],requests:[],status:'RUNNING'};
 const check=(condition,message)=>{if(!condition)qa.errors.push(message);};
 let browser;
 try{
  const response=await fetch(url);check(response.status===200,'HTML HTTP status '+response.status);
  const bytes=Buffer.from(await response.arrayBuffer());qa.htmlSha256=sha(bytes);qa.htmlBytes=bytes.length;
  check(qa.htmlSha256===report.report.sha256&&bytes.length===report.report.bytes,'Served HTML fingerprint differs');
  const html=bytes.toString('utf8');
  const expected=Object.entries(report.rawEmbeddedArtifacts).map(([name,identity])=>({name,identity}));
  for(const [mime,suffix,pattern] of [
   ['png','.png',/<img\b[^>]*\bsrc="data:image\/png;base64,([^"]+)"[^>]*>/g],
   ['svg','.svg',/<a\b[^>]*\bhref="data:image\/svg\+xml;base64,([^"]+)"[^>]*>/g],
  ]){
   const actual=[...html.matchAll(pattern)].map(m=>{const b=Buffer.from(m[1],'base64');return sha(b)+':'+b.length;});
   const wanted=expected.filter(e=>e.name.endsWith(suffix)).map(e=>e.identity.sha256+':'+e.identity.bytes);
   check(JSON.stringify(Object.entries(counter(actual)).sort())===JSON.stringify(Object.entries(counter(wanted)).sort()),'Embedded raw '+mime+' bytes/count differ');
   qa['raw'+mime.toUpperCase()+'Verified']=actual.length;
  }
  browser=await req('playwright').chromium.launch({channel:'chrome',headless:true});qa.browser=browser.version();
  const page=await browser.newPage({viewport:{width:1440,height:1000},deviceScaleFactor:1});
  await page.route('**/favicon.ico',route=>route.fulfill({status:204,body:''}));
  page.on('pageerror',e=>qa.errors.push('pageerror: '+String(e)));
  page.on('console',m=>{if(m.type()==='error')qa.errors.push('console: '+m.text());});
  page.on('request',r=>{if(!r.url().startsWith('data:'))qa.requests.push(r.url());});
  const opened=await page.goto(url,{waitUntil:'domcontentloaded',timeout:120000});
  check(opened?.status()===200,'Browser HTTP status');
  check(await page.locator('.case').count()===report.cases.length,'Browser case denominator differs');
  check((await page.locator('header').textContent()).includes(report.sourceTreeSha256),'Missing candidate identity');
  const kinds=[...new Set(report.cases.map(c=>c.kind))];check(kinds.length===31,'Retained kind denominator differs');
  const chosen=kinds.map(kind=>report.cases.find(c=>c.kind===kind&&['CHECKS_PASSED_REVIEW_REQUIRED','CHECKS_PASSED'].includes(c.status)&&Object.values(c.native).every(n=>n.status==='CHECKS_PASSED')));
  for(const id of ['C-zenuml-source-demo1-smoke','C-sequence-critical-break-rect','A-c4-all-relations','A-block-all-arrow-factories','B-journey-wrapped','shared-math','shared-unicode-rich']){
   const row=report.cases.find(c=>c.id===id);if(row&&!chosen.some(c=>c?.id===id))chosen.push(row);
  }
  for(const row of chosen){
   if(!row){qa.errors.push('No normal representative for retained kind');continue;}
   await page.locator('#search').fill(row.id+' ');
   const card=page.locator('.case:not(.hidden)');
   check(await card.count()===1,'Exact case search: '+row.id);
   await card.locator('img').evaluateAll(async images=>{await Promise.all(images.map(img=>img.decode()));});
   const actual=await card.evaluate(e=>({title:e.querySelector('h2').textContent,images:[...e.querySelectorAll('img')].map(i=>({alt:i.alt,width:i.naturalWidth,height:i.naturalHeight})),status:e.dataset.status}));
   check(actual.title.includes(row.id)&&actual.status===row.status,'Case binding: '+row.id);
   check(actual.images.every(i=>i.width>0&&i.height>0),'Image decode: '+row.id);
   for(const [profile,native] of Object.entries(row.native)){
    if(native.status!=='CHECKS_PASSED')continue;
    const image=actual.images.find(i=>i.alt===row.id+' '+profile);
    check(image?.width===native.width&&image?.height===native.height,'Native dimensions: '+row.id+'/'+profile);
   }
   check(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),'Desktop document overflow: '+row.id);
   if(['C-zenuml-source-demo1-smoke','A-c4-all-relations','B-journey-wrapped'].includes(row.id))
    await page.screenshot({path:path.join(out,row.id+'.png')});
   qa.samples.push({id:row.id,kind:row.kind,...actual});
  }
  await page.locator('#search').fill('__NO_CASE_EXPECTED__');
  check(await page.locator('.case:not(.hidden)').count()===0,'Empty search state');
  await page.locator('#search').fill('');
  for(const [status,count] of Object.entries(report.counts)){
   await page.selectOption('#status',status);
   check(await page.locator('.case:not(.hidden)').count()===count,'Status filter denominator: '+status);
   check((await page.locator('#count').textContent())===count+' / '+report.cases.length,'Status counter: '+status);
  }
  await page.selectOption('#status','');
  await page.locator('#search').fill(chosen[0].id+' ');await page.setViewportSize({width:390,height:844});
  check(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),'Mobile document overflow');
  await page.screenshot({path:path.join(out,'mobile.png')});
  check(qa.requests.every(r=>new URL(r).origin===new URL(url).origin),'Viewer requested an external network resource');
 }catch(error){qa.errors.push(String(error.stack||error));}
 finally{
  if(browser)await browser.close();qa.status=qa.errors.length?'FAIL':'PASS';
  fs.writeFileSync(path.join(out,'viewer.json'),JSON.stringify(qa,null,2)+'\n');
 }
 console.log(JSON.stringify({status:qa.status,samples:qa.samples.length,rawPNG:qa.rawPNGVerified,rawSVG:qa.rawSVGVerified,errors:qa.errors}));
 if(qa.status!=='PASS')process.exitCode=1;
}
main().catch(error=>{console.error(error.stack||error);process.exitCode=1;});
