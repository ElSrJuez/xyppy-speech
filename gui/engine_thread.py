"""Spin up the unmodified xyppy interpreter in its own thread with Pipe objects.

Usage (from gui.app):
    eng = EngineThread(["story.z5"])
    eng.start()
"""
from __future__ import annotations
import threading
import sys
from typing import List
from pathlib import Path

from .pipe import Pipe

class EngineThread(threading.Thread):
    def __init__(self, argv: List[str]):
        super().__init__(daemon=True)
        self.argv = argv
        self.stdin_pipe: Pipe = Pipe()
        self.stdout_pipe: Pipe = Pipe()

    # public handles for GUI
    @property
    def to_engine(self):
        return self.stdin_pipe
    @property
    def from_engine(self):
        return self.stdout_pipe

    # ---------------------------------------------------------------------
    def run(self):
        # Swap stdio for this thread only
        sys.stdin = self.stdin_pipe  # type: ignore
        sys.stdout = self.stdout_pipe  # type: ignore

        # Import here so we don't pull in heavy deps until thread starts
        from xyppy import __main__ as xyppy_main
        # Mimic CLI invocation
        sys.argv = ["xyppy"] + self.argv
        xyppy_main.main()  # type: ignore

    # convenience ---------------------------------------------------------
    def enqueue_line(self, line: str):
        if not line.endswith("\n"):
            line += "\n"
        self.stdin_pipe.write(line)
