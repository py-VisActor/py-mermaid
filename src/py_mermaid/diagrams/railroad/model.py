"""Four grammar frontends share the source Railroad AST, not a graph model."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Expression:
    kind: str
    text: str = ''
    children: tuple['Expression', ...] = ()
    minimum: int = 0
    maximum: int | None = None


@dataclass(frozen=True)
class Rule:
    name: str
    definition: Expression


@dataclass(frozen=True)
class Railroad:
    rules: tuple[Rule, ...]
    title: str = ''
    dialect: str = 'railroad'

