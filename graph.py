from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Graph:
    edges: dict[str, list[str]] = field(default_factory=dict)
    cycles: list[tuple[str, str]] = field(default_factory=list)
    missing: set[str] = field(default_factory=set)


def build_graph(packages: dict[str, list[str]], root: str,
                excluded: str = "") -> Graph:
    """Traverse reachable dependencies using recursive DFS and three colors."""
    if root not in packages:
        raise ValueError(f"Пакет не найден: {root}")
    graph = Graph()
    colors: dict[str, int] = {}

    def visit(name: str) -> None:
        if excluded and excluded in name:
            return
        colors[name] = 1
        graph.edges[name] = []
        if name not in packages:
            graph.missing.add(name)
        for dependency in packages.get(name, []):
            if excluded and excluded in dependency:
                continue
            if dependency not in graph.edges[name]:
                graph.edges[name].append(dependency)
            if colors.get(dependency) == 1:
                graph.cycles.append((name, dependency))
            elif not colors.get(dependency):
                visit(dependency)
        colors[name] = 2

    visit(root)
    return graph


def reverse_dependencies(packages: dict[str, list[str]], root: str,
                         excluded: str = "") -> Graph:
    """Apply the same DFS to reversed edges of the complete repository."""
    reversed_edges: dict[str, list[str]] = {name: [] for name in packages}
    for name, dependencies in packages.items():
        for dependency in dependencies:
            reversed_edges.setdefault(dependency, []).append(name)
    return build_graph(reversed_edges, root, excluded)
