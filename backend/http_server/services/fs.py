from pathlib import Path


def browse(path: str | None, kind: str) -> dict:
    base = Path(path).expanduser() if path else Path.home()
    if not base.exists() or not base.is_dir():
        raise ValueError(f"Путь '{base}' не существует.")

    items = []
    try:
        for entry in sorted(
            base.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())
        ):
            if entry.name.startswith("."):
                continue
            is_dir = entry.is_dir()
            if kind == "dir" and not is_dir:
                continue
            if kind == "file" and is_dir:
                continue
            items.append(
                {
                    "name": entry.name,
                    "path": str(entry),
                    "type": "dir" if is_dir else "file",
                }
            )
    except PermissionError:
        pass

    return {
        "path": str(base),
        "parent": str(base.parent) if base != base.parent else None,
        "items": items,
    }
