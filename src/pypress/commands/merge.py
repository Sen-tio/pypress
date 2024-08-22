from pathlib import Path

import typer
from typing_extensions import Annotated

from ..controllers.merge_controller import MergeController, MergeOptions


def merge(
    input_path: Annotated[
        Path, typer.Argument(dir_okay=False, exists=True, show_default=False)
    ],
    output_path: Annotated[Path, typer.Argument(show_default=False)],
    template_path: Annotated[Path, typer.Argument(exists=True, show_default=False)],
    variable_column: Annotated[str, typer.Option("--variable-column", "-v")] = None,
    file_page_limit: Annotated[int, typer.Option("--file-page-limit", "-l")] = 10000,
    generate_proof: Annotated[bool, typer.Option("--generate-proof", "-p")] = False,
) -> None:
    merge_options = MergeOptions(
        input_path,
        output_path,
        template_path,
        variable_column,
        file_page_limit,
        generate_proof,
    )
    merge_controller = MergeController(merge_options)
    merge_controller.merge()
