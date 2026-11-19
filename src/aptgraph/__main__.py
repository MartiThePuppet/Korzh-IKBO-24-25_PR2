from __future__ import annotations

import argparse
import sys
from subprocess import SubprocessError

from .config import Config
from .graph import Graph, build_graph, reverse_dependencies
from .render import mermaid, save_png
from .repository import AptRepository

STAGES = ("config", "data", "graph", "reverse", "visualize", "all")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Вариант 12: граф зависимостей APT"
    )
    parser.add_argument("--config", default="config.csv")
    parser.add_argument("--stage", choices=STAGES, default="all")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Не отправлять граф Kroki, требуется mmdc",
    )
    return parser


def _show_config(config: Config) -> None:
    values = {
        "package": config.package,
        "repository": config.repository,
        "test_mode": str(config.test_mode).lower(),
        "output": config.output,
        "filter": config.package_filter,
    }
    for key, value in values.items():
        print(f"{key}={value}")


def _load_packages(config: Config, config_path: str) -> dict[str, list[str]]:
    source = config.repository
    if config.test_mode:
        source = str(config.resolved_repository(config_path))
    packages = AptRepository(source, config.test_mode).load()
    if config.package not in packages:
        raise ValueError(f"Пакет не найден: {config.package}")
    return packages


def _show_data(packages: dict[str, list[str]], package: str) -> None:
    print("Прямые зависимости:")
    print("\n".join(packages[package]) or "(нет)")


def _show_reverse(packages: dict[str, list[str]], config: Config) -> None:
    graph = reverse_dependencies(
        packages, config.package, config.package_filter
    )
    names = (name for name in graph.edges if name != config.package)
    print("Обратные зависимости (прямые и транзитивные):")
    print("\n".join(names) or "(нет)")


def _show_graph(packages: dict[str, list[str]], config: Config) -> Graph:
    graph = build_graph(packages, config.package, config.package_filter)
    for name, dependencies in graph.edges.items():
        print(f"{name}: {', '.join(dependencies) or '(нет)'}")
    if graph.cycles:
        print("Циклические ребра:", graph.cycles)
    if graph.missing:
        print("Нет метаданных для:", ", ".join(sorted(graph.missing)))
    return graph


def _show_visualization(
    graph: Graph, config: Config, config_path: str, offline: bool
) -> None:
    output = config.resolved_output(config_path)
    save_png(mermaid(graph, config.package), output, offline)
    print(f"Mermaid: {output.with_suffix('.mmd')}")
    print(f"PNG: {output}")


def _run(args: argparse.Namespace) -> None:
    config = Config.from_csv(args.config)
    if args.stage == "config":
        _show_config(config)
        return
    packages = _load_packages(config, args.config)
    if args.stage == "data":
        _show_data(packages, config.package)
        return
    if args.stage == "reverse":
        _show_reverse(packages, config)
        return
    graph = _show_graph(packages, config)
    if args.stage in {"visualize", "all"}:
        _show_visualization(graph, config, args.config, args.offline)


def main(argv: list[str] | None = None) -> int:
    try:
        _run(_parser().parse_args(argv))
    except (OSError, ValueError, RuntimeError, SubprocessError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
