from typing import Union

from rich.panel import Panel
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
        self.console = Console()
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
        )
        self.task_id = self.progress.add_task(description=task_description, total=20000)
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

        self.progress.console.print(f"{style}{message}")

    def display_result_cancelled(self) -> None:
        self.console.print("\n\n[yellow bold]Merge cancelled! 🚫")

    def display_result_error(self):
        self.progress.stop()
        self.console.print(f"\n[red bold]Merge failed! 💥\n")

    def display_result_success(self):
        self.progress.stop()
        self.console.print(f"\n[green bold]Merge success! 🚀\n")
