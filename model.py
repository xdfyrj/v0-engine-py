# fixtures dataclass

from dataclasses import dataclass

@dataclass(frozen=True)
class Call:
    target: str
    count: int

@dataclass(frozen=True)
class Node:
    id: str
    type: str      # "user" or "anchor"
    scored: bool
    calls: list[Call]

@dataclass(frozen=True)
class Case:
    case: str
    build: str
    schema_version: int
    nodes: list[Node]