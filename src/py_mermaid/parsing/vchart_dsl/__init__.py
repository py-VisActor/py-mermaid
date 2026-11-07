"""Pure VChart DSL syntax. No renderer, native device or external resource I/O."""
from .parser import parse_dsl

__all__ = ['parse_dsl']
