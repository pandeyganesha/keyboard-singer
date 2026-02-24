# Keyboard Singer (Background Program)

This is a **no-UI** background keyboard listener.

When you press **any key**, it plays the **next note** in the current song.

- No per-key mapping.
- Default key gate is `0.4` seconds (rapid presses inside that window are ignored).
- Notes are played on separate audio voices so new notes do **not** cut existing notes.
- Song sequence restarts automatically from the beginning after the last note.
- You can load one or more MIDI files as additional songs.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python3 keyboard_singer.py
```

Optional:

```bash
python3 keyboard_singer.py --gate 0.4 --midi song1.mid --midi song2.mid
```

Add custom inline songs:

```bash
python3 keyboard_singer.py --song "my-phrase:60,62,64,67"
```

## Notes

- The listener is global (system keyboard hook) via `pynput`.
- Stop with `Ctrl+C` in the terminal where the program is running.
- If your Linux distro needs audio packages for `simpleaudio`, install `libasound2-dev` and rebuild the venv.
