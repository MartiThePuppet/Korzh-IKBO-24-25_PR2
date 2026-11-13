from __future__ import annotations

import csv
import re
from urllib.parse import urlparse
from dataclasses import dataclass
from pathlib import Path


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    package: str
    repository: str
    test_mode: bool
    output: str
    package_filter: str = ""

    @classmethod
    def from_csv(cls, path: str | Path) -> "Config":
        config_path = Path(path).resolve()
        if not config_path.is_file():
            raise ConfigError(f"Конфигурационный файл не найден: {path}")
        values: dict[str, str] = {}
        try:
            with config_path.open("r", encoding="utf-8-sig", newline="") as stream:
                for row in csv.reader(stream):
                    if not row or all(not cell.strip() for cell in row):
                        continue
                    if len(row) != 2:
                        raise ConfigError("Каждая строка CSV должна иметь вид key,value")
                    key, value = (cell.strip() for cell in row)
                    if key.lower() in {"key", "параметр"}:
                        continue
                    if not key:
                        raise ConfigError("Имя параметра не может быть пустым")
                    if key in values:
                        raise ConfigError(f"Параметр указан повторно: {key}")
                    values[key] = value
        except UnicodeDecodeError as exc:
            raise ConfigError("Конфигурация должна быть в UTF-8") from exc

        required = {"package", "repository", "test_mode", "output"}
        missing = required - values.keys()
        unknown = set(values) - required - {"filter"}
        if missing:
            raise ConfigError(f"Отсутствуют параметры: {', '.join(sorted(missing))}")
        if unknown:
            raise ConfigError(f"Неизвестные параметры: {', '.join(sorted(unknown))}")
        if not values["package"]:
            raise ConfigError("Имя пакета не может быть пустым")
        if not values["repository"]:
            raise ConfigError("Репозиторий не может быть пустым")
        test_mode = values["test_mode"].lower()
        if test_mode not in {"true", "false", "да", "нет", "1", "0"}:
            raise ConfigError("test_mode должен быть true/false")
        is_test = test_mode in {"true", "да", "1"}
        pattern = r"[A-Z]+" if is_test else r"[a-z0-9][a-z0-9+.-]*"
        if not re.fullmatch(pattern, values["package"]):
            raise ConfigError("Недопустимое имя пакета для выбранного режима")
        output = Path(values["output"])
        if not values["output"] or output.suffix.lower() != ".png":
            raise ConfigError("output должен указывать на файл .png")
        if any(char in values.get("filter", "") for char in "\n\r\x00"):
            raise ConfigError("filter не должен содержать управляющие символы")
        repository = values["repository"]
        if not is_test and urlparse(repository).scheme not in {"http", "https"}:
            raise ConfigError("В обычном режиме repository должен быть HTTP(S) URL индекса Packages")
        if is_test:
            local = Path(repository)
            if not local.is_absolute():
                local = config_path.parent / local
            if not local.is_file():
                raise ConfigError(f"Файл тестового репозитория не найден: {local}")
        return cls(
            package=values["package"],
            repository=values["repository"],
            test_mode=test_mode in {"true", "да", "1"},
            output=values["output"],
            package_filter=values.get("filter", ""),
        )

    def resolved_repository(self, config_path: str | Path) -> Path:
        value = Path(self.repository).expanduser()
        if not value.is_absolute():
            value = Path(config_path).resolve().parent / value
        return value.resolve()

    def resolved_output(self, config_path: str | Path) -> Path:
        value = Path(self.output).expanduser()
        if not value.is_absolute():
            value = Path(config_path).resolve().parent / value
        return value.resolve()
