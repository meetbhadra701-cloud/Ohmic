"""Config loader — single source of truth is backend/config.yaml."""
from __future__ import annotations

import pathlib
from typing import Any

import yaml

_DEFAULT_PATH = pathlib.Path(__file__).resolve().parent.parent / "config.yaml"


def load_config(path: str | pathlib.Path | None = None) -> dict[str, Any]:
    """Load and parse the YAML config. Defaults to backend/config.yaml."""
    p = pathlib.Path(path) if path else _DEFAULT_PATH
    with p.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)
