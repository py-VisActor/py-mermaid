"""Snapshot the public VChart registry for a design, without compiling new DSL."""
import argparse
import importlib.metadata
import json
from pathlib import Path

from py_vchart import VChart
from run_support import ROOT, Run, file_identity, write_json


GROUPS = {
    'cartesian_and_common': 'bar line scatter area rangeArea rangeColumn waterfall histogram boxPlot heatmap mosaic linearProgress common'.split(),
    'polar_and_indicator': 'pie rose radar gauge circularProgress liquid'.split(),
    'hierarchy_and_relation': 'funnel treemap sunburst circlePacking sankey correlation venn'.split(),
    'extension_2d': 'storyline sequenceAnalysis sequence combinationCandlestick pictogram imageCloud candlestick conversionFunnel rankingList rankingBar timeline sequenceScatterPixel sequenceScatterKDE sequenceScatterLink'.split(),
    'map_and_wordcloud': ['map', 'wordCloud'],
}


def shape(value):
    if isinstance(value, dict):
        return 'object_with_values' if 'values' in value else 'object'
    if isinstance(value, list):
        return 'array_of_data_views' if value and all(isinstance(v, dict) and 'values' in v for v in value) else 'raw_array'
    return type(value).__name__


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('Design snapshot output must be new')
    with Run('VCHART-DSL-DESIGN', 'inventory') as run:
        fixture = ROOT / 'tests/vchart_integration/cases-vchart.json'
        run.input(fixture)
        registered = tuple(VChart.supported_types())
        cases = json.loads(fixture.read_text('utf-8'))['cases']
        assert len(registered) == len(set(registered)) == len(cases) == 68
        assert {c['type'] for c in cases} == set(registered)
        group_members = [name for names in GROUPS.values() for name in names]
        assert len(group_members) == len(set(group_members))
        groups = dict(GROUPS)
        groups['statistical_unique_names'] = [t for t in registered if t not in group_members]
        assert len(groups['statistical_unique_names']) == 26
        supplier = ROOT.parent / 'py-vchart'
        inputs = sorted((supplier / 'tests/cases').rglob('spec.json'))
        assert len(inputs) == 225
        source_paths = [supplier / 'src/py_vchart' / name for name in (
            'core/__init__.py', 'chart/common.py', 'chart/cartesian.py', 'chart/statplots.py',
            'chart/plot.py', 'chart/map.py', 'chart/venn.py', 'chart/hierarchy.py')]
        source_paths += [ROOT / name for name in (
            'src/py_mermaid/vchart_bridge.py', 'src/py_mermaid/model/vchart.py',
            'src/py_mermaid/diagrams/charts/vchart.py', 'src/py_mermaid/runtime/registry.py')]
        identities = {str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else '../py-vchart/' + p.relative_to(supplier).as_posix():
                      file_identity(p) for p in source_paths}
        by_type = {row['type']: row for row in cases}
        result = {
            'schema': 'py-mermaid-vchart-dsl-design/v1', 'status': 'DESIGN_ONLY_NOT_IMPLEMENTED',
            'design': 'docs/VCHART_DSL_DESIGN.md', 'plan': 'docs/VCHART_DSL_EXECUTION_PLAN.md',
            'grammar': 'docs/syntax/vchart-v1.ebnf',
            'provider': {'distribution': 'py-visactor-vchart', 'version': importlib.metadata.version('py-visactor-vchart'),
                         'requiredVersion': '0.1.1', 'publicRegistry': 'VChart.supported_types'},
            'registeredTypeCount': len(registered), 'groups': groups,
            'types': [{'name': name, 'representativeFixture': by_type[name]['id'],
                       'representativeDataShape': shape(by_type[name]['spec'].get('data')),
                       'representativeTopLevelKeys': sorted(by_type[name]['spec']),
                       'resourceNames': {'maps': sorted(by_type[name]['maps']), 'svgs': sorted(by_type[name]['svgs'])},
                       'origin': {key: value for key, value in by_type[name]['origin'].items()
                                  if key in ('casePath', 'specSha256', 'pngSha256', 'captureSha256')},
                       'optionAudit': 'REQUIRES_SOURCE_BASED_FIELD_AND_CONDITIONAL_AUDIT'} for name in registered],
            'observedSupplierInputs': {p.relative_to(supplier).as_posix(): file_identity(p) for p in inputs},
            'sourceEvidence': identities, 'fixture': file_identity(fixture), 'run': str(run.path),
            'coverageMeaning': '68 names and225 existing specs are inventoried; no new DSL parser, lowering, option completeness, render or installation acceptance is claimed.'}
        assert result['provider']['version'] == result['provider']['requiredVersion']
        write_json(run.path / 'artifacts/catalogue.json', result, exclusive=True)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        write_json(args.out, result, exclusive=True)
        run.data['functionalStatus'] = 'DESIGN_INVENTORY_ONLY'
        run.data['result'] = {'catalogue': str(args.out), 'types': len(registered), 'existingSpecs': len(inputs)}
        run.save()
    print(json.dumps({'run': str(run.path), 'status': run.data['status'], **run.data['result']}))


if __name__ == '__main__':
    main()
