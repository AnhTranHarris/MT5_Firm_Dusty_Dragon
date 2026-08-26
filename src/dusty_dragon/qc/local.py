from __future__ import annotations

import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class QcCommand:
    name: str
    argv: tuple[str, ...]


def build_qc_plan(*, install: bool) -> tuple[QcCommand, ...]:
    commands: list[QcCommand] = []
    if install:
        commands.append(
            QcCommand(
                name="install",
                argv=(sys.executable, "-m", "pip", "install", "-e", ".[dev]"),
            )
        )
    commands.extend(
        (
            QcCommand(name="ruff", argv=("ruff", "check", ".")),
            QcCommand(name="pytest", argv=("pytest",)),
        )
    )
    return tuple(commands)


def run_qc(*, repository_root: Path, install: bool) -> int:
    for command in build_qc_plan(install=install):
        result = _run(command.argv, cwd=repository_root)
        if result != 0:
            return result
    return 0


def _run(argv: Sequence[str], *, cwd: Path) -> int:
    completed = subprocess.run(argv, cwd=cwd, check=False)
    return completed.returncode
