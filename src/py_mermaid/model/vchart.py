"""Immutable host values for the explicit VChart JSON extension.

Dispatch/dimensions follow py_vchart.core.VChart, not Mermaid's chart grammars.
JSON text distinguishes empty arrays/objects and never retains caller mappings.
"""
from dataclasses import asdict,dataclass
import json
from .vchart_dsl import SpecSpan,DslDiagnostic


@dataclass(frozen=True)
class VChartModel:
    spec_json: str
    width: int
    height: int
    inline_maps_json: str = '{}'
    inline_svgs: tuple[tuple[str,str], ...] = ()
    source_map: tuple[SpecSpan, ...] = ()
    diagnostics: tuple[DslDiagnostic, ...] = ()
    syntax: str = 'json'

    def spec(self):
        return json.loads(self.spec_json)


@dataclass(frozen=True)
class VChartCompilation:
    """Pure inspectable compilation; resources are explicit isolated snapshots."""
    model: VChartModel
    maps_json: str = '{}'
    svgs: tuple[tuple[str,str], ...] = ()
    source_text: str = ''

    def spec(self):return self.model.spec()
    def maps(self):return json.loads(self.maps_json)
    def svg_sources(self):return dict(self.svgs)
    @property
    def source_map(self):return self.model.source_map
    @property
    def diagnostics(self):return self.model.diagnostics
    @property
    def syntax(self):return self.model.syntax
    @property
    def width(self):return self.model.width
    @property
    def height(self):return self.model.height

    def as_dict(self):
        return {'schema':'py-mermaid-vchart-compilation/v1','syntax':self.syntax,
            'spec':self.spec(),'maps':self.maps(),'svgs':self.svg_sources(),
            'width':self.width,'height':self.height,'source':self.source_text,
            'sourceMapEncoding':'python-code-point','source_map':[asdict(v) for v in self.source_map],
            'diagnostics':[asdict(v) for v in self.diagnostics],
            'validation':'syntax, lowering, basic size/type/budgets and explicit resource safety only; provider option validation occurs at rendering'}


@dataclass(frozen=True)
class VChartScene:
    model: VChartModel
    maps_json: str = "{}"
    svgs: tuple[tuple[str, str], ...] = ()

