"""GitHub release transport using existing credentials without logging secrets."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tomllib
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PROJECT = tomllib.loads((ROOT / 'pyproject.toml').read_text('utf-8'))['project']
API = 'https://api.github.com/repos/py-VisActor/py-mermaid'


def credentials():
    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if token:
        return token
    result = subprocess.run(['git', 'credential', 'fill'],
        input='protocol=https\nhost=github.com\n\n', capture_output=True, text=True,
        env={**os.environ, 'GIT_TERMINAL_PROMPT': '0', 'GCM_INTERACTIVE': 'never'})
    values = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
    if not values.get('password'):
        raise RuntimeError('No existing GitHub credential is available')
    return values['password']


def request(url, *, method='GET', data=None, missing=False):
    if urllib.parse.urlsplit(url).hostname not in {'api.github.com', 'uploads.github.com'}:
        raise ValueError('Credentials are restricted to GitHub API hosts')
    raw = json.dumps(data).encode() if isinstance(data, dict) else data
    req = urllib.request.Request(url, data=raw, method=method, headers={
        'Authorization': 'Bearer ' + credentials(), 'Accept': 'application/vnd.github+json',
        'Content-Type': 'application/json' if isinstance(data, dict) else 'application/octet-stream',
        'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'py-mermaid-release'})
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            body = response.read()
            return json.loads(body) if body else None
    except urllib.error.HTTPError as error:
        if missing and error.code == 404:
            return None
        raise RuntimeError(f'GitHub {method} failed ({error.code}): ' + error.read().decode()[:1500]) from None


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def download(tag, manifest_sha, out):
    release = request(API + '/releases/tags/' + urllib.parse.quote(tag, safe=''))
    assets = {item['name']: item for item in release['assets']}
    with urllib.request.urlopen(assets['release-manifest.json']['browser_download_url'], timeout=90) as r:
        raw = r.read()
    assert hashlib.sha256(raw).hexdigest() == manifest_sha, 'Reviewed manifest differs'
    manifest = json.loads(raw)
    assert manifest['project'] == PROJECT['name'] and manifest['version'] == PROJECT['version']
    assert manifest['tag'] == tag and len(manifest['distributions']) == 2
    assert not manifest.get('dirtySource'), 'Development artifacts cannot be published'
    assert manifest['sourceCommit'] == subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    from run_support import source_identity
    assert source_identity()['sourceTreeSha256'] == manifest['sourceTreeSha256'], 'Reviewed product source differs'
    out.mkdir(parents=True, exist_ok=False)
    (out / 'release-manifest.json').write_bytes(raw)
    packages = out / 'packages'
    packages.mkdir()
    for name, identity in manifest['distributions'].items():
        assert Path(name).name == name and name.endswith(('.whl', '.tar.gz'))
        with urllib.request.urlopen(assets[name]['browser_download_url'], timeout=120) as r:
            body = r.read()
        assert len(body) == identity['bytes'] and hashlib.sha256(body).hexdigest() == identity['sha256']
        (packages / name).write_bytes(body)
    return {'status': 'VERIFIED', 'url': release['html_url'], 'manifestSha256': manifest_sha}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['create', 'download', 'dispatch', 'status', 'promote'])
    p.add_argument('--tag', default=PROJECT['name'] + '-v' + PROJECT['version'])
    p.add_argument('--manifest', type=Path)
    p.add_argument('--manifest-sha256')
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--publish', action='store_true')
    args = p.parse_args()
    if args.action == 'download':
        result = download(args.tag, args.manifest_sha256, args.out)
    else:
        args.out.mkdir(parents=True, exist_ok=False)
        if args.action == 'create':
            manifest = json.loads(args.manifest.read_text('utf-8'))
            assert manifest['tag'] == args.tag and manifest['project'] == PROJECT['name']
            assert not manifest.get('dirtySource'), 'Development artifacts cannot be published'
            assert manifest['sourceCommit'] == subprocess.check_output(['git', 'rev-parse', args.tag + '^{commit}'], cwd=ROOT, text=True).strip()
            from release_package import checked_distributions
            files = checked_distributions(manifest, args.manifest.parent / 'packages')
            release = request(API + '/releases/tags/' + args.tag, missing=True)
            if release is None:
                release = request(API + '/releases', method='POST', data={
                    'tag_name': args.tag, 'target_commitish': manifest['sourceCommit'],
                    'name': 'py-mermaid ' + PROJECT['version'],
                    'body': (ROOT / 'docs/releases' / (PROJECT['version'] + '.md')).read_text('utf-8'),
                    'prerelease': True, 'draft': False, 'make_latest': 'false'})
            files.append(args.manifest)
            for file in files:
                current = next((a for a in release['assets'] if a['name'] == file.name), None)
                if current:
                    assert current.get('digest') == 'sha256:' + sha(file), 'Never overwrite released bytes'
                    continue
                request(release['upload_url'].split('{')[0] + '?name=' + urllib.parse.quote(file.name),
                        method='POST', data=file.read_bytes())
            result = request(API + '/releases/' + str(release['id']))
        elif args.action == 'dispatch':
            assert args.manifest_sha256 and len(args.manifest_sha256) == 64
            if request(API + '/environments/pypi', missing=True) is None:
                request(API + '/environments/pypi', method='PUT', data={})
            request(API + '/actions/workflows/publish-pypi.yml/dispatches', method='POST',
                    data={'ref': 'main', 'inputs': {'release_tag': args.tag, 'manifest_sha256': args.manifest_sha256, 'publish': str(args.publish).lower()}})
            result = {'status': 'DISPATCHED', 'tag': args.tag}
        elif args.action == 'promote':
            release = request(API + '/releases/tags/' + args.tag)
            assert args.manifest, 'Stable promotion requires the verified reviewed manifest'
            manifest = json.loads(args.manifest.read_text('utf-8'))
            assert manifest['tag'] == args.tag and not manifest['dirtySource']
            pypi_url = 'https://pypi.org/pypi/' + manifest['project'] + '/' + manifest['version'] + '/json'
            with urllib.request.urlopen(pypi_url, timeout=60) as response:
                actual = {item['filename']: item for item in json.load(response)['urls']}
            assert set(actual) == set(manifest['distributions'])
            assert all(actual[name]['digests']['sha256'] == value['sha256'] and actual[name]['size'] == value['bytes'] for name,value in manifest['distributions'].items())
            result = request(API + '/releases/' + str(release['id']), method='PATCH',
                             data={'prerelease': False, 'make_latest': 'true'})
        else:
            runs = request(API + '/actions/workflows/publish-pypi.yml/runs?per_page=5')
            result = {'runs': [{k: row[k] for k in ('id', 'head_sha', 'status', 'conclusion', 'html_url')} for row in runs['workflow_runs']]}
    (args.out / 'result.json').write_text(json.dumps(result, indent=2) + '\n', 'utf-8')
    print(json.dumps({k: result[k] for k in ('status', 'html_url', 'runs') if k in result}))


if __name__ == '__main__':
    main()
