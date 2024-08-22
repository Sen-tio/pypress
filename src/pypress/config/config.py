import json
from pathlib import Path
from typing import Any

CONFIG_FILE = Path(__file__).parent / "config.json"

default_config: dict[str, Any] = {"license_key": None, "pdflib_version": 9}


def load_config() -> dict[str, Any]:
    if not CONFIG_FILE.exists():
        with open(CONFIG_FILE, "w") as f:
            f.write(json.dumps(default_config))

    return json.loads(CONFIG_FILE.read_text())


def write_config(config: dict[str, Any]):
    with open(CONFIG_FILE, "w") as f:
        f.write(json.dumps(config))
