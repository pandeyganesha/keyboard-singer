#!/usr/bin/env python3
"""Keyboard Singer: background keyboard-to-sequential-note player."""

from __future__ import annotations

import argparse
import math
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import mido
import numpy as np
import simpleaudio as sa
from pynput import keyboard

DEFAULT_GATE_SECONDS = 0.4
SAMPLE_RATE = 44100
DEFAULT_NOTE_SECONDS = 0.55


@dataclass
class Song:
    name: str
    notes: list[int]


def midi_to_hz(midi_note: int) -> float:
    return 440.0 * (2.0 ** ((midi_note - 69) / 12.0))


def synth_note(midi_note: int, seconds: float = DEFAULT_NOTE_SECONDS) -> np.ndarray:
    frequency = midi_to_hz(midi_note)
    t = np.linspace(0, seconds, int(SAMPLE_RATE * seconds), endpoint=False)

    wave_data = np.sin(2 * math.pi * frequency * t)

    attack = max(1, int(0.015 * SAMPLE_RATE))
    release = max(1, int(0.2 * SAMPLE_RATE))
    envelope = np.ones_like(wave_data)
    envelope[:attack] = np.linspace(0.0, 1.0, attack)
    envelope[-release:] *= np.linspace(1.0, 0.0, release)

    audio = (wave_data * envelope * 0.3 * 32767).astype(np.int16)
    return audio


class KeyboardSinger:
    def __init__(self, songs: list[Song], gate_seconds: float) -> None:
        if not songs:
            raise ValueError("At least one song is required")

        self.songs = songs
        self.song_index = 0
        self.note_index = 0
        self.gate_seconds = max(0.0, gate_seconds)
        self.last_trigger = 0.0
        self.lock = threading.Lock()

    @property
    def current_song(self) -> Song:
        return self.songs[self.song_index]

    def next_note(self) -> int:
        song = self.current_song
        note = song.notes[self.note_index]
        self.note_index = (self.note_index + 1) % len(song.notes)
        return note

    def restart(self) -> None:
        with self.lock:
            self.note_index = 0

    def play_note_thread(self, midi_note: int) -> None:
        data = synth_note(midi_note)
        sa.play_buffer(data, 1, 2, SAMPLE_RATE)

    def handle_press(self, _key: keyboard.KeyCode | keyboard.Key | None) -> None:
        now = time.monotonic()
        with self.lock:
            if now - self.last_trigger < self.gate_seconds:
                return
            self.last_trigger = now
            note = self.next_note()
            song = self.current_song
            current_position = self.note_index or len(song.notes)

        threading.Thread(target=self.play_note_thread, args=(note,), daemon=True).start()
        print(
            f"song={song.name!r} note={note} index={current_position}/{len(song.notes)}",
            flush=True,
        )

    def run(self) -> None:
        print("Keyboard Singer is listening globally. Press Ctrl+C to stop.")
        print(f"Current song: {self.current_song.name} ({len(self.current_song.notes)} notes)")
        print(f"Gate: {self.gate_seconds:.2f}s")
        with keyboard.Listener(on_press=self.handle_press) as listener:
            listener.join()


def load_midi_notes(midi_path: Path) -> list[int]:
    midi = mido.MidiFile(midi_path)
    notes: list[tuple[int, int]] = []

    for track in midi.tracks:
        ticks = 0
        for message in track:
            ticks += message.time
            if message.type == "note_on" and message.velocity > 0:
                notes.append((ticks, message.note))

    notes.sort(key=lambda item: item[0])
    return [note for _, note in notes]


def parse_builtin_song(raw: str) -> Song:
    name, _, body = raw.partition(":")
    if not body:
        raise argparse.ArgumentTypeError(
            "Builtin song must look like name:60,62,64"
        )

    try:
        notes = [int(item.strip()) for item in body.split(",") if item.strip()]
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"Invalid note list: {error}") from error

    if not notes:
        raise argparse.ArgumentTypeError("Song needs at least one MIDI note")
    return Song(name=name.strip() or "custom", notes=notes)


def build_default_songs() -> list[Song]:
    return [
        Song("Twinkle Fragment", [60, 60, 67, 67, 69, 69, 67, 65, 65, 64, 64, 62, 62, 60]),
        Song("Ascending C Major", [60, 62, 64, 65, 67, 69, 71, 72]),
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Play sequential notes on any keypress")
    parser.add_argument("--gate", type=float, default=DEFAULT_GATE_SECONDS, help="Seconds to ignore repeated keypresses")
    parser.add_argument("--midi", action="append", default=[], help="Path to MIDI file; can be passed multiple times")
    parser.add_argument(
        "--song",
        action="append",
        type=parse_builtin_song,
        default=[],
        help="Inline song format: name:60,62,64",
    )
    return parser


def collect_songs(midi_files: Iterable[str], extra_songs: Iterable[Song]) -> list[Song]:
    songs = build_default_songs()
    songs.extend(extra_songs)

    for midi_file in midi_files:
        midi_path = Path(midi_file)
        notes = load_midi_notes(midi_path)
        if not notes:
            raise ValueError(f"No playable notes in MIDI file: {midi_path}")
        songs.append(Song(name=f"MIDI:{midi_path.name}", notes=notes))
    return songs


def main() -> None:
    args = build_parser().parse_args()
    songs = collect_songs(args.midi, args.song)
    singer = KeyboardSinger(songs=songs, gate_seconds=args.gate)
    singer.run()


if __name__ == "__main__":
    main()
