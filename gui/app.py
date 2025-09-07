"""Tk application that wires widgets to the EngineThread."""
import sys
import tkinter as tk
from tkinter import ttk
from pathlib import Path

from .engine_thread import EngineThread
from .config import POLL_MS
from .widgets.transcript import Transcript
from .widgets.inputbox import InputBox


class GameApp(tk.Tk):
    def __init__(self, story_path: Path):
        super().__init__()
        self.title("zyppy-speech")
        self.geometry("1024x768")

        # Engine
        self.engine = EngineThread([str(story_path)])
        self.engine.start()

        # Widgets --------------------------------------------------------
        self.transcript = Transcript(self)
        self.input_box = InputBox(self, on_submit=self._on_command)

        # placeholder frames for right side
        self.state_frame = tk.Text(self, height=10, width=30, state="disabled")
        self.speech_frame = tk.Text(self, height=6, width=30, state="disabled")

        # grid layout ----------------------------------------------------
        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(0, weight=3)
        self.rowconfigure(1, weight=1)

        self.transcript.grid(row=0, column=0, sticky="nsew")
        self.input_box.grid(row=1, column=0, sticky="nsew")
        self.state_frame.grid(row=0, column=1, sticky="nsew")
        self.speech_frame.grid(row=1, column=1, sticky="nsew")

        # start polling
        self.after(POLL_MS, self._poll_engine)

    # ------------------------------------------------------------------
    def _on_command(self, text: str):
        self.engine.enqueue_line(text)

    def _poll_engine(self):
        try:
            while True:
                chunk = self.engine.from_engine.get_nowait()
                self.transcript.append(chunk)
        except Exception:
            pass
        self.after(POLL_MS, self._poll_engine)


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m gui.app STORY_FILE.z5")
        sys.exit(1)
    GameApp(Path(sys.argv[1])).mainloop()

if __name__ == "__main__":
    main()
