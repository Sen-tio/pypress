import math
import queue
import threading
from dataclasses import dataclass, field
from pathlib import Path

from pdflib_extended.pdflib import PDFlib

from ..config.config import load_config
from ..views.imposition_view import MessageType

config = load_config()


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
        self.p = PDFlib(
            license_key=config["license_key"], version=config["pdflib_version"]
        )

    def run(self) -> None:
        # Convert parameters passed as inches into points
        # Gutter gets placed at the edge of each img, so we halve it
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
        with self.p.open_document(self.input_path) as doc:
            input_page_count = doc.page_count
            resulting_page_count = math.ceil(doc.page_count / shape)

            # Use first page to get information
            inf_img_w = self.p.pcos_get_number(doc.handle, "pages[1]/width")
            inf_img_h = self.p.pcos_get_number(doc.handle, "pages[1]/height")

        # Correct resulting page count if the output is duplex
        if self.options.duplex and resulting_page_count % 2 != 0:
            resulting_page_count += 1

        # Add gutter to page width and height
        img_w = inf_img_w + (gutter_w * 2)
        img_h = inf_img_h + (gutter_h * 2)

        # Calculate the margin
        margin_w = max(0, (sheet_w - (img_w * cols)) / 2)
        margin_h = max(0, (sheet_h - (img_h * rows)) / 2)

        # Calculate page signature
        signature: list[int] = [i * resulting_page_count + 1 for i in range(shape)]

        img_pos: list[tuple[float, float, float, float]] = (
            self._calculate_img_positions(
                rows, cols, img_w, img_h, gutter_w, gutter_h, margin_w, margin_h
            )
        )

        # Begin document and then begin composition routine
        with self.p.start_document(
            self.output_path, "optimize=true"
        ) as new_doc, self.p.open_document(self.input_path) as doc:

            # Create new page in resulting document for each calculated final page
            for i in range(resulting_page_count):
                with new_doc.start_page(sheet_w, sheet_h) as _:

                    # Place all images in calculated locations
                    for j in range(shape):
                        page_number: int = signature[j] + i

                        if page_number > input_page_count:
                            continue

                        with doc.open_page(page_number) as page:
                            sig_idx = 2 if i % 2 == 0 and self.options.duplex else 0
                            page.fit_page(img_pos[j][sig_idx], img_pos[j][sig_idx + 1])

                    # Draw marks on current page if the option was passed
                    if self.options.crop_marks:
                        self._draw_crop_marks()

        self.message_queue.put((MessageType.PROGRESS_UPDATE, 1))

    def _calculate_img_positions(
        self, rows, cols, img_w, img_h, gutter_w, gutter_h, margin_w, margin_h
    ):
        positions: list[tuple[float, float, float, float]] = []
        x1 = y1 = x2 = y2 = 0.0

        for i in range(rows):
            for j in range(cols):
                for k in range(int(self.options.duplex) + 1):
                    if k == 0:
                        x1 = (img_w * j) + gutter_w + margin_w
                        y1 = (img_h * rows) - (img_h * (i + 1)) + gutter_h + margin_h
                    elif k == 1:
                        x2 = (img_w * cols) - (img_w * (j + 1)) + gutter_w + margin_w
                        y2 = (img_h * rows) - (img_h * (i + 1)) + gutter_h + margin_h
                positions.append((x1, y1, x2, y2))

        return positions

    def _draw_crop_marks(self):
        pass


if __name__ == "__main__":
    options = ImpositionThreadOptions(
        rows=2, columns=2, sheet_size=(13.0, 9.0), duplex=True
    )

    thread = ImpositionThread(
        thread_id=1,
        message_queue=queue.Queue(),
        stop_event=threading.Event(),
        input_path=Path(r"Y:\Archway\948876\948876_PRINT_1.pdf"),
        output_path=Path(r"Y:\Archway\948876\948876_PRINT_1_4up.pdf"),
        options=options,
    )

    thread.start()
