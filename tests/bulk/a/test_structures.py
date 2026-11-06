"""Independent source block/packet/kanban/architecture grammar assertions."""
from .support import SourceCase,install_cases
class StructuresSourceTests(SourceCase):
    pass
_cases={};install_cases(_cases,('block','packet','kanban','architecture'))
for _name,_method in _cases.items():setattr(StructuresSourceTests,_name,_method)
