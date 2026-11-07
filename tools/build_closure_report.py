"""Build a read-only non-VChart closure A/B viewer from one closed Run.
No product execution and no inferred functional acceptance. Failed statuses and
original source/native artifacts remain explicit and byte-identical.
"""
from __future__ import annotations
import argparse,collections,html,json,re,shutil
from pathlib import Path
from run_support import ROOT,file_identity,verify_run,write_json
from build_report_rounds import CSS

def require(ok,message):
 if not ok:raise ValueError(message)
def read(path):return json.loads(path.read_text('utf-8-sig'))
def esc(x):return html.escape(str(x),quote=True)
def closed_run(path):
 for folder in [path.resolve(),*path.resolve().parents]:
  if (folder/'run.json').is_file():return folder
 raise ValueError('Input is not bound to a closed Run: '+str(path))
def ids(rows):
 result={r['id']:r for r in rows}
 require(len(result)==len(rows),'Duplicate case IDs')
 return result

def build(args):
 fixture=args.fixtures.resolve(strict=True);oracle=args.oracle.resolve(strict=True)
 native=[p.resolve(strict=True) for p in args.native]
 run=closed_run(fixture)
 require(all(closed_run(p)==run for p in [oracle,*native]),'Fixtures/oracle/native must belong to the same closed Run')
 integrity=verify_run(run);require(integrity['integrityStatus']=='PASS','Closed Run integrity failed: '+str(integrity['errors']))
 rm=read(run/'run.json');require(rm.get('sourceUnchanged') is True,'Candidate source changed during Run')
 sha=rm['source']['sourceTreeSha256'];candidate=run.relative_to(ROOT).as_posix()
 rows=read(fixture)['cases'];cases=ids(rows)
 require(cases and all(r['expect'] not in ('parser_only','excluded_by_static_scope') and not r.get('parserOnly') for r in rows),'Only rendered/error fixtures supported')
 require(all(re.fullmatch(r'[A-Za-z0-9_.-]+',k) for k in cases),'Unsafe case ID')
 om=read(oracle/'manifest.json');original=ids(om['cases'])
 require(set(original)==set(cases),'Original case denominator differs')
 require(om.get('identity',{}).get('commit')=='1fb7869866dd619168d840291c9c54b4f129758b','Wrong fixed Mermaid source')
 profiles={}
 for folder in native:
  result=read(folder/'results.json');identity=read(folder/'identity.json');profile=result['backend']
  require(profile not in profiles and profile in ('cpu','auto','gpu'),'Duplicate/invalid backend')
  require(result.get('sourceUnchanged') is True and result['source']['sourceTreeSha256']==sha and identity['source']['sourceTreeSha256']==sha,'Native source identity differs')
  mapped=ids(result['cases']);require(set(mapped)==set(cases),'Native case denominator differs: '+profile)
  require(all(r['status'] in ('CHECKS_PASSED','FAILED','ERROR','EXPECTED_ERROR') for r in mapped.values()),'Unknown native status')
  profiles[profile]=(folder,mapped)
 require(profiles,'At least one native profile required')
 acceptance=None;review=None
 for path,which in [(args.acceptance,'acceptance'),(args.visual_review,'review')]:
  if path is None:continue
  data=read(path)
  require(data.get('candidateRun')==candidate and data.get('sourceTreeSha256')==sha,which+' is not bound to this candidate')
  if which=='acceptance':
   require(data.get('status')=='PASS', 'Acceptance must explicitly PASS')
   require(rm['status']=='SUCCESS' and all(c['exitCode']==0 for c in rm['commands']),'Acceptance cannot override failed execution')
   acceptance=data
  else:review=data
 output=args.out.resolve();require(not output.exists(),'Output directory must be new')
 require(not any(p.is_relative_to(output) for p in [fixture,oracle,*native]),'Output contains evidence input')
 output.mkdir(parents=True);(output/'attachments').mkdir()
 manifest=dict(schema='py-mermaid-closure-report/v1',pageSize=12,purpose='READ_ONLY_NON_VCHART_CLOSURE',functionalStatus='NOT_REEVALUATED',
               status='REPORT_CREATED_NOT_NEW_ACCEPTANCE',candidateRun=candidate,sourceTreeSha256=sha,runStatus=rm['status'],profiles=list(profiles),assets={},pages=[],items=[])
 copied={}
 def attach(path):
  path=path.resolve(strict=True);require(path.is_relative_to(ROOT) and path.is_file() and not path.is_symlink(),'Evidence path unsafe')
  original_path=path.relative_to(ROOT).as_posix();identity=file_identity(path)
  # Every actual execution artifact must be declared by its immutable Run.
  if path.is_relative_to(run) and path!=run/'run.json':require(rm['artifacts'].get(path.relative_to(run).as_posix())==identity,'Unbound Run artifact '+str(path))
  if original_path not in copied:
   target='attachments/'+f'{len(copied)+1:05d}-'+path.name
   shutil.copyfile(path,output/target);require(file_identity(output/target)==identity,'Copy changed bytes')
   manifest['assets'][target]={'originalPath':original_path,**identity};copied[original_path]=target
  return copied[original_path]
 globals_=[attach(p) for p in [fixture,run/'run.json',oracle/'manifest.json',*[p/f for p in native for f in ('results.json','identity.json')]]]
 for name in ('source-A/results.json','source-A/identity.json','source-B/browser-manifest.json','source-B/values/oracle-b.json',
              'comparison-B.json',*[f'comparison-C-{p}.json' for p in profiles],*[f'comparison-collapsed-{p}.json' for p in profiles],*[f'comparison-event-{p}.json' for p in profiles]):
  path=run/'artifacts'/name
  if path.is_file():globals_.append(attach(path))
 for optional in (args.acceptance,args.visual_review):
  if optional:globals_.append(attach(optional))
 rendered=[]
 for row in rows:
  id=row['id'];links=[];images=[];source_file=output/'attachments'/(id+'.source')
  source_file.write_bytes(row['source'].encode('utf8'));manifest['assets']['attachments/'+source_file.name]={'derived':True,'caseId':id,'description':'Exact UTF-8 fixture source',**file_identity(source_file)}
  links.append('attachments/'+source_file.name)
  for suffix in ('.json','.error.json','.svg','.png'):
   p=oracle/(id+suffix)
   if p.is_file():
    target=attach(p);links.append(target)
    if suffix=='.png':images.append(('Original',target))
  require(any(p.name in (id+'.json',id+'.error.json') for p in oracle.iterdir()),'Missing original status artifact '+id)
  statuses={}
  for profile,(folder,mapped) in profiles.items():
   status=mapped[id]['status'];statuses[profile]=status
   result_path=folder/(id+'.result.json');require(result_path.is_file(),'Missing per-ID result '+id);links.append(attach(result_path))
   if status=='CHECKS_PASSED':require((folder/(id+'.png')).is_file() and (folder/(id+'.scene.json')).is_file(),'Successful case missing real PNG/scene')
   for suffix in ('.scene.json','.png'):
    p=folder/(id+suffix)
    if p.is_file():
     target=attach(p);links.append(target)
     if suffix=='.png':images.append((profile,target))
  item={'id':id,'kind':row['kind'],'group':row.get('group',''),'expect':row['expect'],'status':' / '.join(k+':'+v for k,v in statuses.items()),'nativeStatuses':statuses,'originalStatus':original[id]['status'],'links':links,'images':images}
  rendered.append(item)
 def page(title,body):return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+esc(title)+'</title><style>'+CSS+'p,li{overflow-wrap:anywhere}</style><header><nav><a href="index.html">Home</a><a href="manifest.json">Manifest</a></nav><h1>'+esc(title)+'</h1><p>Non-VChart closure · NOT_NEW_ACCEPTANCE · '+esc(rm['status'])+'</p></header><main>'+body+'</main></html>'
 grouped=collections.defaultdict(list)
 for row in rendered:grouped[row['group'] or row['kind']].append(row)
 home='<p>Candidate '+esc(candidate)+' / '+esc(sha)+'</p><p>Acceptance: '+esc(acceptance['status'] if acceptance else 'NOT PROVIDED')+'; visual review: '+esc(review.get('status','provided') if review else 'NOT PROVIDED')+'</p><h2>Evidence</h2><ul>'+''.join('<li><a href="'+p+'">'+esc(p)+'</a></li>' for p in globals_)+'</ul>'
 if acceptance:
  home+='<h2>Scope and release gates</h2><p>'+esc(acceptance.get('meaning',''))+'</p><ul>'+''.join('<li>'+esc(g)+'</li>' for g in acceptance.get('remainingExternalReleaseGates',[]))+'</ul>'
 if review:
  home+='<h2>Actual image review</h2><p>'+esc(review.get('summary',''))+'</p>'
  for finding in review.get('findings',[]):home+='<p>'+esc(json.dumps(finding,ensure_ascii=False))+'</p>'
 for group,items in sorted(grouped.items()):
  home+='<h2>'+esc(group)+' ('+str(len(items))+')</h2><nav>'
  for i in range(0,len(items),12):
   name='page-'+str(len(manifest['pages'])+1).zfill(3)+'.html';batch=items[i:i+12];home+='<a href="'+name+'">'+esc(name)+'</a>';body=''
   for row in batch:
    anchor='case-'+row['id'];manifest['items'].append({**row,'page':name,'anchor':anchor})
    body+='<article class="case" id="'+anchor+'" data-case="'+row['id']+'" data-status="'+esc(row['status'])+'"><h2>'+esc(row['id'])+'</h2><p>'+esc(row['kind']+' · '+row['status']+' · Original '+row['originalStatus'])+'</p><div class="grid">'+''.join('<section><h3>'+esc(label)+'</h3><div class="image"><img loading="lazy" src="'+p+'" alt="'+esc(row['id']+' '+label)+'"></div></section>' for label,p in row['images'])+'</div><details><summary>Raw source, state and artifacts</summary><pre>'+esc(json.dumps(row,ensure_ascii=False,indent=2))+'</pre><ul>'+''.join('<li><a href="'+p+'" download>'+esc(p)+'</a></li>' for p in row['links'])+'</ul></details></article>'
   (output/name).write_text(page('Closure '+group,body),encoding='utf8');manifest['pages'].append({'path':name,'items':len(batch),**file_identity(output/name)})
  home+='</nav>'
 (output/'index.html').write_text(page('Non-VChart closure evidence',home),encoding='utf8')
 manifest['index']=file_identity(output/'index.html');manifest['caseCount']=len(rows);manifest['counts']=dict(collections.Counter(r['kind'] for r in rows));manifest['acceptanceStatus']=acceptance['status'] if acceptance else 'NOT_PROVIDED'
 write_json(output/'manifest.json',manifest,exclusive=True)
 return {'status':manifest['status'],'cases':len(rows),'pages':len(manifest['pages']),'out':str(output)}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixtures',type=Path,required=True);p.add_argument('--oracle',type=Path,required=True);p.add_argument('--native',type=Path,nargs='+',action='extend',required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--acceptance',type=Path);p.add_argument('--visual-review',type=Path)
 print(json.dumps(build(p.parse_args())));return 0
if __name__=='__main__':raise SystemExit(main())
