from __future__ import annotations

import argparse
import sys

from .config import Config

STAGES = ("config",)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Вариант 12: граф зависимостей APT"
    )
    parser.add_argument("--config", default="config.csv")
    parser.add_argument("--stage", choices=STAGES, default="config")
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


def _run(args: argparse.Namespace) -> None:
    config = Config.from_csv(args.config)
    if args.stage == "config":
        _show_config(config)
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
