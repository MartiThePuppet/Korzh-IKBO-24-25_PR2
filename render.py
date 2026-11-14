from __future__ import annotations

import json
import shutil
import subprocess
import urllib.request
from pathlib import Path

from .graph import Graph


def mermaid(graph: Graph, root: str) -> str:
    names = {name: f"n{index}" for index, name in enumerate(graph.edges)}
    lines = ["flowchart TD"]
    for name, identifier in names.items():
        lines.append(f"    {identifier}[{json.dumps(name)}]")
    for source, dependencies in graph.edges.items():
        for target in dependencies:
            lines.append(f"    {names[source]} --> {names[target]}")
    return "\n".join(lines) + "\n"


def save_png(source: str, path: Path, offline: bool = False) -> None:
    """Render Mermaid locally with mmdc or via the public Kroki service."""
    path.parent.mkdir(parents=True, exist_ok=True)
    mermaid_path = path.with_suffix(".mmd")
    mermaid_path.write_text(source, encoding="utf-8")
    executable = shutil.which("mmdc")
    if executable:
        subprocess.run(
            [executable, "-i", str(mermaid_path), "-o", str(path)],
            check=True, timeout=120,
        )
        return
    if offline:
        raise RuntimeError("Установите Mermaid CLI (mmdc) для офлайн-рендеринга")
    payload = json.dumps({
        "diagram_source": source,
        "diagram_type": "mermaid",
        "output_format": "png",
    }).encode("utf-8")
    request = urllib.request.Request(
        "https://kroki.io/", payload,
        {"Content-Type": "application/json", "User-Agent": "aptgraph/1.0"},
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        png = response.read()
    if not png.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError("Сервис визуализации вернул не PNG")
    path.write_bytes(png)
