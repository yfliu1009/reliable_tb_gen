# this tool is to calculate the sum of input_len in the json file
# can use for analyzing the input length per request
# usage: python sum_input_len.py <path_to_json>

import json
import sys
from pathlib import Path
from typing import Any, Optional

def to_int(v: Any) -> Optional[int]:
    """Best-effort convert to int; return None if impossible."""
    if isinstance(v, int):
        return v
    if isinstance(v, float) and v.is_integer():
        return int(v)
    if isinstance(v, str):
        try:
            return int(v.strip())
        except ValueError:
            return None
    return None

def main():
    if len(sys.argv) != 2:
        print("Usage: python sum_input_len.py <path_to_json>")
        sys.exit(1)

    path = Path(sys.argv[1])
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    dataset = data.get("dataset", [])
    if not isinstance(dataset, list):
        print("Error: 'dataset' must be a list.")
        sys.exit(2)

    total = 0
    counted = 0
    skipped = 0

    for item in dataset:
        if not isinstance(item, dict):
            skipped += 1
            continue
        val = to_int(item.get("input_len"))
        if val is None:
            skipped += 1
        else:
            total += val
            counted += 1

    print(f"sum(input_len) = {total}")
    print(f"counted = {counted}, skipped = {skipped}")

if __name__ == "__main__":
    main()
