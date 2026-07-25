"""Append-only dated history files with atomic writes."""
import json
import os
import tempfile
from pathlib import Path


def load(path):
    p = Path(path)
    return json.loads(p.read_text()) if p.exists() else {"points": []}


def atomic_write(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=p.parent, suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


def append_point(path, point, required_keys):
    missing = [k for k in required_keys if point.get(k) is None]
    if missing:
        raise ValueError(f"missing required keys: {missing}")
    data = load(path)
    dup = any(pt["date"] == point["date"] and pt.get("segment") == point.get("segment")
              for pt in data["points"])
    if dup:
        return False
    data["points"].append(point)
    atomic_write(path, data)
    return True
