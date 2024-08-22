from typing import Any, Annotated

import typer
from rich.console import Console

from ..config.config import write_config, load_config

console = Console()


def config(
    key: Annotated[str, typer.Argument(show_default=False)] = None,
    value: Annotated[str, typer.Argument(show_default=False)] = None,
) -> None:
    config: dict[str, Any] = load_config()

    if not key and not value:
        console.print(config)
        return

    if key not in config.keys():
        console.print(
            f"{key} is not a valid configuration option, "
            f"type pypress config to see a list of available options",
            style="bold red",
        )
        return

    config[key] = value
    write_config(config)

    console.print(f"{key} has been set to '{value}'", style="bold green")
