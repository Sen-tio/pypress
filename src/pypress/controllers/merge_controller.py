import queue
from pathlib import Path
from typing import Union

import polars as pl
from dataclasses import dataclass
from pdflib_extended.pdflib import PDFlib
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import multiprocessing

from pypress.models.merge.merge_model import MergeThread, MergeThreadException
from pypress.views.merge_view import MergeView

from ..config.config import load_config


config = load_config()


@dataclass
class MergeOptions:
    input_path: Union[Path, str]
    output_path: Union[Path, str]
    template_path: Union[Path, str]
    variable_column: str = None
    file_page_limit: int = 10000
    generate_proof: bool = False


class MergeController:
    def __init__(self, options: MergeOptions) -> None:
        self.options = options
        self.message_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.threads: list[MergeThread] = []
        self.view = MergeView()
        self.p = PDFlib(
            license_key=config["license_key"], version=config["pdflib_version"]
        )

    def _load_data(self) -> pl.DataFrame:
        return pl.read_csv(self.options.input_path, infer_schema_length=0)

    def _set_template_path_column(self, df: pl.DataFrame) -> pl.DataFrame:
        if not self.options.variable_column:
            return df.with_columns(
                pl.lit(self.options.template_path.as_posix()).alias(
                    "__pypress_template_path"
                )
            )

        template_path = Path(self.options.template_path)
        if not template_path.is_dir():
            template_path = template_path.parent

        return df.with_columns(
            pl.col(self.options.variable_column)
            .map_elements(
                lambda x: Path(
                    template_path, x + ".pdf" if not x.lower().endswith(".pdf") else x
                ).as_posix(),
                return_dtype=pl.Utf8,
            )
            .alias("__pypress_template_path")
        )

    def _set_template_page_count_column(self, df: pl.DataFrame) -> pl.DataFrame:
        seen_documents_page_count: dict[str, int] = {}

        def get_document_page_count(file_path: str) -> int:
            if file_path in seen_documents_page_count:
                return seen_documents_page_count[file_path]

            p = PDFlib(version=config["pdflib_version"])
            with p.open_document(file_path) as doc:
                seen_documents_page_count[file_path] = doc.page_count
                return doc.page_count

        if not self.options.variable_column:
            return df.with_columns(
                pl.lit(get_document_page_count(self.options.template_path)).alias(
                    "__pypress_template_page_count"
                )
            )

        return df.with_columns(
            pl.col("__pypress_template_path")
            .apply(get_document_page_count, return_dtype=pl.Int8)
            .alias("__pypress_template_page_count")
        )

    def _split_dataframe_by_pages(
        self,
        df: pl.DataFrame,
    ) -> list[pl.DataFrame]:
        chunks = []
        cumulative_pages = 0
        start_idx = 0

        # Iterate over the rows using indices
        for i, page_count in enumerate(df["__pypress_template_page_count"]):
            cumulative_pages += page_count

            # When cumulative pages exceed max_pages, slice the DataFrame
            if cumulative_pages >= self.options.file_page_limit:
                chunks.append(df[start_idx : i + 1])
                start_idx = i + 1
                cumulative_pages = 0

        # Append the last chunk if there are remaining rows
        if start_idx < df.height:
            chunks.append(df[start_idx:])

        return chunks

    def _start_merge_thread(self, thread_id: int, df: pl.DataFrame) -> pl.DataFrame:
        output_path = (
            self.options.output_path.parent
            / f"{self.options.output_path.stem}_{thread_id + 1}.pdf"
        )
        thread = MergeThread(
            thread_id, self.message_queue, self.stop_event, df, output_path
        )

        thread.start()
        self.threads.append(thread)

    def merge(self) -> None:
        cancelled = False

        df: pl.DataFrame = self._load_data()
        df = self._set_template_path_column(df)
        df = self._set_template_page_count_column(df)
        df_chunks: list[pl.DataFrame] = self._split_dataframe_by_pages(df)

        with ThreadPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
            futures = [
                executor.submit(self._start_merge_thread, i, df_chunks[i])
                for i in range(len(df_chunks))
            ]
            for future in as_completed(futures):
                future.result()

        while (
            any(thread.is_alive() for thread in self.threads)
            or not self.message_queue.empty()
        ):
            try:
                message = self.message_queue.get(timeout=0.01)
                self.view.process_message(message)
            except queue.Empty:
                continue
            except KeyboardInterrupt:
                self.stop_event.set()
                cancelled = True

        if cancelled:
            self.view.display_result_cancelled()
            return
        elif self.stop_event.is_set():
            self.view.display_result_error()
            return

        self.view.display_result_success()
