from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv


def load_config(path: str | None) -> dict:
    """Читает настройки из файла или из переменной DIGEST_CONFIG (для GitHub Actions)."""
    load_dotenv()
    if os.environ.get("DIGEST_CONFIG"):
        cfg = yaml.safe_load(os.environ["DIGEST_CONFIG"])
    else:
        cfg = yaml.safe_load(Path(path or "config.yaml").read_text(encoding="utf-8"))
    return cfg or {}


def env(name: str, required: bool = True) -> str | None:
    value = os.environ.get(name)
    if required and not value:
        raise RuntimeError(f"Не задана переменная окружения {name} (см. README)")
    return value
