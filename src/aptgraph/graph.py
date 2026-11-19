from __future__ import annotations

from dataclasses import dataclass, field

VISITING = 1
VISITED = 2


@dataclass
class Graph:
    edges: dict[str, list[str]] = field(default_factory=dict)
    cycles: list[tuple[str, str]] = field(default_factory=list)
    missing: set[str] = field(default_factory=set)


def _is_excluded(name: str, excluded: str) -> bool:
    return bool(excluded and excluded in name)


def _visit(
    name: str,
    packages: dict[str, list[str]],
    excluded: str,
    colors: dict[str, int],
    graph: Graph,
) -> None:
    colors[name] = VISITING
    graph.edges[name] = []
    if name not in packages:
        graph.missing.add(name)
    for dependency in dict.fromkeys(packages.get(name, [])):
        if _is_excluded(dependency, excluded):
            continue
        graph.edges[name].append(dependency)
        state = colors.get(dependency, 0)
        if state == VISITING:
            graph.cycles.append((name, dependency))
        elif state != VISITED:
            _visit(dependency, packages, excluded, colors, graph)
    colors[name] = VISITED


def build_graph(
    packages: dict[str, list[str]], root: str, excluded: str = ""
) -> Graph:
    """Build a reachable dependency graph with recursive DFS."""
    if root not in packages:
        raise ValueError(f"Пакет не найден: {root}")
    graph = Graph()
    if not _is_excluded(root, excluded):
        _visit(root, packages, excluded, {}, graph)
    return graph
