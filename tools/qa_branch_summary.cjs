/* Read-only local branch-summary QA. No product execution or classification changes. */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {createRequire}=require('node:module');
const root=path.resolve(__dirname,'..'),req=createRequire(path.join(root,'.local/f011-oracle/package.json'));
const arg=n=>{const i=process.argv.indexOf(n);return i<0?null:process.argv[i+1];};
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
async function main(){
 const url=arg('--url'),manifest=arg('--report'),out=arg('--out');
 if(!url||!manifest||!out)throw Error('--url --report --out required');
 fs.mkdirSync(out,{recursive:false});
 const report=JSON.parse(fs.readFileSync(manifest,'utf8')),base=new URL('.',url);
 const qa={schema:'py-mermaid-branch-summary-qa/v1',status:'RUNNING',errors:[],branches:0,pages:[],screenshots:[]};
 const check=(value,message)=>{if(!value)qa.errors.push(message);};
 let browser;
 try{
  const home=Buffer.from(await(await fetch(url)).arrayBuffer());check(sha(home)===report.report.sha256&&home.length===report.report.bytes,'Home fingerprint');
  const response=await fetch(new URL('verification.json',base));check(response.status===200,'Result JSON HTTP');
  const raw=Buffer.from(await response.arrayBuffer());check(sha(raw)===report.input.sha256&&raw.length===report.input.bytes,'Result JSON bytes');
  const result=JSON.parse(raw.toString('utf8')),wanted=new Map(result.branchRecords.map(b=>[b.id,b.conclusion.classification])),seen=new Set();
  for(const page of report.pages){
   const r=await fetch(new URL(page.path,base));check(r.status===200,'Page HTTP '+page.path);
   const b=Buffer.from(await r.arrayBuffer());check(sha(b)===page.sha256&&b.length===page.bytes,'Page fingerprint '+page.path);
   const rows=[...b.toString('utf8').matchAll(/<article id="([^"]+)" data-classification="([^"]+)"/g)];
   check(rows.length===page.ids.length&&rows.length<=12,'Page denominator '+page.path);
   for(const [,id,status] of rows){check(!seen.has(id),'Duplicate branch '+id);seen.add(id);check(wanted.get(id)===status,'Changed classification '+id);}
   qa.pages.push({path:page.path,branches:rows.length});
  }
  check(seen.size===report.branchRecords&&seen.size===wanted.size,'Complete branch denominator');qa.branches=seen.size;
  const cache=new Map();
  for(const row of result.branchRecords)for(const [id,href] of Object.entries(row.caseLinks||{})){
   const target=new URL(href,base);check(target.origin===base.origin,'External comparison link');
   const hash=target.hash;target.hash='';
   if(!cache.has(target.href)){const r=await fetch(target);check(r.status===200,'Comparison HTTP');cache.set(target.href,await r.text());}
   check(cache.get(target.href).includes('id="case-'+id+'"')&&hash==='#case-'+id,'Comparison case binding '+id);
  }
  browser=await req('playwright').chromium.launch({channel:'chrome',headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:1000},deviceScaleFactor:1});
  page.on('pageerror',e=>qa.errors.push(e.message));await page.goto(url,{waitUntil:'domcontentloaded'});
  check(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),'Desktop overflow');
  await page.screenshot({path:path.join(out,'index-desktop.png'),fullPage:true});qa.screenshots.push('index-desktop.png');
  await page.goto(new URL(report.pages[0].path,base).href,{waitUntil:'domcontentloaded'});
  check(await page.locator('article').count()===report.pages[0].ids.length,'Browser branch page denominator');
  await page.setViewportSize({width:390,height:844});check(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),'Mobile overflow');
  await page.screenshot({path:path.join(out,'branch-mobile.png')});qa.screenshots.push('branch-mobile.png');
 }catch(error){qa.errors.push(String(error.stack||error));}
 finally{if(browser)await browser.close();qa.status=qa.errors.length?'FAIL':'PASS';fs.writeFileSync(path.join(out,'viewer.json'),JSON.stringify(qa,null,2)+'\n');}
 console.log(JSON.stringify({status:qa.status,branches:qa.branches,pages:qa.pages.length,errors:qa.errors}));
 if(qa.status!=='PASS')process.exitCode=1;
}
main().catch(error=>{console.error(error.stack||error);process.exitCode=1;});
