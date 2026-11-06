"""ZenUML-specific immutable syntax tree (nested call scopes, not flow edges)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Participant:
    id: str
    label: str = ''
    type: str = ''
    stereotype: str = ''
    emoji: str = ''
    color: str = ''
    group: str = ''
    width: float | None = None
    explicit: bool = False
    starter: bool = False


@dataclass(frozen=True)
class Statement:
    kind: str
    label: str = ''
    source: str = ''
    target: str = ''
    children: tuple['Statement', ...] = ()
    sections: tuple[tuple[str,tuple['Statement', ...]], ...] = ()
    assignment: str = ''
    comment: str = ''
    offset: int = 0
    participants: tuple[str, ...] = ()
    assignee: str = ''
    return_explicit: bool = False
    source_text: str = ''


@dataclass(frozen=True)
class ZenUML:
    participants: tuple[Participant, ...]
    statements: tuple[Statement, ...]
    title: str = ''
    starter: str = '_STARTER_'

