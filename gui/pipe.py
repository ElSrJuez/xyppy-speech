import queue
import io

class Pipe(queue.Queue, io.TextIOBase):
    """Queue-backed text stream that implements minimal file-like methods
    used by the xyppy interpreter for stdin/stdout replacement."""
    def __init__(self, maxsize: int = 2048):
        queue.Queue.__init__(self, maxsize=maxsize)
        io.TextIOBase.__init__(self)

    # --- file-like ---------------------------------------------------------
    def write(self, s: str):  # type: ignore[override]
        self.put(s)
    def readline(self, *args, **kwargs):  # type: ignore[override]
        return self.get()
    def flush(self):
        pass
