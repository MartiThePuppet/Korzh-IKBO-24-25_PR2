from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

CSV_COLUMNS = 2
REQUIRED_KEYS = {"package", "repository", "test_mode", "output"}
TRUE_VALUES = {"true", "да", "1"}
FALSE_VALUES = {"false", "нет", "0"}


class ConfigError(ValueError):
    """Invalid CLI configuration."""


def _read_values(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise ConfigError(f"Конфигурационный файл не найден: {path}")
    values: dict[str, str] = {}
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.reader(stream, strict=True):
                _add_row(values, row)
    except UnicodeDecodeError as exc:
        raise ConfigError("Конфигурация должна быть в UTF-8") from exc
    except csv.Error as exc:
        raise ConfigError(f"Некорректный CSV: {exc}") from exc
    return values


def _add_row(values: dict[str, str], row: list[str]) -> None:
    if all(not cell.strip() for cell in row):
        return
    if len(row) != CSV_COLUMNS:
        raise ConfigError("Каждая строка CSV должна иметь вид key,value")
    key, value = (cell.strip() for cell in row)
    if key.lower() in {"key", "параметр"}:
        return
    if not key:
        raise ConfigError("Имя параметра не может быть пустым")
    if key in values:
        raise ConfigError(f"Параметр указан повторно: {key}")
    values[key] = value


def _validate_keys(values: dict[str, str]) -> None:
    missing = REQUIRED_KEYS - values.keys()
    unknown = values.keys() - REQUIRED_KEYS - {"filter"}
    if missing:
        names = ", ".join(sorted(missing))
        raise ConfigError(f"Отсутствуют параметры: {names}")
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ConfigError(f"Неизвестные параметры: {names}")


def _parse_mode(value: str) -> bool:
    mode = value.lower()
    if mode not in TRUE_VALUES | FALSE_VALUES:
        raise ConfigError("test_mode должен быть true/false")
    return mode in TRUE_VALUES


def _resolve_path(value: str, config_path: str | Path) -> Path:
    path = Path(value).expanduser()
    return (Path(config_path).resolve().parent / path).resolve()


def _validate_repository(value: str, path: Path, test_mode: bool) -> None:
    if not value:
        raise ConfigError("Репозиторий не может быть пустым")
    if test_mode:
        local = _resolve_path(value, path)
        if not local.is_file():
            raise ConfigError(f"Файл тестового репозитория не найден: {local}")
        return
    url = urlparse(value)
    if url.scheme not in {"http", "https"} or not url.hostname:
        raise ConfigError("repository должен быть HTTP(S) URL индекса Packages")


def _validate_fields(values: dict[str, str], test_mode: bool) -> None:
    pattern = r"[A-Z]+" if test_mode else r"[a-z0-9][a-z0-9+.-]*"
    if not re.fullmatch(pattern, values["package"]):
        raise ConfigError("Недопустимое имя пакета для выбранного режима")
    if Path(values["output"]).suffix.lower() != ".png":
        raise ConfigError("output должен указывать на файл .png")
    if any(char in values.get("filter", "") for char in "\n\r\x00"):
        raise ConfigError("filter не должен содержать управляющие символы")


@dataclass(frozen=True)
class Config:
    """Validated parameters loaded from a CSV file."""

    package: str
    repository: str
    test_mode: bool
    output: str
    package_filter: str = ""

    @classmethod
    def from_csv(cls, path: str | Path) -> Config:
        config_path = Path(path).resolve()
        values = _read_values(config_path)
        _validate_keys(values)
        test_mode = _parse_mode(values["test_mode"])
        _validate_fields(values, test_mode)
        _validate_repository(values["repository"], config_path, test_mode)
        return cls(
            package=values["package"],
            repository=values["repository"],
            test_mode=test_mode,
            output=values["output"],
            package_filter=values.get("filter", ""),
        )

    def resolved_repository(self, config_path: str | Path) -> Path:
        return _resolve_path(self.repository, config_path)

    def resolved_output(self, config_path: str | Path) -> Path:
        return _resolve_path(self.output, config_path)
