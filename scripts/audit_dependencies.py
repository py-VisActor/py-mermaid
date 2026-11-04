"""Inventory pinned manifests, pnpm dependency edges and literal source imports.

Standard library only. The pnpm reader intentionally supports only the locked
v9 mapping/scalar structures needed here, not arbitrary YAML. No npm install,
JS execution, network, product import or rendering is performed.
"""
from __future__ import annotations
import argparse
from collections import defaultdict, deque
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'.local/upstream-mermaid'
PACKAGES=('packages/mermaid','packages/parser','packages/mermaid-layout-elk',
          'packages/mermaid-layout-tidy-tree','packages/mermaid-zenuml')
OUT=ROOT/'references/dependencies.json'


def scalar(value):
    value=value.strip()
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    if value.startswith('"') and value.endswith('"'):
        return json.loads(value)
    return value


def blocks(text,indent):
    """Return exact same-indent mapping blocks, including empty mappings."""
    rows=[];current=None;lines=[]
    pattern=re.compile(r'^ {'+str(indent)+r'}(\S.*?):(?:\s*\{\})?\s*$')
    for line in text.splitlines():
        match=pattern.match(line)
        if match:
            if current is not None:rows.append((current,'\n'.join(lines)))
            current=scalar(match[1]);lines=[]
        elif line.strip() and not line.lstrip().startswith('#') and len(line)-len(line.lstrip())<=indent:
            if current is not None:rows.append((current,'\n'.join(lines)))
            current=None;lines=[]
        elif current is not None:
            lines.append(line)
    if current is not None:rows.append((current,'\n'.join(lines)))
    if len({name for name, _ in rows}) != len(rows):
        raise ValueError('Duplicate pnpm mapping key')
    return dict(rows)


def mapping_values(text,indent):
    result={}
    for line in text.splitlines():
        if not line.strip():continue
        match=re.match(r'^ {'+str(indent)+r'}(\S.*?):\s+(.+)$',line)
        if not match:raise ValueError('Unsupported dependency mapping: '+line)
        result[scalar(match[1])]=scalar(match[2])
    return result


def git_bytes(path):
    return subprocess.check_output(['git','-C',str(SOURCE),'show','HEAD:'+path])


def package_name(specifier):
    if specifier.startswith(('.', '/', '#', 'node:')):return None
    return '/'.join(specifier.split('/')[:2])if specifier.startswith('@')else specifier.split('/')[0]


def source_imports():
    # Literal-import candidates, not a TypeScript AST or bundle reachability.
    tree=subprocess.check_output(['git','-C',str(SOURCE),'ls-tree','-r','--format=%(objectname) %(path)','HEAD',
                                  *[p+'/src'for p in PACKAGES]]).decode().splitlines()
    selected=[]
    for row in tree:
        oid,name=row.split(' ',1)
        if Path(name).suffix not in ('.ts','.js','.mts','.mjs','.cjs'):continue
        if any(p in name for p in ('/tests/','/__tests__/','/__mocks__/','/docs/','/vitepress/','.spec.','.test.')):continue
        selected.append((oid,name))
    packed=subprocess.check_output(['git','-C',str(SOURCE),'cat-file','--batch'],
                                   input=('\n'.join(oid for oid,_ in selected)+'\n').encode())
    offset=0
    imports=defaultdict(list);scanned={}
    pattern=re.compile(r'\b(?:from\s+|import\s+|import\s*\(\s*|require\s*\(\s*)([\'"`])([^\'"`\r\n]+)\1')
    for oid,name in selected:
        end=packed.index(b'\n',offset);header=packed[offset:end].decode().split()
        if header[:2]!=[oid,'blob']:raise ValueError('Unexpected canonical source object')
        size=int(header[2]);raw=packed[end+1:end+1+size];offset=end+size+2
        text=raw.decode('utf-8')
        scanned[name]=hashlib.sha256(raw).hexdigest()
        # Preserve line locations while excluding JSDoc/block and full-line comments.
        clean=re.sub(r'/\*.*?\*/',lambda m:'\n'*m[0].count('\n'),text,flags=re.S)
        clean=re.sub(r'(?m)^\s*//[^\n]*','',clean)
        for match in pattern.finditer(clean):
            spec=match[2]
            if '${'in spec:continue
            package=package_name(spec)
            if package is None:continue
            start=clean.rfind(';',0,match.start())+1
            statement=clean[start:match.end()].lstrip()
            token=clean[match.start():match.start(1)].lstrip()
            if token.startswith('from')and not re.match(r'(?:import|export)\b',statement):continue
            kind='type_only'if re.match(r'(?:import|export)\s+type\b',statement)else'value_or_mixed_candidate'
            imports[package].append({'path':name,'line':clean.count('\n',0,match.start())+1,
                                     'specifier':spec,'kind':kind})
    return dict(sorted(imports.items())),scanned


def build():
    lock=json.loads((ROOT/'references/upstream.lock.json').read_bytes())
    commit=subprocess.check_output(['git','-C',str(SOURCE),'rev-parse','HEAD']).decode().strip()
    if commit!=lock['commit']:raise ValueError('Pinned source commit differs')
    if subprocess.check_output(['git','-C',str(SOURCE),'status','--porcelain','--untracked-files=normal']).strip():
        raise ValueError('Pinned checkout is dirty')
    files={};manifests={}
    for name in ('package.json','pnpm-lock.yaml',*[p+'/package.json'for p in PACKAGES]):
        raw=git_bytes(name);sha=hashlib.sha256(raw).hexdigest()
        if name in lock['sha256'] and sha!=lock['sha256'][name]:raise ValueError('Pinned SHA differs: '+name)
        files[name]=sha
        if name.endswith('.json'):manifests[name.removesuffix('/package.json')]=json.loads(raw)
    lock_text=git_bytes('pnpm-lock.yaml').decode()
    if not re.search(r"(?m)^lockfileVersion: '9\.0'$",lock_text):raise ValueError('Expected pinned pnpm v9 structure')
    sections=blocks(lock_text,0)
    importers=blocks(sections['importers'],2)
    snapshots=blocks(sections['snapshots'],2)
    resolutions={}
    for importer,text in importers.items():
        groups={}
        for group,body in blocks(text,4).items():
            if group not in ('dependencies','devDependencies','optionalDependencies'):continue
            groups[group]={name:mapping_values(fields,8)for name,fields in blocks(body,6).items()}
        resolutions[importer]=groups
    graph={}
    package_records=blocks(sections['packages'],2)
    unresolved=[]
    for node,body in snapshots.items():
        deps={}
        for group,fields in blocks(body,4).items():
            if group in ('dependencies','optionalDependencies'):
                deps.update(mapping_values(fields,6))
        graph[node]=deps
    def target(name,version):
        key=name+'@'+version
        if key in graph:return key
        if version in graph:return version  # npm aliases
        return None
    rows=[];roots=set()
    for importer in PACKAGES:
        manifest=manifests[importer]
        for group in ('dependencies','devDependencies','peerDependencies','optionalDependencies'):
            for name,requested in manifest.get(group,{}).items():
                resolved=resolutions.get(importer,{}).get(group,{}).get(name,{})
                version=resolved.get('version')
                if group in ('dependencies','devDependencies','optionalDependencies')and version is None:
                    raise ValueError('No importer resolution: '+importer+'/'+name)
                row={'owner':manifest['name'],'importer':importer,'group':group,'name':name,
                     'declared':requested,'lockSpecifier':resolved.get('specifier'),'resolved':version,
                     'workspace':bool(version and version.startswith('link:')),
                     'typesPackage':name.startswith('@types/')or name=='@chevrotain/types'}
                rows.append(row)
                if group=='dependencies'and version and not row['workspace']:
                    root=target(name,version)
                    if root is None:raise ValueError('Missing snapshot: '+name+'@'+version)
                    roots.add(root)
    reached=set();queue=deque(sorted(roots))
    while queue:
        node=queue.popleft()
        if node in reached:continue
        reached.add(node)
        for name,version in graph[node].items():
            child=target(name,version)
            if child is None:unresolved.append({'parent':node,'name':name,'version':version})
            elif child not in reached:queue.append(child)
    if unresolved:
        raise ValueError('Unresolved dependency snapshot edges: '+json.dumps(unresolved))
    imports,scanned=source_imports()
    declarations={row['name']for row in rows}
    extras=[{'name':name,'references':references,'declaredInAuditedPackages':name in declarations,
             'rootWorkspaceResolution':resolutions.get('.',{}).get('devDependencies',{}).get(name)}
            for name,references in imports.items()if name not in {r['name']for r in rows if r['group']=='dependencies'}
            and name!='mermaid']
    return {'schema':'py-mermaid-dependency-inventory/v1','upstreamVersion':lock['version'],
      'upstreamCommit':commit,'canonicalInputsSha256':files,
      'packages':[{'path':p,'name':manifests[p]['name'],'version':manifests[p]['version'],
                   'license':manifests[p].get('license')}for p in PACKAGES],
      'declarations':rows,'coreDependencyCount':len(manifests['packages/mermaid']['dependencies']),
      'literalImports':imports,'scannedSourceFilesSha256':scanned,'additionalSourceImports':extras,
      'declaredProductionClosure':{'snapshotCount':len(reached),'nodes':sorted(reached),
          'edges':{name:graph[name]for name in sorted(reached)},'unresolved':unresolved,
          'registryIntegrity':{name:(re.search(r'\bintegrity:\s*([^,}\s]+)',
                           package_records.get(name.split('(',1)[0],''))[1]
                           if re.search(r'\bintegrity:\s*([^,}\s]+)',package_records.get(name.split('(',1)[0],''))else None)
                           for name in sorted(reached)}},
      'patches':{name:{'sha256':hashlib.sha256(git_bytes(name)).hexdigest(),
                        'content':git_bytes(name).decode()}for name in ('patches/roughjs.patch','patches/fastdom.patch')},
      'pythonDeclaredDependencies':__import__('tomllib').loads((ROOT/'pyproject.toml').read_text('utf-8'))['project']['dependencies'],
      'limitations':['Manifest production closure includes declared types and resolved optional/peer contexts; it is not an executed bundle or minimal runtime SBOM.',
        'Literal import candidates exclude conventional tests/docs; no complete TypeScript AST, tree shaking, generated-code or computed-import reachability claim.',
        'devDependency placement does not imply no runtime/bundled semantics. Source extras are listed separately from the declared production closure.',
        'Third-party transitive package licenses/tarball bytes have not been fetched or audited; only first-party manifest license fields are recorded.',
        'No Python Mermaid parser/layout/render or py-elk integration is implemented by this inventory.'],
      'productOrSourceExecutions':0,'networkRequests':0}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--build',action='store_true');mode.add_argument('--check',action='store_true')
    args=parser.parse_args();data=build()
    raw=json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
    if args.build:OUT.write_text(raw,encoding='utf-8',newline='\n')
    elif OUT.read_text('utf-8')!=raw:raise ValueError('Dependency inventory differs from pinned source and lock')
    print(json.dumps({'coreDependencies':data['coreDependencyCount'],
        'declarations':len(data['declarations']),'literalPackages':len(data['literalImports']),
        'productionClosureSnapshots':data['declaredProductionClosure']['snapshotCount'],
        'unresolvedEdges':len(data['declaredProductionClosure']['unresolved']),
        'productOrSourceExecutions':0,'networkRequests':0}))


if __name__=='__main__':main()
