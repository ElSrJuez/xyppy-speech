import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from ..config import TRANSCRIPT_FONT

class Transcript(ScrolledText):
    """Read-only scrolling text widget."""
    def __init__(self, master, **kwargs):
        super().__init__(master, wrap="word", font=TRANSCRIPT_FONT, state="disabled", **kwargs)
        # tag for ansi stripped text; color handling later

    def append(self, text: str):
        self.configure(state="normal")
        self.insert("end", text)
        self.see("end")
        self.configure(state="disabled")
