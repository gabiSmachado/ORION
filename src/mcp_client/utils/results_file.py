from pathlib import Path
import csv
from typing import Iterable, Mapping


def save_results(data: Mapping | Iterable[Mapping], file_path: Path):
    """Persist intent, tool call, and final type definition entries to CSV."""

    fieldnames = ["intent", "tool_call", "type_definition"]
    rows = data if isinstance(data, Iterable) and not isinstance(data, Mapping) else [data]
    rows = [row for row in rows if isinstance(row, Mapping)]
    if not rows:
        return

    mode = "a" if file_path.is_file() else "w"
    with open(file_path, mode=mode, newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if mode == "w":
            writer.writeheader()
        writer.writerows(rows)