import argparse
import sys
from pathlib import Path

from .config import Config
from .graph import build_graph, reverse_dependencies
from .render import mermaid, save_png
from .repository import AptRepository


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Вариант 12: граф зависимостей APT")
    parser.add_argument("--config", default="config.csv")
    parser.add_argument("--stage", default="all", choices=[
        "config", "data", "graph", "reverse", "visualize", "all",
    ])
    parser.add_argument("--offline", action="store_true",
                        help="Не отправлять граф сервису Kroki; требуется mmdc")
    args = parser.parse_args(argv)
    try:
        config = Config.from_csv(args.config)
        if args.stage == "config":
            for key, value in [
                ("package", config.package), ("repository", config.repository),
                ("test_mode", str(config.test_mode).lower()),
                ("output", config.output), ("filter", config.package_filter),
            ]:
                print(f"{key}={value}")
            return 0
        source = (config.resolved_repository(args.config) if config.test_mode
                  else config.repository)
        packages = AptRepository(source, config.test_mode).load()
        if config.package not in packages:
            raise ValueError(f"Пакет не найден: {config.package}")
        if args.stage == "data":
            print("Прямые зависимости:")
            print("\n".join(packages[config.package]) or "(нет)")
            return 0
        if args.stage == "reverse":
            graph = reverse_dependencies(packages, config.package,
                                         config.package_filter)
            print("Обратные зависимости (прямые и транзитивные):")
            print("\n".join(n for n in graph.edges if n != config.package) or "(нет)")
            return 0
        graph = build_graph(packages, config.package, config.package_filter)
        for name, dependencies in graph.edges.items():
            print(f"{name}: {', '.join(dependencies) or '(нет)'}")
        if graph.cycles:
            print("Циклические ребра:", graph.cycles)
        if graph.missing:
            print("Нет метаданных для:", ", ".join(sorted(graph.missing)))
        if args.stage in {"visualize", "all"}:
            output = config.resolved_output(args.config)
            save_png(mermaid(graph, config.package), output, args.offline)
            print(f"Mermaid: {output.with_suffix('.mmd')}")
            print(f"PNG: {output}")
        return 0
    except (OSError, ValueError, RuntimeError, RecursionError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
