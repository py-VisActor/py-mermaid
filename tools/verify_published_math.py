"""Verify published mathematics through external wheel/sdist installations.

Use tools/workflow.py batch for immutable command logs. This is development
verification only; production imports the normal installed py_katex package.
"""
from pathlib import Path
import argparse
import email
import hashlib
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import venv
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = ['py-skia-canvas==0.1.0a18', 'py-visactor-elk==0.1.0', 'py-visactor-katex==0.1.0']


def read(path):
    return json.loads(path.read_text('utf-8'))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', 'utf-8')


def metadata(raw):
    item = email.message_from_bytes(raw)
    assert item['Name'] == 'py-mermaid' and item['Version'] == '0.0.1a0'
    actual = [value for value in item.get_all('Requires-Dist') if 'extra ==' not in value]
    assert sorted(actual) == sorted(EXPECTED), actual


def smoke(args):
    assert sys.flags.isolated and not os.environ.get('PYTHONPATH')
    from PIL import Image
    from io import BytesIO
    import math
    import py_mermaid, py_katex, pyelk, py_skia_canvas
    from py_mermaid import render, MermaidError

    assert importlib.metadata.version('py-visactor-katex') == py_katex.__version__ == '0.1.0'
    assert importlib.metadata.version('py-skia-canvas') == '0.1.0a18'
    assert importlib.metadata.version('py-visactor-elk') == '0.1.0'
    locations = {module.__name__: str(Path(module.__file__).resolve())
                 for module in [py_mermaid, py_katex, pyelk, py_skia_canvas]}
    assert all(Path(path).is_relative_to(Path(sys.prefix).resolve()) for path in locations.values()), locations
    assert not shutil.which('node')
    required = importlib.metadata.requires('py-mermaid')
    assert 'py-visactor-katex==0.1.0' in required
    assert not any(value.lower().startswith('py-katex') for value in required)
    args.out.mkdir(parents=True, exist_ok=False)
    cases = read(ROOT / 'tests/math/published-cases.json')['cases']
    results = []
    for case in cases:
        result = render(case['text'], config=case.get('config'), backend=args.backend)
        events = [event for event in result.trace if event.kind == 'math']
        glyphs = [event for event in result.trace if event.kind == 'math-glyph']
        assert sorted(e.text for e in events) == sorted(case['maths']), case['id']
        assert [node.id for node in result.diagram.nodes] == case['nodeIds']
        assert [[edge.source, edge.target] for edge in result.diagram.edges] == case['edges']
        assert all(any(c in (e.text or '') for e in glyphs) for c in case.get('glyphs', ''))
        if case.get('literal'):
            assert case['literal'] in ''.join(e.text or '' for e in result.trace if e.kind == 'text')
        image = Image.open(BytesIO(result.data)).convert('RGB')
        painted = []
        for event in events:
            b = event.box
            assert b.x >= 0 and b.y >= 0 and b.x + b.width <= result.width + .01 and b.y + b.height <= result.height + .01
            pixels = image.crop((math.floor(b.x), math.floor(b.y), math.ceil(b.x + b.width), math.ceil(b.y + b.height)))
            ink = sum(min(pixel) < 180 for pixel in pixels.getdata())
            assert ink > 2, (case['id'], 'Missing real mathematics pixels')
            painted.append(ink)
        if args.backend == 'gpu':
            assert dict(result.backend)['renderer'] == 'GPU'
        if args.backend == 'cpu':
            assert dict(result.backend)['renderer'] == 'CPU'
        name = case['id'] + '.png'
        (args.out / name).write_bytes(result.data)
        results.append({'id': case['id'], 'file': name, 'sha256': hashlib.sha256(result.data).hexdigest(),
                        'width': result.width, 'height': result.height, 'mathPixels': painted,
                        'backend': dict(result.backend), 'status': 'PASS'})
    # Exercise all five encoders with actual node, edge and group mathematics.
    text = 'flowchart LR\nsubgraph G["Group $$g_1$$"]\nA["Node $$x^2$$"] -->|"Edge $$\\\\frac{a}{b}$$"| B["Done $$\\\\sqrt{y}$$"]\nend'
    exports = []
    for fmt, header in [('png', b'\x89PNG'), ('jpg', b'\xff\xd8'), ('webp', b'RIFF'), ('svg', b'<'), ('pdf', b'%PDF')]:
        result = render(text, backend=args.backend, format=fmt)
        assert result.data.lstrip().startswith(header)
        assert len([event for event in result.trace if event.kind == 'math']) == 4
        name = 'combined-math.' + fmt
        (args.out / name).write_bytes(result.data)
        exports.append({'file': name, 'bytes': len(result.data), 'sha256': hashlib.sha256(result.data).hexdigest()})
    try:
        render(r'flowchart TD' + '\n' + r'A["$$\DefinitelyInvalidPublishedControl$$"]', backend=args.backend)
    except MermaidError as error:
        assert error.code.startswith('MATH_')
    else:
        raise AssertionError('Malformed mathematics silently accepted')
    save(args.out / 'smoke.json', {'status': 'PASS', 'isolated': True, 'nodeAvailable': False,
         'mathDistribution': 'py-visactor-katex', 'mathVersion': '0.1.0', 'modules': locations,
         'profile': args.backend, 'cases': results, 'exports': exports})
    print(json.dumps({'status': 'PASS', 'profile': args.backend, 'cases': len(results), 'exports': len(exports)}))


def install(artifact, out, profiles):
    home = Path(tempfile.mkdtemp(prefix='py-mermaid-published-math-'))
    assert not home.resolve().is_relative_to(ROOT.parent.resolve())
    environment = home / 'venv'
    venv.EnvBuilder(with_pip=True).create(environment)
    python = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    work = home / 'work'
    work.mkdir()
    out.mkdir(parents=True, exist_ok=False)
    env = {key: value for key, value in os.environ.items() if not key.startswith('PYTHON')}
    env.update(PYTHONIOENCODING='utf-8', PYTHONUTF8='1')
    commands = []

    def run(name, argv, *, empty_path=False):
        child_env = {**env, **({'PATH': ''} if empty_path else {})}
        done = subprocess.run([str(x) for x in argv], cwd=work, env=child_env, capture_output=True, timeout=600)
        (out / (name + '.stdout.log')).write_bytes(done.stdout)
        (out / (name + '.stderr.log')).write_bytes(done.stderr)
        commands.append({'name': name, 'argv': [str(x) for x in argv], 'cwd': str(work), 'exitCode': done.returncode, 'emptyPath': empty_path})
        assert done.returncode == 0, name + ' failed; see ' + str(out)

    report = out / 'pip-install-report.json'
    run('install-with-official-dependencies', [python, '-I', '-m', 'pip', '--isolated', 'install',
        '--index-url', 'https://pypi.org/simple/', '--no-cache-dir', '--report', report, artifact.resolve()])
    lock = read(ROOT / 'references/math-release-lock.json')
    installed_math = next(item for item in read(report)['install'] if item['metadata']['name'] == 'py-visactor-katex')
    assert installed_math['metadata']['version'] == '0.1.0'
    assert installed_math['download_info']['url'].startswith('https://files.pythonhosted.org/')
    assert installed_math['download_info']['archive_info']['hashes']['sha256'] == lock['distributions']['py_visactor_katex-0.1.0-py3-none-any.whl']['sha256']
    run('install-test-only-pillow', [python, '-I', '-m', 'pip', '--isolated', 'install', '--index-url', 'https://pypi.org/simple/', '--no-cache-dir', 'Pillow==12.3.0'])
    run('dependency-consistency', [python, '-I', '-m', 'pip', 'check'])
    run('existing-math-regression', [python, '-I', '-m', 'unittest', 'discover', '-s', ROOT / 'tests/math', '-p', 'test_*.py', '-v'], empty_path=True)
    run('existing-public-api-regression', [python, '-I', '-m', 'unittest', 'discover', '-s', ROOT / 'tests/f011', '-p', 'test_api.py', '-v'], empty_path=True)
    for profile in profiles:
        run('installed-math-' + profile, [python, '-I', Path(__file__).resolve(), '--installed-smoke',
            '--backend', profile, '--out', out / ('smoke-' + profile)], empty_path=True)
    result = {'status': 'PASS', 'artifact': artifact.name, 'sha256': hashlib.sha256(artifact.read_bytes()).hexdigest(),
              'environment': str(environment), 'mathDownload': installed_math['download_info'], 'commands': commands}
    save(out / 'installation.json', result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--wheel', type=Path)
    p.add_argument('--sdist', type=Path)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--backend', choices=['cpu', 'auto', 'gpu'], action='append')
    p.add_argument('--installed-smoke', action='store_true')
    args = p.parse_args()
    args.out = args.out.resolve()
    if args.installed_smoke:
        args.backend = (args.backend or ['cpu'])[0]
        smoke(args)
        return
    assert args.wheel and args.sdist
    with zipfile.ZipFile(args.wheel) as archive:
        metadata(archive.read('py_mermaid-0.0.1a0.dist-info/METADATA'))
        assert not any(name.startswith('py_katex/') for name in archive.namelist())
    with tarfile.open(args.sdist, 'r:gz') as archive:
        item = next(member for member in archive.getmembers() if member.name.count('/') == 1 and member.name.endswith('/PKG-INFO'))
        metadata(archive.extractfile(item).read())
    args.out.mkdir(parents=True, exist_ok=False)
    installations = [install(artifact, args.out / mode, args.backend or ['cpu', 'auto', 'gpu'])
                     for mode, artifact in [('wheel', args.wheel), ('sdist', args.sdist)]]
    save(args.out / 'validation.json', {'status': 'PASS', 'mathDependency': 'py-visactor-katex==0.1.0',
         'profiles': args.backend or ['cpu', 'auto', 'gpu'], 'casesPerProfile': 8, 'exportsPerProfile': 5,
         'installations': installations})
    print(json.dumps({'status': 'PASS', 'installations': len(installations), 'mathDependency': 'py-visactor-katex==0.1.0'}))


if __name__ == '__main__':
    main()
