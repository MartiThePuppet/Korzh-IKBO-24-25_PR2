from __future__ import annotations

import argparse
import sys

from .config import Config
from .repository import AptRepository

STAGES = ("config", "data",)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Вариант 12: граф зависимостей APT"
    )
    parser.add_argument("--config", default="config.csv")
    parser.add_argument("--stage", choices=STAGES, default="data")
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


def _load_packages(config: Config) -> dict[str, list[str]]:
    packages = AptRepository(config.repository).load()
    if config.package not in packages:
        raise ValueError(f"Пакет не найден: {config.package}")
    return packages


def _show_data(packages: dict[str, list[str]], package: str) -> None:
    print("Прямые зависимости:")
    print("\n".join(packages[package]) or "(нет)")


def _run(args: argparse.Namespace) -> None:
    config = Config.from_csv(args.config)
    if args.stage == "config":
        _show_config(config)
        return
    packages = _load_packages(config)
    if args.stage == "data":
        _show_data(packages, config.package)
        return


def main(argv: list[str] | None = None) -> int:
    try:
        _run(_parser().parse_args(argv))
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
