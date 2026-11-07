/* Development-only read-only getter probe. Never imported by production. */
const fs = require('node:fs'), path = require('node:path'), cp = require('node:child_process');
const crypto = require('node:crypto'), {createRequire} = require('node:module');
const root = path.resolve(__dirname, '../..');
const req = createRequire(path.join(root, '.local/f011-oracle/package.json'));
const sha = b => crypto.createHash('sha256').update(b).digest('hex');
const arg = n => {const i=process.argv.indexOf(n);return i<0?null:process.argv[i+1];};
async function main() {
  if (!arg('--fixtures') || !arg('--out')) throw Error('--fixtures FILE --out NEWDIR required');
  const fixturePath=path.resolve(arg('--fixtures')), out=path.resolve(arg('--out'));
  // Reuse the full canonical source/build-transport verification. This starts
  // no browser/formula when --verify-only; its identity is retained in out.
  cp.execFileSync(process.execPath,[path.join(root,'tools/oracle/bulk_capture.cjs'),
    '--verify-only','--out',out],{stdio:'inherit'});
  const identity=JSON.parse(fs.readFileSync(path.join(out,'identity.json')));
  const fixture=JSON.parse(fs.readFileSync(fixturePath)), {chromium}=req('playwright');
  const browser=await chromium.launch({channel:'chrome',headless:true});
  const records=[];
  try {
    for(const item of fixture.cases) {
      const page=await browser.newPage();
      try {
        await page.goto('about:blank');
        await page.addScriptTag({path:path.join(root,'.local/f011-oracle/node_modules/mermaid/dist/mermaid.js')});
        const result=await page.evaluate(async item => {
          mermaid.initialize({startOnLoad:false,...item.config});
          const pure=(v,seen=new WeakSet(),depth=0)=>{
            if(v===null||typeof v!=='object')return typeof v==='function'?undefined:v;
            if(depth>24)return {$truncated:'depth'};
            if(seen.has(v))return {$ref:true};seen.add(v);
            if(v instanceof Map)return Object.fromEntries([...v].map(([k,x])=>[k,pure(x,seen,depth+1)]));
            if(v instanceof Set)return [...v].map(x=>pure(x,seen,depth+1));
            if(Array.isArray(v))return v.map(x=>pure(x,seen,depth+1));
            return Object.fromEntries(Object.keys(v).filter(k=>typeof v[k]!=='function').map(k=>[k,pure(v[k],seen,depth+1)]));
          };
          try {
            const d=await mermaid.mermaidAPI.getDiagramFromText(item.source), snapshot={};
            const getters=['getDomains','getTransitions','getData','getRoot','getMindmap',
              'getC4ShapeArray','getBoundaries','getRels','getTitle','getC4ShapeInRow','getC4BoundaryInRow',
              'getClasses','getRelations','getStates','getRootDoc','getDataStructures',
              'getDiagramTitle','getAccTitle','getAccDescription'];
            for(const k of getters)if(typeof d.db[k]==='function'){
              try{snapshot[k]=pure(d.db[k]());}catch(e){snapshot[k]={$getterError:String(e)};}
            }
            return {status:'PARSED',kind:d.type,snapshot};
          } catch(e) {return {status:'SOURCE_PARSE_ERROR',error:String(e),location:e?.hash?.loc||null};}
        },item);
        const row={id:item.id,source:item.source,config:item.config,...result};
        fs.writeFileSync(path.join(out,item.id+'.json'),JSON.stringify(row,null,2)+'\n');records.push(row);
      } finally {await page.close();}
    }
  } finally {await browser.close();}
  fs.writeFileSync(path.join(out,'manifest.json'),JSON.stringify({schema:'branch-A-source-getters/v1',
    fixtureSha256:sha(fs.readFileSync(fixturePath)),identity,browser:browser.version(),cases:records},null,2)+'\n');
}
main().catch(e=>{console.error(e);process.exitCode=1;});
