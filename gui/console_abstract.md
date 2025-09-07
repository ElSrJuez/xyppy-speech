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
