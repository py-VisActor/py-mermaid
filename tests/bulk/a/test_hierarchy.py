"""Independent mindmap/tree-view source grammar and DB assertions."""
from .support import SourceCase,install_cases
class HierarchySourceTests(SourceCase):
    pass
_cases={};install_cases(_cases,('mindmap','treeView'))
for _name,_method in _cases.items():setattr(HierarchySourceTests,_name,_method)
