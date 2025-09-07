# Runtime State Introspection Helpers – Design Draft

This document describes **non-mutating** helper functions that allow the Tkinter GUI (or any future client) to query live data from an executing xyppy Z-machine without breaking encapsulation or rewriting core op-codes.

> All helpers take an instance of `zenv.Env` (the canonical execution context) and return *plain Python objects* (dict / list / int / str) safe to serialise as JSON.

## 1 Why another layer?
The Z-machine keeps almost everything in its virtual memory, making direct queries tedious.  These helpers centralise the decoding logic so every UI component (Tk, tests, web, etc.) uses *one* source of truth.

## 2 Location in repo
```
xyppy-speech/
└─ state/
   ├─ __init__.py        # re-exports helpers
   ├─ object_table.py    # low-level Z-object parsing utilities
   └─ helpers.py         # high-level façade documented here
```

## 3 High-level API (helpers.py)
```python
from __future__ import annotations
from typing import Dict, List, Any
from xyppy.zenv import Env
from .object_table import (
    unpack_zscii,           # bytes → str
    iter_objects,           # walk all objects
    get_object_by_id,       # id → ObjStruct
)

# ---------- Player ---------------------------------------------------------

def get_player_id(env: Env) -> int:
    """Return the object id reserved for the player (obj #1 by convention)."""
    return 1


def get_player_state(env: Env) -> Dict[str, Any]:
    """Return basic stats about the protagonist."""
    pid = get_player_id(env)
    pobj = get_object_by_id(env, pid)
    return {
        "object_id": pid,
        "short_name": pobj.short_name,
        "parent_room_id": pobj.parent_id,
        "attributes": pobj.flags,  # raw 32-bit attr mask
    }


def get_player_inventory(env: Env) -> List[Dict[str, Any]]:
    """Return a list of carried objects (children of player object)."""
    pid = get_player_id(env)
    return [obj.as_dict() for obj in iter_objects(env, parent_id=pid)]

# ---------- World ----------------------------------------------------------

def get_room_state(env: Env, room_id: int) -> Dict[str, Any]:
    """Return info plus visible items for a given room id."""
    room = get_object_by_id(env, room_id)
    children = [obj.as_dict() for obj in iter_objects(env, parent_id=room_id)]
    return {
        "object_id": room_id,
        "short_name": room.short_name,
        "children": children,
        "attributes": room.flags,
    }


def get_current_room(env: Env) -> Dict[str, Any]:
    """Convenience: derive current room from player’s parent."""
    player = get_object_by_id(env, get_player_id(env))
    return get_room_state(env, player.parent_id)

# ---------- Misc -----------------------------------------------------------

def get_status_line(env: Env) -> str:
    """Return the latest text written to the status bar (window 1)."""
    return env.output_buffer[1].get_status_line()  # helper to implement in vterm
```

Only *read* operations are allowed.  Any function that would mutate `env.mem` MUST live elsewhere.

## 4 Low-level object parsing (object_table.py)
`zenv.Header` exposes `obj_tab_base`.  For v1–3 each object record is 9 bytes; v4+ is 14 bytes.  We wrap that logic in a lightweight `ObjStruct` dataclass:

```python
@dataclass
class ObjStruct:
    object_id: int
    parent_id: int
    sibling_id: int
    child_id: int
    flags: int
    short_name: str

    def as_dict(self):
        return {
            "object_id": self.object_id,
            "short_name": self.short_name,
        }
```

Helper `iter_objects(env, parent_id=None)` walks the tree by following `sibling_id / child_id` pointers, stopping at `0`.

## 5 Thread-safety
Engine runs in its own thread.  Helpers **never** call blocking I/O or Tk.  The GUI thread calls them inside `after()` callbacks.  Accessing `env.mem` is safe because the interpreter mutates only a few bytes at a time; even so, we keep calls short-lived and copy out data.

## 6 Performance
Walking all ~255 objects takes <0.1 ms on CPython.  Results can be cached per turn by listening for an opcode that sets global `turn_counter`, but premature optimisation is avoided.

## 7 Future extensions
* `get_transcript(turn=n)` – slice of scrollback.
* `get_save_blob()` – return a Quetzal save as bytes for cloud saves.

---
*Draft 0.1 – 2025-09-07*
