"""Source grammar/DB parameters: class/state/ER/requirement/usecase/C4."""
from .support import SourceCase,install_cases
class ModelingSourceTests(SourceCase):
    pass
_cases={};install_cases(_cases,('classDiagram','stateDiagram','er','requirement','usecase','c4'))
for _name,_method in _cases.items():setattr(ModelingSourceTests,_name,_method)
