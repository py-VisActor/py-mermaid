/* Exact fixed-bundle numerical observations. Development oracle only.
 * Run with node --experimental-vm-modules; no npm helper resolution/installs.
 */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),vm=require('node:vm');
const repo=path.resolve(__dirname,'../..'), hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const MAP_SHA='8b844955879bad4b284a9603827b8268f11ecb57cd0fbf2f338c24e2afa99679';
const BUNDLE_SHA='ffd1a76f0553952a344c68a9b1502dd5cfb6faab72541307b74679c5abc9cec8';
const used=new Map(),dependencies=[];
function argument(name,fallback){const i=process.argv.indexOf(name);return i<0?fallback:process.argv[i+1];}
function extract(text,needle){
  const begin=text.indexOf(needle);if(begin<0)throw Error('Missing original source function '+needle);
  const brace=text.indexOf('{',begin);let depth=1,i=brace+1;
  for(;i<text.length&&depth;i++){if(text[i]==='{')depth++;else if(text[i]==='}')depth--;}
  if(depth)throw Error('Unbalanced original function');return text.slice(begin,i);
}
async function main(){
  if(typeof vm.SourceTextModule!=='function')throw Error('Pass --experimental-vm-modules');
  const fixtures=path.resolve(argument('--fixtures',path.join(__dirname,'cases-B.json'))),out=path.resolve(argument('--out',''));
  if(!argument('--out')||fs.existsSync(out))throw Error('--out must name a new directory');
  const mapPath=path.join(repo,'.local/f011-oracle/node_modules/mermaid/dist/mermaid.js.map');
  const bundlePath=path.join(repo,'.local/f011-oracle/node_modules/mermaid/dist/mermaid.js');
  if(hash(fs.readFileSync(mapPath))!==MAP_SHA||hash(fs.readFileSync(bundlePath))!==BUNDLE_SHA)throw Error('Fixed bundle/map identity changed');
  const map=JSON.parse(fs.readFileSync(mapPath,'utf8'));
  const originals=new Map(map.sources.map((s,i)=>[s,map.sourcesContent[i]]));
  function exact(packageVersion,file){
    const names=map.sources.filter(s=>s.includes('/'+packageVersion+'/')&&s.endsWith('/'+file));
    if(names.length!==1)throw Error('Non-unique exact source '+packageVersion+'/'+file);
    return names[0];
  }
  function source(key){
    if(!originals.has(key))throw Error('Module absent from fixed map: '+key);
    const text=originals.get(key);used.set(key,{name:key,sha256:hash(Buffer.from(text,'utf8'))});return text;
  }
  function umd(key){
    const module={exports:{}};const sandbox={module,exports:module.exports,Date,Math};
    vm.runInNewContext(source(key),sandbox,{filename:key});return module.exports;
  }
  const dayjs=umd(exact('dayjs@1.11.21','dayjs/dayjs.min.js'));
  for(const plugin of ['isoWeek','customParseFormat','advancedFormat','duration'])dayjs.extend(umd(exact('dayjs@1.11.21','dayjs/plugin/'+plugin+'.js')));
  const context=vm.createContext({Date,Math,Map,Set,Infinity});const modules=new Map(),packages=new Map();
  function getModule(key){
    if(modules.has(key))return modules.get(key);
    const module=new vm.SourceTextModule(source(key),{context,identifier:key});modules.set(key,module);return module;
  }
  async function link(specifier,parent){
    const key=specifier.startsWith('.')?path.posix.normalize(path.posix.join(path.posix.dirname(parent.identifier),specifier)):specifier;
    dependencies.push({from:parent.identifier,specifier,to:key});
    if(!specifier.startsWith('.')){if(!packages.has(specifier))throw Error('Unbound exact package '+specifier);return packages.get(specifier);}
    return getModule(key);
  }
  async function evaluate(key){const m=getModule(key);if(m.status==='unlinked')await m.link(link);if(m.status!=='evaluated')await m.evaluate();return m.namespace;}
  async function synthetic(name,values){
    const m=new vm.SyntheticModule(Object.keys(values),function(){for(const [k,v]of Object.entries(values))this.setExport(k,v);},{context,identifier:'mechanical-binding:'+name});
    packages.set(name,m);await m.link(()=>{throw Error('Synthetic namespace has no dependencies')});await m.evaluate();return m;
  }
  const bisector=await evaluate(exact('d3-array@3.2.4','d3-array/src/bisector.js'));
  const ticks=await evaluate(exact('d3-array@3.2.4','d3-array/src/ticks.js'));
  await synthetic('d3-array',{bisector:bisector.default,tickStep:ticks.tickStep});
  let time={};
  for(const file of ['millisecond','second','minute','hour','day','week','month','year','ticks'])Object.assign(time,await evaluate(exact('d3-time@3.1.0','d3-time/src/'+file+'.js')));
  // Exact index.js export aliases; the entry module also exports unrelated
  // tree-shaken files absent from the map, so bind only the observed imports.
  source(exact('d3-time@3.1.0','d3-time/src/index.js'));
  source(exact('d3-array@3.2.4','d3-array/src/index.js'));
  time.timeMillisecond=time.millisecond;time.timeSecond=time.second;time.timeWeek=time.timeSunday;
  await synthetic('d3-time',time);
  const format=await evaluate(exact('d3-time-format@4.1.0','d3-time-format/src/defaultLocale.js'));
  const canonicalRoot=path.join(repo,'.local/upstream-mermaid/packages/mermaid/src');
  const rawPins={'diagrams/gantt/ganttRenderer.js':'bf1c7231c8666070124eed4f6078b1d62ab4dea0973c44cc5d6264469961e488','diagrams/git/gitGraphRenderer.ts':'d90f6685b76b2f33bebd6e5b47912c076e77f3180c3e27d821ae06261f1aac81','diagrams/cynefin/cynefinBoundaries.ts':'f5c71c15a4277d9ef36d07962ddb13a7b4fe32e4e038eb5fe10a8999a2c4efd2'};
  function raw(file){const bytes=fs.readFileSync(path.join(canonicalRoot,file));if(hash(bytes)!==rawPins[file])throw Error('Fixed checkout source changed: '+file);const text=bytes.toString('utf8');used.set(file,{name:file,sha256:hash(bytes),repository:'mermaid-checkout'});return text;}
  const estimateRaw=extract(raw('diagrams/gantt/ganttRenderer.js'),'function getEstimatedTickCount');
  const estimate=vm.runInNewContext('('+estimateRaw+')',{dayjs,Infinity});
  const gitRaw=extract(raw('diagrams/git/gitGraphRenderer.ts'),'const findLane');
  const gitErased=gitRaw.replace(/: number\b/g,'');
  const gitContext=vm.createContext({Math,lanes:[]});const findLane=vm.runInContext(gitErased+';findLane',gitContext);
  const randomRaw=extract(raw('diagrams/cynefin/cynefinBoundaries.ts'),'export function seededRandom');
  const seededRandom=vm.runInNewContext('('+randomRaw.replace(/^export /,'').replace(/: number\b/g,'')+')',{Math});
  function date(parts){const d=new Date(0);d.setFullYear(parts[0],(parts[1]??1)-1,parts[2]??1);d.setHours(parts[3]??0,parts[4]??0,parts[5]??0,parts[6]??0);return d;}
  function serialize(d){return d===null?null:{local:[d.getFullYear(),d.getMonth()+1,d.getDate(),d.getHours(),d.getMinutes(),d.getSeconds(),d.getMilliseconds()],epochMs:d.getTime()};}
  function timeTicks(x){
    const start=date(x.start),end=date(x.end),m=/^([1-9]\d*)(millisecond|second|minute|hour|day|week|month)$/.exec(x.interval||'');
    let interval=x.count;
    if(m&&estimate(start,end,+m[1],m[2])<=10000){
      const names={millisecond:'timeMillisecond',second:'timeSecond',minute:'timeMinute',hour:'timeHour',day:'timeDay',month:'timeMonth',week:'time'+x.weekday[0].toUpperCase()+x.weekday.slice(1)};
      interval=time[names[m[2]]].every(+m[1]);
    }
    return time.timeTicks(start,end,interval).map(serialize);
  }
  const doc=JSON.parse(fs.readFileSync(fixtures,'utf8'));const rows=[];
  for(const row of doc.pureProbes){
    const x=row.input;let value=null,error=null;
    try{
      if(row.kind==='parse'){const d=dayjs(x.value,x.format,true);value=d.isValid()?serialize(d.toDate()):null;}
      else if(row.kind==='dayFormat')value=dayjs(date(x.date)).format(x.format);
      else if(row.kind==='axis')value=format.timeFormat(x.format)(date(x.date));
      else if(row.kind==='ticks')value=timeTicks(x);
      else if(row.kind==='gitLane'){gitContext.lanes=x.lanes.slice();value=findLane(x.a,x.b);}
      else if(row.kind==='random')value=seededRandom(x.seed);
      else throw Error('Unknown numerical kind '+row.kind);
    }catch(e){error={name:e.name,message:String(e.message),stack:String(e.stack)};}
    rows.push({id:row.id,kind:row.kind,input:x,value,error});
  }
  fs.mkdirSync(out,{recursive:true});
  const result={schema:'py-mermaid-branch-original-observations/v1',group:'B',fixtureSha256:hash(fs.readFileSync(fixtures)),identity:{commit:'1fb7869866dd619168d840291c9c54b4f129758b',bundleSha256:BUNDLE_SHA,mapSha256:MAP_SHA,wrapperVersion:'exact-source-mechanical-bindings/v1',modules:[...used.values()],dependencies,adapters:[{symbol:'getEstimatedTickCount',transformation:'brace-delimited function extraction only',originalSha256:hash(Buffer.from(estimateRaw))},{symbol:'findLane',transformation:'erase literal TypeScript number annotations only',originalSha256:hash(Buffer.from(gitRaw)),wrapperSha256:hash(Buffer.from(gitErased))},{symbol:'seededRandom',transformation:'remove export and literal TypeScript number annotations only',originalSha256:hash(Buffer.from(randomRaw))}]},environment:{node:process.version,timezone:Intl.DateTimeFormat().resolvedOptions().timeZone,offsetMinutes:new Date().getTimezoneOffset()},rows};
  fs.writeFileSync(path.join(out,'oracle-b.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({rows:rows.length,out}));
}
main().catch(e=>{console.error(e.stack);process.exitCode=1;});
