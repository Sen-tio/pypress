import multiprocessing
import queue
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..models.imposition_thread import ImpositionThread, ImpositionThreadOptions
from ..views.imposition_view import ImpositionView
from pathlib import Path


class ImpositionController:
    def __init__(
        self,
        input_files: list[Path],
        output_path: Path,
        options: ImpositionThreadOptions,
    ) -> None:
        self.options = options
        self.input_files = input_files
        self.output_path = output_path
        self.message_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.threads: list[ImpositionThread] = []
        self.view = ImpositionView()

    def impose(self) -> None:
        cancelled = False

        with ThreadPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
            futures = [
                executor.submit(self._start_imposition_thread, i, self.input_files[i])
                for i in range(len(self.input_files))
            ]

            for future in as_completed(futures):
                future.result()

        self.view.set_progress_total_and_start(len(self.input_files))

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

    def _start_imposition_thread(self, thread_id: int, input_file: Path):
        up: int = self.options.rows * self.options.columns
        output_file: Path = self.output_path / f"{input_file.stem}_{up}up.pdf"

        thread = ImpositionThread(
            thread_id,
            self.message_queue,
            self.stop_event,
            input_file,
            output_file,
            self.options,
        )

        thread.start()
        self.threads.append(thread)
