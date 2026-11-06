/* Development-only viewer QA. Uses existing pinned Playwright, never installs. */
const fs=require('node:fs');
const path=require('node:path');
const {createRequire}=require('node:module');
const crypto=require('node:crypto');
const root=path.resolve(__dirname,'..');
const req=createRequire(path.join(root,'.local/f011-oracle/package.json'));
const arg=name=>{const i=process.argv.indexOf(name);return i<0?null:process.argv[i+1];};

async function main(){
  const url=arg('--url'),outArg=arg('--out');
  if(!url||!outArg)throw new Error('--url REPORT_URL --out NEW_DIRECTORY required');
  const out=path.resolve(outArg);fs.mkdirSync(out,{recursive:false});
  const report={url,browser:null,errors:[],cases:[],profiles:[],requests:[]};
  const browser=await req('playwright').chromium.launch({channel:'chrome',headless:true});
  report.browser=browser.version();
  try {
    const page=await browser.newPage({viewport:{width:1440,height:1000},deviceScaleFactor:1});
    await page.route('**/favicon.ico',route=>route.fulfill({status:204,body:''}));
    page.on('pageerror',e=>report.errors.push(String(e)));
    page.on('console',m=>{if(m.type()==='error')report.errors.push(m.text());});
    page.on('request',r=>report.requests.push(r.url().startsWith('data:')?'data:':r.url()));
    const response=await page.goto(url,{waitUntil:'load'});
    if(!response||response.status()!==200)throw new Error('Report HTTP response is not 200');
    // Large self-contained matrices exceed Chromium's inspector response cache.
    // Hash a direct HTTP read; browser assertions below still inspect the page.
    const bodyResponse=await fetch(url);
    if(bodyResponse.status!==200)throw new Error('Report fingerprint HTTP response is not 200');
    const html=Buffer.from(await bodyResponse.arrayBuffer());report.htmlSha256=crypto.createHash('sha256').update(html).digest('hex');
    const data=await page.locator('#report-data').evaluate(e=>JSON.parse(e.textContent));
    report.scope=data.scope;report.profiles=data.profiles;
    report.exportSamples=[];
    for(const sample of data.exports||[]){
      const bytes=Buffer.from(sample.url.split(',')[1],'base64');
      const digest=crypto.createHash('sha256').update(bytes).digest('hex');
      if(digest!==sample.sha256||bytes.length!==sample.bytes)report.errors.push('Static export fingerprint '+sample.file);
      const link=page.locator('#export-samples a').filter({hasText:sample.file.toUpperCase()});
      if(await link.count()!==1||await link.getAttribute('download')!==sample.file)report.errors.push('Static export download link '+sample.file);
      report.exportSamples.push({file:sample.file,sha256:digest,bytes:bytes.length});
    }
    report.positiveCases=data.cases.length;report.errorCases=data.negatives.length;
    for(const profile of data.profiles){
      await page.selectOption('#profile',profile);
      for(const [index,item] of data.cases.entries()){
        await page.locator('#positive-nav button').nth(index).click();
        await page.locator('#a-image').evaluate(img=>img.decode());
        await page.locator('#b-image').evaluate(img=>img.decode());
        const actual=await page.evaluate(()=>({
          id:document.getElementById('case-id').textContent,
          status:document.getElementById('functional-status').textContent,
          a:document.getElementById('a-image').naturalWidth,b:document.getElementById('b-image').naturalWidth,
          text:document.getElementById('source-code').textContent,
          overflow:document.documentElement.scrollWidth>innerWidth+1,
        }));
        // Navigation titles need not be unique; the stable case ID must match.
        if(actual.id!==item.id||actual.status!=='PASS'||actual.a!==item.officialImage.width||actual.b!==item.profiles[profile].image.width||actual.text!==item.text||actual.overflow)
          report.errors.push(profile+'/'+item.id+' viewer/content mismatch '+JSON.stringify(actual));
        report.cases.push({id:item.id,profile,status:actual.status});
      }
      for(const [index,item] of data.negatives.entries()){
        await page.locator('#negative-nav button').nth(index).click();
        if(await page.locator('#case-id').textContent()!==item.id||item.profiles[profile].status!=='PASS')report.errors.push('Error case mismatch '+item.id+'/'+profile);
      }
    }
    const defaultIndex=data.cases.findIndex(c=>c.id===data.defaultCase);
    await page.locator('#positive-nav button').nth(defaultIndex).click();
    await page.selectOption('#profile',data.profiles[0]);
    for(const mode of ['overlay','diff','mask','side']){
      await page.locator('[data-mode="'+mode+'"]').click();
      if(mode==='diff'||mode==='mask')await page.locator('#diagnostic-image').evaluate(img=>img.decode());
    }
    await page.screenshot({path:path.join(out,'desktop.png'),fullPage:true});
    await page.setViewportSize({width:390,height:844});
    if(await page.locator('#zoom').inputValue()==='fit')await page.waitForFunction(()=>{
      const img=document.getElementById('a-image');return parseFloat(img.style.width)<=img.parentElement.clientWidth;
    });
    await page.screenshot({path:path.join(out,'mobile.png'),fullPage:true});
    if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1))report.errors.push('Mobile page horizontal overflow');
    report.externalRequests=report.requests.filter(u=>u!=='data:'&&u!==url&&!u.endsWith('/favicon.ico'));
    if(report.externalRequests.length)report.errors.push('Unexpected external requests');
  } catch(error){report.errors.push(String(error));}
  finally{await browser.close();report.status=report.errors.length?'FAIL':'PASS';fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2));}
  console.log(JSON.stringify({status:report.status,cases:report.cases.length,errors:report.errors,out}));
  if(report.errors.length)process.exitCode=1;
}
main().catch(e=>{console.error(e);process.exitCode=1;});
