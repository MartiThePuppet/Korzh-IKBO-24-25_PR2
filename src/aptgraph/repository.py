from __future__ import annotations

import gzip
import lzma
import re
import urllib.request
from pathlib import Path

INDEX_TIMEOUT = 20
GZIP_SIGNATURE = b"\x1f\x8b"
XZ_SIGNATURE = b"\xfd7zXZ\x00"


class RepositoryError(RuntimeError):
    """Repository data could not be loaded or parsed."""


def _read_remote_index(url: str) -> bytes:
    try:
        with urllib.request.urlopen(url, timeout=INDEX_TIMEOUT) as response:
            return response.read()
    except OSError as exc:
        raise RepositoryError(f"Не удалось скачать индекс: {url}") from exc


def _read_local_index(path: Path) -> bytes:
    if path.is_dir():
        index = next((item for item in path.rglob("Packages*")
                      if item.is_file()), None)
    else:
        index = path if path.is_file() else None
    if index is None:
        raise RepositoryError(f"Индекс Packages не найден: {path}")
    try:
        return index.read_bytes()
    except OSError as exc:
        raise RepositoryError(f"Не удалось прочитать индекс: {index}") from exc


def _decode_index(data: bytes) -> str:
    try:
        if data.startswith(GZIP_SIGNATURE):
            data = gzip.decompress(data)
        elif data.startswith(XZ_SIGNATURE):
            data = lzma.decompress(data)
    except (OSError, EOFError, lzma.LZMAError) as exc:
        raise RepositoryError("Повреждённый сжатый индекс Packages") from exc
    return data.decode("utf-8", errors="replace")


def _read_fields(record: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    current = None
    for line in record.splitlines():
        if line.startswith((" ", "\t")) and current:
            fields[current] += " " + line.strip()
        elif ":" in line:
            current, _, value = line.partition(":")
            fields[current] = value.strip()
    return fields


def _dependency_name(option: str) -> str:
    return re.split(r"[\s(:\[]", option.strip(), maxsplit=1)[0]


def _dependency_groups(fields: dict[str, str]) -> list[list[str]]:
    depends = ",".join(fields.get(key, "")
                       for key in ("Pre-Depends", "Depends"))
    return [
        list(map(_dependency_name, group.split("|")))
        for group in depends.split(",") if group.strip()
    ]


def _register_providers(
    providers: dict[str, str], fields: dict[str, str], name: str
) -> None:
    for option in fields.get("Provides", "").split(","):
        virtual = _dependency_name(option)
        if virtual:
            providers.setdefault(virtual, name)


def _select_dependency(
    group: list[str], packages: set[str], providers: dict[str, str]
) -> str:
    for name in group:
        if name in packages:
            return name
    for name in group:
        if name in providers:
            return providers[name]
    return group[0]


class AptRepository:
    """Load dependencies from a Debian Packages index."""

    def __init__(self, source: str | Path):
        self.source = str(source)
        self.packages: dict[str, list[str]] = {}

    def load(self) -> dict[str, list[str]]:
        self.packages = self._parse_packages(self._read_source())
        return self.packages

    def _read_source(self) -> bytes:
        if self.source.startswith(("http://", "https://")):
            return _read_remote_index(self.source)
        return _read_local_index(Path(self.source))

    @staticmethod
    def _parse_packages(data: bytes) -> dict[str, list[str]]:
        alternatives: dict[str, list[list[str]]] = {}
        providers: dict[str, str] = {}
        for record in re.split(r"\n\s*\n", _decode_index(data)):
            fields = _read_fields(record)
            name = fields.get("Package")
            if name:
                alternatives[name] = _dependency_groups(fields)
                _register_providers(providers, fields, name)
        if not alternatives:
            raise RepositoryError("Индекс Packages не содержит пакетов")
        packages = set(alternatives)
        return {
            name: list(dict.fromkeys(
                _select_dependency(group, packages, providers)
                for group in groups
            ))
            for name, groups in alternatives.items()
        }
