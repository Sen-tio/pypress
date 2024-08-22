from enum import Enum
from typing import Union

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
from rich.text import Text


class MessageType(Enum):
    PROGRESS_MESSAGE = 1
    PROGRESS_WARNING = 2
    PROGRESS_ERROR = 3
    PROGRESS_UPDATE = 4


class ImpositionView:
    def __init__(self, task_description: str = "Imposing") -> None:
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
        self, message: tuple[Union[MessageType, int], Union[int, str]]
    ) -> None:
        if message[0] in [
            MessageType.PROGRESS_MESSAGE,
            MessageType.PROGRESS_WARNING,
            MessageType.PROGRESS_ERROR,
        ]:
            self.progress_message(message[1], message[0].value)
        elif message[0] == MessageType.PROGRESS_UPDATE:
            self.update_progress(message[1])

    def update_progress(self, advance: int) -> None:
        self.progress.update(self.task_id, advance=advance)

    def progress_message(self, message: str, level: int = 1) -> None:
        style = "[bright_black italic]"

        if level == MessageType.PROGRESS_WARNING.value:
            style = "[yellow italic]"
        elif level == MessageType.PROGRESS_ERROR.value:
            style = "[bright_red italic]"

        self.progress.console.log(f"{style}{message}")

    def display_start(self) -> None:
        title = Text("PyPress", style="magenta bold")
        caption = Text("Imposition", style="bright_black italic")

        self.console.print(title, caption, "\n")

    def display_result_cancelled(self) -> None:
        self.console.print("\n\n[yellow bold]Imposition cancelled! 🚫")

    def display_result_error(self):
        self.progress.stop()
        self.console.print(f"\n[red bold]Imposition failed! 💥\n")

    def display_result_success(self):
        self.progress.stop()

        self.console.print(
            f"\n[green bold]Imposition completed in "
            f"{self.progress.tasks[self.task_id].elapsed:.2f}s! 🚀\n"
        )
