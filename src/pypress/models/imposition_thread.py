import math
import queue
import threading
from pathlib import Path
from dataclasses import dataclass, field

from pdflib_extended.pdflib import PDFlib


class ImpositionThreadException(Exception):
    pass


@dataclass
class ImpositionThreadOptions:
    rows: int
    columns: int
    sheet_size: tuple[float, float]
    duplex: bool
    gutter: tuple[float, float] = field(default=(0.0, 0.0))
    bleed: tuple[float, float] = field(default=(0.0, 0.0))
    crop_marks: bool = field(default=False)
    sequential: bool = field(default=False)


class ImpositionThread(threading.Thread):
    def __init__(
        self,
        thread_id: int,
        message_queue: queue.Queue,
        stop_event: threading.Event,
        input_path: Path,
        output_path: Path,
        options: ImpositionThreadOptions,
    ) -> None:
        threading.Thread.__init__(self)
        self.thread_id = thread_id
        self.message_queue = message_queue
        self.stop_event = stop_event
        self.input_path = input_path
        self.output_path = output_path
        self.options = options
        self.p = PDFlib()

    def run(self) -> None:
        # Convert parameters passed as inches into points
        # Gutter gets placed at the edge of each image, so we halve it
        gutter_w, gutter_h = ((x * 72) / 2 for x in self.options.gutter)
        bleed_w, bleed_h = (x * 72 for x in self.options.bleed)
        sheet_w, sheet_h = (x * 72 for x in self.options.sheet_size)

        # Determine resulting shape of final product
        rows, cols = self.options.rows, self.options.columns
        shape = rows * cols

        # Adjust gutter by subtracting it by the bleed
        gutter_w = max(0, gutter_w - bleed_w)
        gutter_h = max(0, gutter_h - bleed_h)

        # Open input document to determine the rest of required information
        with self.p.open_document(self.input_path) as document:
            input_page_count = document.page_count
            resulting_page_count = math.ceil(document.page_count / shape)

            # Use first page to get information
            with document.open_page(page_number=1) as page:
                inf_image_w = page.width
                inf_image_h = page.height

        # Correct resulting page count if the output is duplex
        resulting_page_count += 1 if self.options.duplex else 0

        # Add gutter to page width and height
        image_w = inf_image_w + (gutter_w * 2)
        image_h = inf_image_h + (gutter_h * 2)

        # Calculate the margin
        margin_w = max(0, (sheet_w - (image_w * cols)) / 2)
        margin_h = max(0, (sheet_h - (image_h * rows)) / 2)

        signature: list[tuple[float, float]] = self._calculate_page_signature(
            shape, input_page_count, resulting_page_count
        )

        image_positons: list[tuple[float, float, float, float]] = (
            self._calculate_image_positions(
                rows, cols, image_w, image_h, gutter_w, gutter_h, margin_w, margin_h
            )
        )

        # Begin document and then begin composition routine
        with self.p.start_document(self.output_path, "optimize=true") as new_doc:
            pass

    def _calculate_image_positions(
        self, rows, cols, image_w, image_h, gutter_w, gutter_h, margin_w, margin_h
    ):
        positions: list[tuple[float, float, float, float]] = []
        x1 = y1 = x2 = y2 = 0.0

        for i in range(rows):
            for j in range(cols):
                for k in range(int(self.options.duplex) + 1):
                    if k == 0:
                        x1 = (image_w * j) + gutter_w + margin_w
                        y1 = (
                            (image_h * rows) - (image_h * (i + 1)) + gutter_h + margin_h
                        )
                    elif k == 1:
                        x2 = (
                            (image_w * cols) - (image_w * (j + 1)) + gutter_w + margin_w
                        )
                        y2 = (
                            (image_h * rows) - (image_h * (i + 1)) + gutter_h + margin_h
                        )
                positions.append((x1, y1, x2, y2))

        return positions

    @staticmethod
    def _calculate_page_signature(
        shape: int, input_page_count: int, resulting_page_count: int
    ) -> list[tuple[float, float]]:
        signature: list[tuple[float, float]] = []

        for i in range(shape):
            back = (i * resulting_page_count) + 1
            if i != shape:
                front = i * resulting_page_count
            else:
                front = input_page_count
            signature.append((front, back))

        return signature
