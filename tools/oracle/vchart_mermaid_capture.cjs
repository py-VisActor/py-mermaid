/* Development-only seven-DSL original oracle. Production never loads JS. */
const fs=require('node:fs'),path=require('node:path'),cp=require('node:child_process'),crypto=require('node:crypto');
const arg=n=>{const i=process.argv.indexOf(n);return i<0?null:process.argv[i+1]};
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const root=path.resolve(__dirname,'../..');
function main(){
 if(!arg('--fixtures')||!arg('--out'))throw Error('--fixtures FILE --out NEWDIR required');
 const input=path.resolve(arg('--fixtures')),out=path.resolve(arg('--out'));
 if(fs.existsSync(out))throw Error('Output must be new: '+out);
 const fixture=JSON.parse(fs.readFileSync(input));
 const extra=(fixture.unsupportedCases||[]).map(c=>({...c,group:'A'}));
 const combined={...fixture,cases:[...fixture.cases,...extra]};
 const transport=out+'.fixtures.json';
 fs.writeFileSync(transport,JSON.stringify(combined,null,2)+'\n',{flag:'wx'});
 cp.execFileSync(process.execPath,[path.join(root,'tools/oracle/bulk_capture.cjs'),
  '--fixtures',transport,'--out',out],{stdio:'inherit'});
 const manifest=JSON.parse(fs.readFileSync(path.join(out,'manifest.json')));
 const expected=new Map(combined.cases.map(c=>[c.id,c]));
 const rows=manifest.cases.map(actual=>{
  const c=expected.get(actual.id),negative=c.expect==='syntax_error';
  const matches=negative?actual.status==='error'&&Boolean(actual.sourceError):actual.status==='captured';
  return {id:c.id,kind:c.kind,sourceExpectation:c.expect,status:actual.status,expectationMatches:matches,
   nativeRestrictionOnly:Boolean(c.nativeExpectedErrorCodes),sourceError:actual.sourceError||null};
 });
 const summary={schema:'py-mermaid-vchart-original/v1',input:{path:input,sha256:sha(fs.readFileSync(input))},
  transport:{path:transport,sha256:sha(fs.readFileSync(transport))},identity:manifest.identity,
  cases:rows,failed:rows.filter(r=>!r.expectationMatches).length,
  note:'Original inputs include native restriction probes. Their source-success is not native success.'};
 fs.writeFileSync(path.join(out,'vchart-mermaid-source-summary.json'),JSON.stringify(summary,null,2)+'\n',{flag:'wx'});
 if(summary.failed)process.exitCode=1;
}
try{main()}catch(e){console.error(e.stack||String(e));process.exitCode=1}
