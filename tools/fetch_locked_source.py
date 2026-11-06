"""Acquire a fixed npm source archive for development inspection, never install.

Requires the lockfile's integrity value. Every download/extraction is recorded
in a fresh standard run; no archive writes outside .local/bulk-sources.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import tarfile
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
from run_support import ROOT, Run, write_json, file_identity

MAX_BYTES=128*1024*1024


def read_url(url):
    if urlparse(url).scheme!='https':raise ValueError('Source download must use HTTPS')
    with urlopen(Request(url,headers={'User-Agent':'py-mermaid-locked-source/1'}),timeout=60) as response:
        result=response.read(MAX_BYTES+1)
    if len(result)>MAX_BYTES:raise ValueError('Source download exceeds budget')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package');parser.add_argument('version');parser.add_argument('--integrity',required=True)
    args=parser.parse_args()
    if not re.fullmatch(r'(?:@[a-zA-Z0-9_.-]+/)?[a-zA-Z0-9_.-]+',args.package) or not re.fullmatch(r'[a-zA-Z0-9_.+-]+',args.version):raise ValueError('Invalid fixed package identity')
    tokens=args.integrity.split()
    if len(tokens)!=1 or '-' not in tokens[0]:raise ValueError('One exact lockfile integrity value required')
    algorithm,expected=tokens[0].split('-',1)
    if algorithm not in ('sha512','sha256'):raise ValueError('Strong integrity hash required')
    cache_root=(ROOT/'.local/bulk-sources').resolve()
    target=(cache_root/(args.package.replace('@','').replace('/','-')+'-'+args.version)).resolve()
    if not target.is_relative_to(cache_root):raise ValueError('Invalid extraction target')
    with Run('SOURCE','acquire') as run:
        if target.exists():raise FileExistsError('Source cache exists; inspect its receipt instead of overwriting: '+str(target))
        metadata_url='https://registry.npmjs.org/'+quote(args.package,safe='@')+'/'+quote(args.version,safe='')
        metadata_bytes=read_url(metadata_url);metadata=json.loads(metadata_bytes)
        if metadata.get('name')!=args.package or metadata.get('version')!=args.version:raise ValueError('Registry package identity mismatch')
        tarball_url=metadata['dist']['tarball'];archive=read_url(tarball_url)
        digest=base64.b64encode(hashlib.new(algorithm,archive).digest()).decode('ascii')
        if digest!=expected:raise ValueError('Source archive differs from lockfile integrity')
        metadata_path=run.path/'artifacts/npm-metadata.json';metadata_path.write_bytes(metadata_bytes)
        archive_path=run.path/'artifacts/source.tgz';archive_path.write_bytes(archive)
        members=[]
        with tarfile.open(fileobj=io.BytesIO(archive),mode='r:gz') as tar:
            total=0
            for member in tar.getmembers():
                pure=PurePosixPath(member.name)
                destination=(target/Path(*pure.parts)).resolve()
                if not destination.is_relative_to(target) or pure.is_absolute() or '..' in pure.parts or '\\' in member.name or ':' in member.name or member.issym() or member.islnk() or not (member.isfile() or member.isdir()):
                    raise ValueError('Unsafe source archive member: '+member.name)
                total+=member.size
                if total>MAX_BYTES:raise ValueError('Expanded source exceeds budget')
                members.append(member)
            target.mkdir(parents=True,exist_ok=False)
            tar.extractall(target,members=members,filter='data')
        receipt={'schema':'py-mermaid-locked-source/v1','package':args.package,'version':args.version,'expectedIntegrity':args.integrity,
            'registry':metadata_url,'tarball':tarball_url,'tarballIdentity':file_identity(archive_path),'gitHead':metadata.get('gitHead'),
            'license':metadata.get('license'),'runId':run.id,'sourceDirectory':str(target),
            'files':{p.relative_to(target).as_posix():file_identity(p) for p in sorted(target.rglob('*')) if p.is_file()}}
        write_json(target/'source-receipt.json',receipt,exclusive=True);write_json(run.path/'artifacts/source-receipt.json',receipt)
        run.event('locked_source_acquired',package=args.package,version=args.version,integrityVerified=True,directory=str(target))
        print(json.dumps({'runId':run.id,'sourceDirectory':str(target),'license':metadata.get('license'),'sha256':receipt['tarballIdentity']['sha256']}))


if __name__=='__main__':main()
