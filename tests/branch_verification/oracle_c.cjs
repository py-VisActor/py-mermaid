/* Independent development-only fixed parser probe. Never imports Python. */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {pathToFileURL}=require('node:url');
const root=path.resolve(__dirname,'../..'),arg=name=>process.argv[process.argv.indexOf(name)+1];
if(process.argv.includes('--help')){console.log('node oracle_c.cjs --out NEWDIR (fixed offline @mermaid-js/parser ABNF priority)');process.exit(0);}
const sha=buffer=>crypto.createHash('sha256').update(buffer).digest('hex');
const probes=[
 ['bare-terminator','railroad-abnf-beta\nword = "a";'],
 ['trailing-comment','railroad-abnf-beta\nword = "a"; trailing comment\n'],
 ['comment-line','railroad-abnf-beta\n; comment only\nword = "a";'],
 ['quoted-semicolon','railroad-abnf-beta\nword = "a;b";'],
 ['two-rules','railroad-abnf-beta\nfirst = "a";\nsecond = "b";']
];
(async()=>{
 const out=path.resolve(arg('--out'));if(!process.argv.includes('--out')||fs.existsSync(out))throw Error('Requires new --out directory');
 const pkg=path.join(root,'.local/f011-oracle/node_modules/@mermaid-js/parser');
 const packageJson=JSON.parse(fs.readFileSync(path.join(pkg,'package.json'),'utf8'));
 if(packageJson.version!=='2.0.1')throw Error('Fixed parser version drift');
 const entry=path.join(pkg,'dist/mermaid-parser.core.mjs');
 const source=path.join(root,'.local/upstream-mermaid/packages/parser/src/language/railroad-abnf/railroad-abnf.langium');
 if(sha(fs.readFileSync(source))!=='d156141dab0c649a6a063c59a5d277aec56eda295f955d5c65c28cffe077ad84')throw Error('Fixed ABNF grammar drift');
 const mod=await import(pathToFileURL(entry).href);
 const parser=mod.createRailroadAbnfServices().RailroadAbnf.parser.LangiumParser;
 const cases=probes.map(([id,source])=>{
  const result=parser.parse(source);
  const errors=[...(result.lexerErrors||result.lexingErrors||[]),...(result.parserErrors||[])];
  return {id,source,accepted:errors.length===0,rules:(result.value?.rules||[]).map(r=>r.name),
          errors:errors.map(e=>({name:e.name,message:e.message,offset:e.offset??e.token?.startOffset}))};
 });
 fs.mkdirSync(out,{recursive:true});fs.writeFileSync(path.join(out,'abnf.json'),JSON.stringify({schema:'py-mermaid-C-source-priority/v1',
  package:'@mermaid-js/parser@2.0.1',entrySha256:sha(fs.readFileSync(entry)),grammarSha256:sha(fs.readFileSync(source)),cases},null,2)+'\n');
 console.log(JSON.stringify({status:'SOURCE_OBSERVED',cases:cases.length,accepted:cases.filter(c=>c.accepted).map(c=>c.id)}));
})().catch(error=>{console.error(error.stack);process.exitCode=1;});
