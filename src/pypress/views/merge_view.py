from typing import Union

from rich import box
from rich.panel import Panel
from rich.text import Text
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    SpinnerColumn,
)
from enum import Enum


class MergeMessageType(Enum):
    PROGRESS_MESSAGE = 1
    PROGRESS_WARNING = 2
    PROGRESS_ERROR = 3
    PROGRESS_UPDATE = 4


class MergeView:
    def __init__(self, task_description: str = "Merging") -> None:
        self.console = Console(log_path=False)
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("•"),
            TimeElapsedColumn(),
            TextColumn("•"),
            TimeRemainingColumn(),
            transient=True,
            console=self.console,
        )
        self.task_id = self.progress.add_task(description=task_description)
        self.display_start()

    def set_progress_total_and_start(self, total: int) -> None:
        self.progress.tasks[self.task_id].total = total
        self.progress.start()

    def process_message(
        self, message: tuple[Union[MergeMessageType, int], Union[int, str]]
    ) -> None:
        if message[0] in [
            MergeMessageType.PROGRESS_MESSAGE,
            MergeMessageType.PROGRESS_WARNING,
            MergeMessageType.PROGRESS_ERROR,
        ]:
            self.progress_message(message[1], message[0].value)
        elif message[0] == MergeMessageType.PROGRESS_UPDATE:
            self.update_progress(message[1])

    def update_progress(self, advance: int) -> None:
        self.progress.update(self.task_id, advance=advance)

    def progress_message(self, message: str, level: int = 1) -> None:
        style = "[bright_black italic]"

        if level == MergeMessageType.PROGRESS_WARNING.value:
            style = "[yellow italic]"
        elif level == MergeMessageType.PROGRESS_ERROR.value:
            style = "[bright_red italic]"

        self.progress.console.log(f"{style}{message}")

    def display_start(self) -> None:
        title = Text("PyPress", style="magenta bold")
        caption = Text("Merge", style="bright_black italic")

        self.console.print(title, caption, "\n")

    def display_result_cancelled(self) -> None:
        self.console.print("\n\n[yellow bold]Merge cancelled! 🚫")

    def display_result_error(self):
        self.progress.stop()
        self.console.print(f"\n[red bold]Merge failed! 💥\n")

    def display_result_success(self):
        self.progress.stop()

        self.console.print(
            f"\n[green bold]Merge completed in "
            f"{self.progress.tasks[self.task_id].elapsed:.2f}s! 🚀\n"
        )
