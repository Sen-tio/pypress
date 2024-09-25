from pathlib import Path

import typer
from typing_extensions import Annotated, Literal

from ..controllers.merge_controller import MergeController, MergeOptions


def vaildate_draw_omr(choice: int):
    if choice not in [0, 1, 2]:
        raise typer.BadParameter("Parameter value for draw_omr must be 0, 1, or 2.")
    return choice


def merge(
    input_path: Annotated[
        Path,
        typer.Argument(
            dir_okay=False,
            exists=True,
            show_default=False,
            help="Data file that will be merged.",
        ),
    ],
    output_path: Annotated[
        Path,
        typer.Argument(
            show_default=False, help="Resulting merged file to be written to."
        ),
    ],
    template_path: Annotated[
        Path,
        typer.Argument(
            exists=True, show_default=False, help="Template to be used for the merge."
        ),
    ],
    variable_column: Annotated[
        str,
        typer.Option(
            "--variable-column",
            "-v",
            help="Column to variably select template names from template directory.",
        ),
    ] = None,
    file_page_limit: Annotated[
        int,
        typer.Option(
            "--file-page-limit", "-l", help="Maximum page limit of merged files."
        ),
    ] = 10000,
    generate_proof: Annotated[
        bool,
        typer.Option(
            "--generate-proof",
            "-p",
            help="Create unique proof, on variable column as well if provided.",
        ),
    ] = False,
    draw_omr: Annotated[
        int,
        typer.Option(
            "--draw-omr",
            "-o",
            callback=vaildate_draw_omr,
            help="Draw optical mark recognition lines on merged document. "
            "Pass 1 for simplex or 2 for duplex.",
        ),
    ] = 0,
) -> None:
    merge_options = MergeOptions(
        input_path,
        output_path,
        template_path,
        variable_column,
        file_page_limit,
        generate_proof,
        draw_omr,
    )
    merge_controller = MergeController(merge_options)
    merge_controller.merge()
