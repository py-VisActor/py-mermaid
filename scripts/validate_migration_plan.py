"""Validate handoff scope/task barriers only; never run product or tests."""
from __future__ import annotations

import argparse
from collections import Counter
import graphlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check(root: Path = ROOT, plan_override: dict | None = None) -> dict:
    plan = plan_override if plan_override is not None else json.loads(
        (root / 'references/migration-execution.json').read_text('utf-8'))
    features = json.loads((root / 'references/feature-modules.json').read_text('utf-8'))
    compatibility = json.loads((root / 'docs/compatibility.json').read_text('utf-8'))
    lock = json.loads((root / 'references/upstream.lock.json').read_text('utf-8'))
    errors = []
    phases = ['P0', 'P1', 'P2', 'P3', 'P4', 'P5']
    if plan.get('schema') != 'py-mermaid-migration-execution/v1' or plan.get('phaseOrder') != phases:
        errors.append('Invalid execution schema or phase order')
    if not (plan.get('upstreamCommit') == features['upstreamCommit'] == compatibility['upstreamCommit'] == lock['commit']):
        errors.append('Execution plan source commit differs')
    expected_strategy = {'sourceFirstAllFeatures': True, 'formalTestDesignPhase': 'P2',
                         'firstProductTestExecutionPhase': 'P3', 'finalFullValidationPhase': 'P4'}
    if any(plan.get('strategy', {}).get(k) != v for k, v in expected_strategy.items()):
        errors.append('Source-first/test-design/triage/final-validation strategy differs')
    if plan.get('architecture') != 'canvas-native-no-dom':
        errors.append('Canvas-native architecture differs')
    slots = plan.get('parallelism', {})
    if slots.get('defaultSlots') != slots.get('coordinators', 0) + slots.get('workers', 0):
        errors.append('Parallel slot budget differs')
    tasks = plan.get('tasks', [])
    ids = [task['id'] for task in tasks]
    if not ids or len(ids) != len(set(ids)):
        errors.append('Empty or duplicate task IDs')
    by_id = {task['id']: task for task in tasks}
    graph = {}
    for task in tasks:
        tid = task['id']
        if task['phase'] not in phases:
            errors.append('Unknown phase: ' + tid)
        if task.get('status') not in plan.get('stateVocabulary', []):
            errors.append('Unknown task status: ' + tid)
        if not task.get('ownerRole') or not task.get('exitRule'):
            errors.append('Missing role/exit rule: ' + tid)
        deps = task.get('dependsOn', [])
        needs = task.get('integrationNeeds', [])
        graph[tid] = set(deps + needs)
        for dep in graph[tid]:
            if dep not in by_id:
                errors.append(f'Unknown task dependency: {tid} -> {dep}')
            elif task['phase'] in phases and by_id[dep]['phase'] in phases and phases.index(by_id[dep]['phase']) > phases.index(task['phase']):
                errors.append(f'Later phase prerequisite: {tid} -> {dep}')
        for name in task.get('writePaths', []):
            if name.startswith(('/', '\\')) or ':' in name or '..' in name.split('/'):
                errors.append('Unsafe planned write path: ' + tid)
    try:
        list(graphlib.TopologicalSorter(graph).static_order())
    except graphlib.CycleError:
        errors.append('Cyclic task start/integration dependencies')

    def ancestors(tid):
        visited = set()
        pending = list(by_id.get(tid, {}).get('dependsOn', []))
        while pending:
            dep = pending.pop()
            if dep in visited:
                continue
            visited.add(dep)
            pending.extend(by_id.get(dep, {}).get('dependsOn', []))
        return visited

    source_tasks = {t['id'] for t in tasks if t['phase'] == 'P1' and t['kind'] == 'work'}
    if not source_tasks <= ancestors('P1-GATE'):
        errors.append('P1 gate omits source tasks')
    barriers = {'P2': 'P1-GATE', 'P3': 'P2-GATE', 'P4': 'P3-GATE', 'P5': 'P4-GATE'}
    for task in tasks:
        if task['phase'] in barriers and barriers[task['phase']] not in ancestors(task['id']):
            errors.append('Missing stage barrier: ' + task['id'])
    for phase in phases[:-1]:
        gate = phase + '-GATE'
        phase_work = {t['id'] for t in tasks if t['phase'] == phase and t['kind'] == 'work'}
        if gate not in by_id or not phase_work <= ancestors(gate):
            errors.append('Phase gate omits work: ' + phase)
    coverage = plan.get('featureTaskCoverage', {})
    actual = Counter(d for item in coverage.values() for d in item['detectors'])
    if actual != Counter(d['id'] for d in compatibility['diagrams']):
        errors.append('Detector task coverage differs')
    if set(coverage) != {f['id'] for f in features['features']}:
        errors.append('Feature family coverage differs')
    for fid, item in coverage.items():
        task = by_id.get(item['sourceTask'], {})
        if task.get('phase') != 'P1' or fid not in task.get('featureIds', []):
            errors.append('Feature missing P1 source owner: ' + fid)
    expected_cross = {c['id'] for c in compatibility['crossCutting']}
    cross_owners = plan.get('crossCuttingOwners', {})
    modules = {m['id'] for m in features['sharedModules']}
    if set(cross_owners) != expected_cross or not set(cross_owners.values()) <= modules:
        errors.append('Cross-cutting owners differ')
    assigned_modules = {m for t in tasks if t['phase'] == 'P1' for m in t.get('sharedModules', [])}
    if assigned_modules != modules:
        errors.append('Shared module source coverage differs')
    for name in plan.get('documents', []):
        if not (root / name).is_file():
            errors.append('Missing execution document: ' + name)
    task_doc = (root / 'docs/TASKS.md').read_text('utf-8')
    for tid in ids:
        if f'| {tid} |' not in task_doc:
            errors.append('Missing task index row: ' + tid)
    if by_id.get('P5-02', {}).get('requiresExplicitAuthorization') is not True:
        errors.append('External publishing authorization boundary missing')
    template_path = root / 'references/execution-state.template.json'
    if not template_path.is_file():
        errors.append('Missing execution-state template')
    else:
        template = json.loads(template_path.read_text('utf-8'))
        if template.get('template') is not True or set(template.get('tasks', {})) != set(ids):
            errors.append('Execution-state template task coverage differs')
        if set(template.get('detectors', {})) != {d['id'] for d in compatibility['diagrams']}:
            errors.append('Execution-state template detector coverage differs')
        if set(template.get('crossCutting', {})) != expected_cross or set(template.get('sharedModules', {})) != modules:
            errors.append('Execution-state template shared scope differs')
        if any(row.get('status') != 'planned' or row.get('ownerAgent') is not None
               for row in template.get('tasks', {}).values()):
            errors.append('Template falsely contains execution progress')
        for mid, row in template.get('sharedModules', {}).items():
            expected = {t['id'] for t in tasks if t['phase'] == 'P1' and mid in t.get('sharedModules', [])}
            if set(row.get('sourceTasks', [])) != expected:
                errors.append('Template shared-module providers differ: ' + mid)
        if 'C01' not in by_id.get('P1-03', {}).get('sharedModules', []):
            errors.append('Preprocessing/position diagnostics owner C01 missing from P1-03')
    execution = features.get('executionStrategy', {})
    if execution.get('phaseOrder') != phases or execution.get('formalTestDesignPhase') != 'P2':
        errors.append('Feature plan execution order differs')
    render_policy = plan.get('renderValidationPolicy')
    if render_policy != 'references/render-validation-policy.json' or not (root / render_policy).is_file():
        errors.append('Missing functional render-validation policy')
    else:
        render = json.loads((root / render_policy).read_text('utf-8'))
        cross = render.get('crossEngine', {})
        expected = {'functionalParityRequired': True, 'renderedContentAndRelationshipsRequired': True,
                    'geometryQualityRequired': True, 'pixelEqualityRequired': False,
                    'absoluteCoordinateEqualityRequired': False, 'naturalDimensionEqualityRequired': False,
                    'explicitDimensionContractRequired': True,
                    'imageMetricsRole': 'diagnostic-and-review-routing-only'}
        if any(cross.get(k) != v for k, v in expected.items()):
            errors.append('Functional render-parity acceptance differs')
        gates = {layer['id']: layer['gate'] for layer in render.get('layers', [])}
        if gates != {'L1': True, 'L2': True, 'L3': True, 'L4': False}:
            errors.append('Render functional/quality/diagnostic layers differ')
        if render.get('phaseOrder') != phases or render.get('comparatorsToBuildIn') != 'P2':
            errors.append('Render verification stage order differs')
        if features.get('renderValidationPolicy') != render_policy:
            errors.append('Feature render-policy link differs')
        pixel = render.get('pixelTool', {})
        if pixel.get('defaultMode') != 'diagnostic' or pixel.get('functionalStatus') != 'NOT_EVALUATED':
            errors.append('Pixel utility functional/diagnostic boundary differs')
        for field in ('path', 'documentation', 'requirements'):
            if not pixel.get(field) or not (root / pixel[field]).is_file():
                errors.append('Missing pixel utility artifact: ' + field)
    return {'status': 'MIGRATION_PLAN_VALIDATED' if not errors else 'INCOMPLETE',
            'errors': errors, 'tasks': len(tasks), 'phaseCounts': dict(Counter(t['phase'] for t in tasks)),
            'featureFamilies': len(coverage), 'detectors': sum(actual.values()),
            'crossCutting': len(cross_owners),
            'initialReadyTasks': [t['id'] for t in tasks if not t.get('dependsOn')],
            'productExecutions': 0,
            'limitation': 'Scope, task references and phase barriers only; no product implementation or functional acceptance.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', required=True)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    result = check()
    payload = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open('x', encoding='utf-8') as stream:
            stream.write(payload)
    print(payload, end='')
    raise SystemExit(bool(result['errors']))


if __name__ == '__main__':
    main()
