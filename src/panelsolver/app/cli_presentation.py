"""Terminal-only presentation for batch commands.

This module adapts the runtime's text log and progress callbacks.  Solver and
runtime modules deliberately know nothing about Rich.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from types import TracebackType
from typing import Self

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich.text import Text

_LEVEL = re.compile(r"^\[(INFO|WARN|WARNING|ERROR|RUN|OK|SAVE)\]\s*(.*)$")
_STYLES = {
    "INFO": "cyan",
    "WARN": "yellow",
    "WARNING": "yellow",
    "ERROR": "bold red",
    "RUN": "blue",
    "OK": "green",
    "SAVE": "cyan",
}


def use_rich_ui(*, plain: bool, stream=None) -> bool:
    """Return whether an interactive terminal should receive live Rich UI."""
    target = sys.stdout if stream is None else stream
    return not plain and not os.environ.get("CI") and bool(target.isatty())


class CliPresentation:
    """Own the Console and Progress lifecycle for one CLI invocation."""

    def __init__(self, *, rich_ui: bool, verbose: bool, stream=None) -> None:
        self.rich_ui = rich_ui
        self.verbose = verbose
        self.stream = sys.stdout if stream is None else stream
        self.console = Console(file=self.stream, highlight=False) if rich_ui else None
        self.progress: Progress | None = None
        self.task_id: int | None = None

    def start(
        self,
        *,
        domain: str,
        input_path: Path,
        output_path: Path,
        cases: int,
        workers: int,
    ) -> None:
        if not self.rich_ui:
            print(
                f"[RUN] cases={cases} workers={workers} input={input_path}",
                file=self.stream,
                flush=True,
            )
            return
        assert self.console is not None
        table = Table.grid(padding=(0, 2))
        for label, value in (
            ("Domain", domain),
            ("Input", str(input_path)),
            ("Cases", str(cases)),
            ("Workers", str(workers)),
            ("Output", str(output_path)),
        ):
            table.add_row(Text(label, style="bold"), Text(value))
        self.console.print(Panel(table, title="Panel Solver", title_align="left"))
        self.progress = Progress(
            TextColumn("Solving"),
            BarColumn(),
            TextColumn("{task.completed:.0f}/{task.total:.0f}"),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            TextColumn("ETA"),
            TimeRemainingColumn(),
            console=self.console,
        )
        self.progress.start()
        self.task_id = self.progress.add_task("Solving", total=cases)

    def log(self, message: str) -> None:
        if not self.rich_ui:
            print(message, file=self.stream, flush=True)
            return
        match = _LEVEL.match(message)
        level, text = match.groups() if match else ("INFO", message)
        if level in {"RUN", "OK"} and not self.verbose:
            return
        label = "WARN" if level == "WARNING" else level
        assert self.console is not None
        self.console.print(f"[{_STYLES[level]}]{label:<5}[/] {escape(text)}")

    def update(self, done: int, total: int) -> None:
        if self.progress is not None and self.task_id is not None:
            self.progress.update(self.task_id, completed=done, total=total)

    def finish(self, output_path: Path) -> None:
        if self.progress is not None:
            self.progress.stop()
        if self.rich_ui:
            assert self.console is not None
            message = Text("OK", style="green")
            message.append("    Wrote results: ")
            message.append(str(output_path))
            self.console.print(message)
        else:
            print(f"[OK] Wrote results: {output_path}", file=self.stream, flush=True)

    def close(self) -> None:
        if self.progress is not None:
            self.progress.stop()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        self.close()


__all__ = ("CliPresentation", "use_rich_ui")
