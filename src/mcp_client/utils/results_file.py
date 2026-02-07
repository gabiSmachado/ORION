from pathlib import Path
import csv


def save_results(data: dict, file_path: Path):
    """Persist intent, tool call, and final type definition entries to CSV."""

    fieldnames = ["intent", "intent_processing", "tool_call", "type_definition", "policy"]
    mode = "a" if file_path.is_file() else "w"

    with file_path.open(mode, newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        if mode == "w":
            writer.writeheader()

        sanitized_row = {name: data.get(name, "") for name in fieldnames}
        writer.writerow(sanitized_row)
