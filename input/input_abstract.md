# Unified Input Layer – Design Notes

This document describes how **xyppy-GUI** will handle user keyboard commands and asynchronously injected "craft" commands (e.g. produced by a speech-recognition component) while remaining fully compatible with the Z-machine’s blocking `get_line_of_input` routine.

---

## 1  Current Engine Behaviour
* The interpreter ultimately calls `vterm.Screen.get_line_of_input(prompt, prefilled)`.
* That method:
  1. Prints the prompt using the same ANSI pipeline used for all output.
  2. Switches the terminal to raw mode, reads keystrokes until <Enter>, echoes edits, then returns the **entire line** (a Python `str`).
* Execution **blocks** until the function returns, so from the VM’s POV input is strictly synchronous.

## 2  GUI Constraints & Goals
1. **Native console parity** – Typing in the transcript pane must behave exactly like the CLI version (line editing, history, control keys).
2. **Voice Craft Commands** – The GUI may receive an extra command string *at any time* from an async speech recogniser.
3. **Order Preservation** – If the player is halfway through typing a line, a voice command should *not* interleave chars; instead it should queue **after** the pending text command or (configurable) pre-empt it.
4. **Thread Safety** – The VM runs in its own thread; GUI events happen in Tk’s main thread.  Copies, not references, cross the boundary.

## 3  Core Abstraction: `InputQueue`
```
class InputQueue(queue.Queue):
    def enqueue(self, text: str, *, source: str = "kbd", priority: int = 0):
        """Put a full command line into the queue.
        priority: higher wins; FIFO within same priority."""
```
* **Engine Side** – `Pipe.readline()` blocks on `InputQueue.get()` and returns the string **without** the terminating newline.
* **GUI Side** –
  * Keyboard pane calls `enqueue(cmd, source="kbd", priority=0)` when the user presses <Enter>.
  * Speech module calls `enqueue(cmd, source="voice", priority=1)` immediately after recognition.

This mirrors a *single* stdin stream while still allowing priority injection.

### 3.1  Echo Strategy
Because `get_line_of_input` normally echoes user keystrokes while they are typed, an injected craft command **must also appear in the transcript** so the player sees what happened.  Two approaches:
1. **Fake-echo** – GUI writes the command line into the transcript pane before enqueuing.
2. **Engine Echo** – Pre-pend the command to the queue **with** a trailing `\n`; when the interpreter resumes, its own echo prints it (simpler, keeps parity).

We choose **Engine Echo** to reuse existing behaviour.

## 4  Keyboard Editing vs Async Injection
While the user edits a line, characters live in the InputBuffer widget, *not* in the InputQueue.  An incoming voice command therefore has two options (configurable via `config.py`):
* **`append` (default)** – Add after current user line; engine will receive it later.
* **`preempt_if_idle`** – If the user has not typed for *N* milliseconds, flush their buffer and inject the voice command first.

The implementation simply checks `inputbox.is_busy()` before choosing the priority value.

## 5  Error Handling & Cancellation
* The speech recogniser can push special tokens:
  * `#cancel` – clear the user’s current editing buffer.
  * `#undo`   – enqueue an `undo` verb (if supported by game).
* Invalid UTF-8 is discarded; we log and ignore.

## 6  Voice Integration Outline
1. **speech.py** (new) spawns `speech_recognition.Recognizer` (or Vosk / Whisper) in a background thread.
2. On each recognised phrase, call `InputQueue.enqueue(text, source="voice", priority=voice_priority)`.
3. Use a `queue.Queue` to avoid direct Tk calls from within the recogniser thread.

## 7  Race Conditions & Testing
* The only critical section is `InputQueue` itself which uses an internal lock.
* Unit tests simulate concurrent `enqueue` calls with random sleeps to guarantee order and starvation behaviour.

## 8  Configuration Snippet (`config.py`)
```python
VOICE_PRIORITY        = 1       # > keyboard (0)
VOICE_PREEMPT_TIMEOUT = 800     # ms of keyboard idle before pre-emption
```

## 9  Open Questions
* **Partial dictation** – Should voice insert *words* at cursor instead of whole lines?  (Out-of-scope for v1.)
* **Hot-word activation** – "Computer, look" versus always-on recogniser.

---
*Draft 0.1 – 2025-09-07*
