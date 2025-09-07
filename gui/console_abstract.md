# Tkinter Console Abstraction – Design Document

## 1 Purpose
Provide a thin GUI wrapper around the existing **xyppy** CLI engine so that the game can be played inside a desktop window without modifying engine internals or breaking existing text-based workflows.

## 2 Guiding Principles
1. **Separation of Concerns** – GUI communicates with the engine **solely** via two well-defined channels:
   • **Standard I/O pipes** for all player-facing text (exactly what a human would see or type).  
   • **Canonical read-only helpers** (e.g. `get_player_state()`, `get_room_objects()`) exposed by the engine module for structured data such as player stats, inventory, current room, flags, etc.  
   These helpers never mutate game state—they are _introspection only_—so the engine continues to own all logic while the GUI can render rich parallel views.
2. **Small Modules** – Each file should have one clear responsibility; prefer many tiny modules over a monolith.
3. **DRY** – Re-use helpers (queues, widgets, parsing) via shared utility modules and avoid copy-paste.
4. **Configuration Over Code** – Window layout, colours, polling interval, key bindings, etc. live in `gui/config.py` (or `.toml`) so UX tweaks require no code changes.
5. **Fail-Fast & Recover** – GUI errors must not crash the engine thread; log and keep running.
6. **Cross-Platform** – Only depend on the Python stdlib + Pillow (for GIFs). Avoid native extensions.

## 3 Functional Objectives
• Render the engine’s ANSI/Unicode output in a scrollable read-only **Transcript** pane (top-left).
• Provide a four-line editable **Input Buffer** (bottom-left) that forwards <Enter> to the engine.
• Show a live **Object Explorer** tree (top-right) that mirrors player location & inventory.
• Display an **NPC Speech** panel (bottom-right) for out-of-band dialogue or hints.
• Preserve keyboard shortcuts: ↑ / ↓ command history, Ctrl-L clear screen, etc.
• Allow window resizing; panes adapt proportionally (Tk `grid` weights).

### 3.1 Widget Inventory
| Pane (grid pos) | Widget Class         | Purpose | Key Interactions |
|-----------------|----------------------|---------|------------------|
| **Transcript** (row=0, col=0) | `widgets.transcript.Transcript` (ScrolledText) | Stream of ANSI text coming from engine. Auto-scrolls unless user has scrolled up. | PgUp/PgDn scroll, Ctrl-L clear, search (future). |
| **Input Buffer** (row=1, col=0) | `widgets.inputbox.InputBox` (Text height=4) | Line editing with history. Emits full command on ↵ to `InputQueue`. | ↑/↓ history, Tab autocomplete (future), Ctrl-C abort line. |
| **State Explorer** (row=0, col=1) | `widgets.explorer.Explorer` (ttk.Treeview) | Shows player stats, inventory tree, current room items. Refreshed every turn via `state.helpers`. | Double-click inventory item -> quick “LOOK item”. |
| **Speech Panel** (row=1, col=1) | `widgets.speech.SpeechPane` (Read-only Text) | Displays last N recognised voice phrases + engine replies (“Sorry, didn’t catch…”) | Click phrase -> re-enqueue it as text command. |

The grid weights (`row0=3`, `row1=1`, `col0=3`, `col1=2`) keep the text area dominant while still exposing contextual info.

## 4 Architecture Overview
```
┌───────────────┐       stdout (ANSI)        ┌───────────────────┐
│  Engine Loop  │ ─────────────────────────▶ │  GUI Transcript   │
│  (thread)     │                            │  ScrollText       │
│               │ ◀───────────────────────── │  → Object/Speech  │
└─────▲─▲─▲─────┘       stdin (text)         └─────────┬─────────┘
      │ │ │                                    user input│
      │ │ └───────────────────────────────────────────────┘
      │ │               GUI MainThread
      │ └─→ safe queues (Pipe)  ←────────────────────────────
      └──────────────────────────────────────────────────────
```

• **Pipe** – A `queue.Queue` subclass that behaves like a text stream (`write`, `readline`, `flush`).
• **engine_thread.py** – Boots the game, replaces `sys.stdin/out` with Pipe objects, runs forever.
• **app.py** – Tkinter `Tk` subclass that owns widgets and a 30 ms polling loop.

## 4.1 Threading, Concurrency & Fault-Tolerance
The application always has **exactly two Python threads**:

| Thread | Responsibilities | Must **never** do |
|--------|------------------|--------------------|
| **GUI (MainThread)** | • Owns all Tk widgets.  
• Polls `from_engine` queue every *POLL_MS* ms.  
• Sends user keystrokes & voice-craft commands to `to_engine`. | Call functions that block > 10 ms or touch `env.mem`. |
| **EngineThread** | • Runs `xyppy.__main__.run()` unchanged.  
• Reads from `sys.stdin` (wired to `to_engine`).  
• Writes to `sys.stdout` (wired to `from_engine`). | Make any Tk calls or hold GIL while sleeping. |

### Bridge Objects
* **`pipe.Pipe`** – A subclass of `queue.Queue` + `io.TextIOBase` so that the interpreter believes it is dealing with real files.
* **`InputQueue`** – Extends `queue.PriorityQueue`; shared by keyboard & speech modules (see *input_abstract.md*).
* **`OutputQueue`** – Plain `queue.Queue`; stores raw ANSI bytes.

Both queues are **bounded** (`maxsize=2048`) to prevent unbounded memory growth.  When full, the engine thread blocks (back-pressure) and the GUI shows a soft warning.

### Deadlocks & Lifetime
1. **Startup** –  GUI builds queues, starts EngineThread *(daemon=True)*, then enters `mainloop()`.
2. **Normal operation** –  Engine blocks on `InputQueue.get()`; GUI unblocks it by enqueuing lines.
3. **Quit handling**  –  If the game executes `quit`, EngineThread exits and closes the output queue with a sentinel `None`.  The GUI detects the sentinel and calls `self.destroy()`.
4. **Force-quit** (GUI window close) – GUI enqueues `quit\n` with high priority then waits up to 1 s for thread join; if still alive uses `threading.interrupt_main()` as last resort.

### Exception Flow
* Exceptions in **EngineThread** are caught, formatted and pushed to `OutputQueue` with a `[[ERROR]]` tag so they appear in transcript.
* Exceptions in **GUI thread** bubble up to Tk’s handler; we additionally log to *stderr* and attempt graceful shutdown.

### GIL Considerations
The Z-machine interpreter is CPU-bound but seldom blocks I/O; running it in a separate thread frees the main thread for 60 fps UI refresh even on modest hardware.  No C-extensions that release the GIL are used, so contention is minimal.

### Race-Free Data Access
GUI state panels (object explorer, speech) call the **read-only** helpers from *state_helper.md*.  Each helper copies slices of `env.mem` into local Python objects *within the EngineThread* via a `call_in_engine(fn)` utility which uses a `Queue` + `Event` to synchronously execute the function inside the interpreter thread, guaranteeing consistency without locks.

```
# engine_thread.py
_work_queue: Queue[Callable]

def engine_loop():
    while True:
        try:
            task = _work_queue.get_nowait()
            result = task()
            _result_queue.put(result)
        except queue.Empty:
            step(env)  # normal VM step
```

GUI performs:
```
_result_queue = Queue()
_work_queue.put(lambda: get_current_room(env))
result = _result_queue.get()
```
Only short, non-blocking lambdas are permitted; long enumeration (e.g., entire dictionary dump) must be chunked.

### Avoiding Tk From Worker Thread
Any attempt to update widgets outside the main thread raises `RuntimeError` thanks to a custom `CheckedText` wrapper that asserts `threading.current_thread() is threading.main_thread()`.

## 5 Folder Structure
```
xyppy-speech/
├─ gui/
│  ├─ __init__.py            # GUI package marker
│  ├─ app.py                 # Tk root window & widgets
│  ├─ engine_thread.py       # Starts CLI engine with pipes
│  ├─ pipe.py                # Queue-backed file-like bridge
│  ├─ ansi.py                # Minimal ANSI→Tk tag mapper
│  ├─ parser.py              # (Optional) parse stdout for object/speech panes
│  ├─ widgets/
│  │   ├─ transcript.py      # ScrolledText wrapper + tags
│  │   ├─ inputbox.py        # 4-line Text widget with history
│  │   ├─ explorer.py        # Treeview for objects/rooms
│  │   └─ speech.py          # Read-only Speech pane
│  ├─ config.py              # Default constants + load_from_env()
│  └─ resources/             # Icons, GIFs, style themes
└─ ... existing engine files ...
```

## 6 Key Modules
**pipe.Pipe**
```python
class Pipe(queue.Queue):
    def write(self, data: str):
        self.put(data)
    def readline(self) -> str:
        return self.get()  # block until data
    def flush(self):
        pass  # no-op
```

**engine_thread.start()**
```python
sys.stdin  = stdin_pipe
sys.stdout = stdout_pipe
xyppy.__main__.run()  # unchanged CLI entry-point
```

**ansi.colourise(text, text_widget)** – Scan for `\x1b[31m` etc. and add Tk tags mapped in `config.COLORS`.

## 7 Configuration Examples (`config.py`)
```python
POLL_MS          = 30
TRANSCRIPT_FONT  = ("Cascadia Mono", 11)
COLORS = {
    "31": {"foreground": "#ff5555"},  # red
    "1":  {"font": ("Cascadia Mono", 11, "bold")},
}
```

## 8 Extensibility Hooks
• **signals.py** using `blinker` (optional) to broadcast `post_command`, `room_changed`.  
• Theme loader: drop `*.json` in `resources/themes/` and select at runtime.
• Ability to embed the same Pipe bridge in a test harness → deterministic unit tests.

## 9 Dependencies
* Python ≥ 3.9
* Tkinter (stdlib)
* Pillow (only if GIFs or PNG icons required)

_No external GUI frameworks; keeps install friction minimal._

## 10 Next Steps
1. Implement `pipe.py`, verify unit tests around read/write fairness.
2. Build `engine_thread.py`, confirm CLI still works headless.
3. Prototype `app.py` with Transcript + Input only.
4. Add ANSI colour mapping.
5. Implement Object Explorer parser.
6. Package as `python -m xyppy.gui` entry-point.

---
*Document version 0.1 – 2025-09-07*
