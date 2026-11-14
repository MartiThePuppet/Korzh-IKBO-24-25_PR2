from __future__ import annotations

import gzip
import json
import lzma
import re
import urllib.request
from pathlib import Path


class RepositoryError(RuntimeError):
    pass


class AptRepository:
    """Reads a small JSON fixture or Debian Packages index without apt libraries."""

    def __init__(self, source: str | Path, test_mode: bool = False):
        self.source = str(source)
        self.test_mode = test_mode
        self.packages: dict[str, list[str]] = {}

    def load(self) -> dict[str, list[str]]:
        if self.test_mode:
            path = Path(self.source)
            if not path.is_file():
                raise RepositoryError(f"Тестовый репозиторий не найден: {path}")
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(raw, dict) or any(not isinstance(v, list) for v in raw.values()):
                    raise ValueError
                if any(not isinstance(k, str) or not re.fullmatch(r"[A-Z]+", k)
                       for k in raw):
                    raise ValueError
                if any(not isinstance(x, str) or not re.fullmatch(r"[A-Z]+", x)
                       for deps in raw.values() for x in deps):
                    raise ValueError
                self.packages = raw
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                raise RepositoryError("Некорректный JSON тестового репозитория") from exc
            return self.packages

        data = self._read_source()
        self.packages = self._parse_packages(data)
        return self.packages

    def _read_source(self) -> bytes:
        if self.source.startswith(("http://", "https://")):
            try:
                with urllib.request.urlopen(self.source, timeout=20) as response:
                    return response.read()
            except OSError as exc:
                raise RepositoryError(f"Не удалось скачать индекс: {self.source}") from exc
        path = Path(self.source)
        if path.is_file():
            try:
                return path.read_bytes()
            except OSError as exc:
                raise RepositoryError(f"Не удалось прочитать индекс: {path}") from exc
        candidates = list(path.glob("**/Packages*")) if path.is_dir() else []
        if not candidates:
            raise RepositoryError(f"Индекс Packages не найден: {path}")
        return candidates[0].read_bytes()

    @staticmethod
    def _parse_packages(data: bytes) -> dict[str, list[str]]:
        if data[:2] == b"\x1f\x8b":
            data = gzip.decompress(data)
        elif data[:6] == b"\xfd7zXZ\x00":
            data = lzma.decompress(data)
        text = data.decode("utf-8", errors="replace")
        result: dict[str, list[str]] = {}
        alternatives: dict[str, list[list[str]]] = {}
        providers: dict[str, str] = {}
        for record in re.split(r"\n\s*\n", text):
            fields: dict[str, str] = {}
            current = None
            for line in record.splitlines():
                if line.startswith((" ", "\t")) and current:
                    fields[current] += " " + line.strip()
                elif ":" in line:
                    current, value = line.split(":", 1)
                    fields[current] = value.strip()
            name = fields.get("Package")
            if name:
                depends = ",".join(fields.get(key, "")
                                   for key in ("Pre-Depends", "Depends"))
                alternatives[name] = [
                    [re.split(r"[\s(:\[]", option.strip(), 1)[0]
                     for option in group.split("|")]
                    for group in depends.split(",") if group.strip()
                ]
                result[name] = []
                for provided in fields.get("Provides", "").split(","):
                    virtual = re.split(r"[\s(:]", provided.strip(), 1)[0]
                    if virtual:
                        providers.setdefault(virtual, name)
        for name, groups in alternatives.items():
            for group in groups:
                selected = next((item for item in group if item in result), None)
                if selected is None:
                    selected = next((providers[item] for item in group
                                     if item in providers), group[0])
                if selected not in result[name]:
                    result[name].append(selected)
        if not result:
            raise RepositoryError("Индекс Packages не содержит пакетов")
        return result
