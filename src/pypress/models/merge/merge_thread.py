import queue
import re
import threading
from pathlib import Path
from typing import Any

import polars as pl
from pdflib_extended.pdflib import PDFlib

from .merge_cache import MergeCache, Document, Page, Block, MergeCacheException
from ...config.config import load_config
from ...views.merge_view import MergeMessageType

config = load_config()


class MergeThreadException(Exception):
    pass


class MergeFieldException(Exception):
    pass


class MergeThread(threading.Thread):
    def __init__(
        self,
        thread_id: int,
        message_queue: queue.Queue,
        stop_event: threading.Event,
        df: pl.DataFrame,
        output_path: Path,
    ) -> None:
        threading.Thread.__init__(self)
        self.thread_id = thread_id
        self.message_queue = message_queue
        self.stop_event = stop_event
        self.df = df
        self.output_path = output_path
        self.p = PDFlib(
            license_key=config["license_key"], version=config["pdflib_version"]
        )
        self.cache = MergeCache(self.p)

    def run(self) -> None:
        try:
            self.merge_loop()
        except MergeThreadException as e:
            self.message_queue.put(
                (MergeMessageType.PROGRESS_ERROR, f"Thread-ID-{self.thread_id}: {e}")
            )
            self.throw_error()

    def merge_loop(self) -> None:
        self.df = self.df.with_columns(
            pl.col("__pypress_template_page_count").cast(pl.Int8)
        )

        res: int = self.p.begin_document(self.output_path.as_posix(), "optimize=true")
        if res < 0:
            self.throw_error()
            raise MergeThreadException(self.p.get_errmsg())

        for row in self.df.iter_rows(named=True):
            if self.stop_event.is_set():
                self.message_queue.put(
                    (
                        MergeMessageType.PROGRESS_WARNING,
                        f"Thread-ID-{self.thread_id}: Shutting down",
                    )
                )
                return

            self.merge_document(row)
            self.message_queue.put(
                (MergeMessageType.PROGRESS_UPDATE, row["__pypress_template_page_count"])
            )

        self.cache.clear_cache()
        self.p.end_document("")

        self.message_queue.put(
            (
                MergeMessageType.PROGRESS_MESSAGE,
                f"Thread-ID-{self.thread_id}: Wrote file {self.output_path.name}",
            )
        )

    def merge_document(self, row: dict[str, Any]) -> None:
        doc_path: str = row["__pypress_template_path"]

        try:
            doc: Document = self.cache.get_or_cache_document(doc_path)
        except MergeCacheException as e:
            self.throw_error()
            raise MergeThreadException(str(e))

        for page in doc.pages:
            self.merge_page(doc, page, row)

    def merge_page(self, doc: Document, page: Page, row: dict[str, Any]) -> None:
        self.p.begin_page_ext(page.width, page.height, "")
        self.p.fit_image(page.image_handle, 0, 0, "fitmethod=meet")
        self.p.fit_pdi_page(page.handle, 0, 0, "blind")

        for block in page.blocks:
            self.merge_block(doc, page, block, row)

        self.p.end_page_ext("")

    def merge_block(
        self, doc: Document, page: Page, block: Block, row: dict[str, Any]
    ) -> None:
        try:
            replaced_text = replace_merge_fields(block.text, row)
        except MergeFieldException as e:
            self.throw_error()
            raise MergeThreadException(
                f"Block '{block.name}' on page {page.number} of document "
                f"'{doc.name}' could not be filled, {e}"
            )

        if block.type.lower() == "text":
            result: int = self.merge_text_block(page, block, replaced_text)
        elif block.type.lower() == "image":
            result: int = self.merge_image_block(page, block, replaced_text)
        elif block.type.lower() == "pdf":
            result: int = self.merge_pdf_block(page, block, replaced_text)
        elif block.type.lower() == "graphics":
            result: int = self.merge_graphics_block(page, block, replaced_text)
        else:
            raise MergeThreadException(f"Unsupported block type: {block.type}")

        if result < 0:
            self.throw_error()
            raise MergeThreadException(self.p.get_errmsg())

    def merge_graphics_block(self, page: Page, block: Block, replaced_text: str) -> int:
        try:
            graphics_handle: int = self.cache.get_or_cache_graphics(replaced_text)
        except MergeCacheException:
            self.message_queue.put(
                (
                    MergeMessageType.PROGRESS_WARNING,
                    f"Image could not be placed: {replaced_text}",
                )
            )
            return 1

        return self.p.fill_graphicsblock(page.handle, block.name, graphics_handle, "")

    def merge_pdf_block(self, page: Page, block: Block, replaced_text: str) -> int:
        try:
            pdf_block_page: Page = self.cache.get_or_cache_pdf_page(
                replaced_text, block.page
            )
        except MergeCacheException as e:
            self.message_queue.put(
                (
                    MergeMessageType.PROGRESS_WARNING,
                    f"PDF could not be placed '{replaced_text}': {e}",
                )
            )
            return 1

        return self.p.fill_pdfblock(page.handle, block.name, pdf_block_page.handle, "")

    def merge_text_block(self, page: Page, block: Block, replaced_text: str) -> int:
        return self.p.fill_textblock(
            page.handle, block.name, replaced_text, "encoding=unicode embedding"
        )

    def merge_image_block(self, page: Page, block: Block, replaced_text: str) -> int:
        try:
            image_handle: int = self.cache.get_or_cache_image(replaced_text)
        except MergeCacheException:
            self.message_queue.put(
                (
                    MergeMessageType.PROGRESS_WARNING,
                    f"Image could not be placed: {replaced_text}",
                )
            )
            return 1

        return self.p.fill_imageblock(page.handle, block.name, image_handle, "")

    def throw_error(self) -> None:
        self.stop_event.set()


def replace_merge_fields(text: str, row: dict[str, Any]) -> str:
    try:
        text: str = re.sub("«(.*?)»", lambda m: row[m.group(1).lower()], text)
        text = re.sub("(\\r\\n)+", "\r\n", text).strip()
    except KeyError as e:
        raise MergeFieldException(f"Column '{e.args[0]}' not found in data")

    if text == "":
        # Avoid empty block to force fill
        return " "

    return text
