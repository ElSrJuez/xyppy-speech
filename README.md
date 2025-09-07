# zyppy-speech – Infocom's Z-Machine in Python (speech-enabled fork of **xyppy**)

### Usage:

* `python -m zyppy FILE_OR_URL` (in module/dev mode)
* `python zyppy.py FILE_OR_URL` (in single file mode)
* `zyppy FILE_OR_URL` (in installed mode)
* run `./build-single-file-version.py` to get that handy single-file zyppy.py
* run `python -m pip install .` to install zyppy

### Quick Look:

![Color Support](https://github.com/theinternetftw/xyppy/raw/master/screens/color_support.gif)

More screens can be found on [their dedicated page.](https://github.com/theinternetftw/xyppy/tree/master/screens)

### Features:

* Supports all modern Z-machine games (versions 2, 3, 4, 5, 7, 8, and zblorb files)
* Everything, including the build system, requires nothing but modern python 3
* Quetzal support, so saves are portable to and from many other zmachine apps
* Healthy color terminal support on windows and linux
* Run games straight from the web by passing in a URL
* A major focus was "feel." Lines scroll in like it's the 80s.

### "Features":

* Doesn't support mid-input interrupts
* No character font
* You can turn slow scroll mode off with --no-slow-scroll (you monster)
* Not fast enough to play really unoptimized Inform 7 games (so far I've found 2 offenders)

## GUI Roadmap
A Tkinter-based desktop interface is in active design.  See [`gui/console_abstract.md`](gui/console_abstract.md) for architecture and guiding principles.

## Runtime State Introspection
The interpreter exposes read-only helpers for player, inventory and room data.  Details: [`state/state_helper.md`](state/state_helper.md).

## Unified Input Layer
Keyboard commands and asynchronous voice "craft" commands share a common queue.  Design notes in [`input/input_abstract.md`](input/input_abstract.md).

### TODO:
* More features, implement the last few bits of the spec
* Config file, so you don't have to set an alias or keep passing args
