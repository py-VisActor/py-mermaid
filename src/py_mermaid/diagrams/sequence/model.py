"""Immutable sequence semantics, in source declaration/event order."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Actor:
    id: str
    label: str
    kind: str = 'participant'
    wrap: bool = False
    box: int | None = None
    created: int | None = None
    destroyed: int | None = None
    metadata: tuple = ()


@dataclass(frozen=True)
class Event:
    kind: str
    source: str = ''
    target: str = ''
    text: str = ''
    arrow: str = ''
    wrap: bool = False
    placement: str = ''
    connection: str = ''
    number: float | None = None
    offset: int = 0


@dataclass(frozen=True)
class ActorBox:
    title: str
    color: str
    actors: tuple[str, ...]
    wrap: bool = False


@dataclass(frozen=True)
class Sequence:
    actors: tuple[Actor, ...]
    events: tuple[Event, ...]
    boxes: tuple[ActorBox, ...] = ()
    title: str = ''
    metadata: tuple = ()

