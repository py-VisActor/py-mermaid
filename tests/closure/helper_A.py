"""Independent literal data bindings, with no behavior during discovery."""
from dataclasses import asdict,is_dataclass
import json
from pathlib import Path

CASES=json.loads(Path(__file__).with_name('cases-A.json').read_text(encoding='utf8'))['cases']


def plain(value):
    if is_dataclass(value):return {key:plain(item) for key,item in asdict(value).items()}
    if isinstance(value,dict):return {key:plain(item) for key,item in value.items()}
    if isinstance(value,(tuple,list)):return [plain(item) for item in value]
    return value


def select(value,path):
    for key in path:value=value[key]
    return value


def parse_case(case):
    from py_mermaid.runtime.registry import parse_diagram
    return parse_diagram(case['source'],config=case['config'])


