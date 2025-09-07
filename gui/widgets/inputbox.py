import tkinter as tk
from tkinter import ttk
from ..config import TRANSCRIPT_FONT

class InputBox(tk.Text):
    """Multiline input buffer with history."""
    def __init__(self, master, on_submit, **kwargs):
        super().__init__(master, height=4, wrap="word", font=TRANSCRIPT_FONT, **kwargs)
        self.on_submit = on_submit
        self.history = []
        self.history_idx = 0
        # bindings
        self.bind("<Return>", self._submit)
        self.bind("<Up>", self._hist_prev)
        self.bind("<Down>", self._hist_next)
    # -------------------------------------------------
    def _get_current_line(self):
        return self.get("1.0", "end-1c")

    def _submit(self, event=None):
        text = self._get_current_line().strip()
        self.delete("1.0", "end")
        if text:
            self.history.append(text)
            self.history_idx = len(self.history)
            self.on_submit(text)
        return "break"

    def _hist_prev(self, event):
        if self.history:
            self.history_idx = max(0, self.history_idx - 1)
            self._show_history()
        return "break"
    def _hist_next(self, event):
        if self.history:
            self.history_idx = min(len(self.history), self.history_idx + 1)
            self._show_history()
        return "break"
    def _show_history(self):
        self.delete("1.0", "end")
        if self.history_idx < len(self.history):
            self.insert("end", self.history[self.history_idx])
