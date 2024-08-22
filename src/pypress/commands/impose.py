from pathlib import Path
from typing import Union

import typer
from typing_extensions import Annotated
from ..controllers.imposition_controller import ImpositionController
from ..models.imposition_thread import ImpositionThreadOptions


def impose(
    input_path: Annotated[
        list[Path],
        typer.Argument(dir_okay=False, exists=True, show_default=False),
    ],
    output_path: Annotated[Path, typer.Argument(show_default=False)],
    rows: Annotated[int, typer.Argument(help="Number of rows", show_default=False)],
    columns: Annotated[
        int, typer.Argument(help="Number of columns", show_default=False)
    ],
    sheet_size: Annotated[
        tuple[float, float],
        typer.Argument(help="Sheet size as width and height", show_default=False),
    ],
    duplex: Annotated[
        bool, typer.Option("--duplex", "-d", help="Enable duplex printing")
    ] = False,
    gutter: Annotated[
        tuple[float, float],
        typer.Option("--gutter", "-g", help="Gutter size as width and height"),
    ] = (0.0, 0.0),
    bleed: Annotated[
        tuple[float, float],
        typer.Option("--bleed", "-b", help="Bleed size as width and height"),
    ] = (0.0, 0.0),
    crop_marks: Annotated[
        bool, typer.Option("--crop-marks", "-m", help="Enable crop marks")
    ] = False,
) -> None:
    imposition_options = ImpositionThreadOptions(
        rows=rows,
        columns=columns,
        sheet_size=sheet_size,
        duplex=duplex,
        gutter=gutter,
        bleed=bleed,
        crop_marks=crop_marks,
    )

    imposition_controller = ImpositionController(
        input_files=input_path, output_path=output_path, options=imposition_options
    )

    imposition_controller.impose()
