from __future__ import annotations

import math
import wave
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import numpy as np

from audio_engine import AudioEngine, EngineConfig
from model import BarPattern
from presets import OFF, TA, TI, grid_spec

MIDI_PPQ = 480
TI_MIDI_NOTE = 52  # E3: string 5, fret 7 in standard tuning
TA_MIDI_NOTE = 40  # E2: open low E; exported as a short muted/dead-string role
GUITAR_PROGRAM = 29  # General MIDI: Overdriven Guitar, zero-based program number


@dataclass(frozen=True)
class TimelineSlot:
    start_quarters: Fraction
    duration_quarters: Fraction
    state: str
    muted: bool
    beat_index: int
    step_index: int


def bar_quarters(pattern: BarPattern) -> Fraction:
    pattern.normalize()
    return Fraction(pattern.numerator * 4, pattern.denominator)


def iter_bar_slots(pattern: BarPattern) -> list[TimelineSlot]:
    pattern.normalize()
    beat_quarters = Fraction(4, pattern.denominator)
    coverage = pattern.coverage()
    slots: list[TimelineSlot] = []

    for beat_index, beat in enumerate(pattern.beats):
        if coverage[beat_index] != beat_index:
            continue

        spec = grid_spec(beat.grid)
        remaining_beats = pattern.numerator - beat_index
        span_beats = min(spec.span_beats, remaining_beats)
        total_quarters = beat_quarters * span_beats
        step_quarters = total_quarters / spec.steps

        for step_index in range(spec.steps):
            state = OFF if beat.muted else beat.steps[step_index]
            slots.append(
                TimelineSlot(
                    start_quarters=beat_index * beat_quarters + step_index * step_quarters,
                    duration_quarters=step_quarters,
                    state=state,
                    muted=beat.muted,
                    beat_index=beat_index,
                    step_index=step_index,
                )
            )

    slots.sort(key=lambda slot: slot.start_quarters)
    return slots


def _varlen(value: int) -> bytes:
    value = max(0, int(value))
    buffer = value & 0x7F
    out = bytearray([buffer])
    value >>= 7
    while value:
        buffer = (value & 0x7F) | 0x80
        out.insert(0, buffer)
        value >>= 7
    return bytes(out)


def _meta_text(kind: int, text: str) -> bytes:
    payload = text.encode("utf-8")
    return bytes((0xFF, kind)) + _varlen(len(payload)) + payload


def export_midi(path: str | Path, pattern: BarPattern, bpm: float) -> None:
    pattern = BarPattern.from_dict(pattern.to_dict())
    events: list[tuple[int, int, bytes]] = []

    tempo = int(round(60_000_000 / max(20.0, float(bpm))))
    tempo_data = tempo.to_bytes(3, "big")
    events.append((0, 0, b"\xFF\x51\x03" + tempo_data))

    denominator_power = int(round(math.log2(pattern.denominator)))
    events.append(
        (
            0,
            0,
            bytes((0xFF, 0x58, 0x04, pattern.numerator, denominator_power, 24, 8)),
        )
    )
    events.append((0, 0, _meta_text(0x03, "TittyTatter Guitar")))
    events.append((0, 0, _meta_text(0x01, "TI = string 5 fret 7 E3; TA = muted string 6")))
    events.append((0, 1, bytes((0xC0, GUITAR_PROGRAM))))

    for slot in iter_bar_slots(pattern):
        if slot.state not in (TI, TA):
            continue

        start_tick = int(round(float(slot.start_quarters) * MIDI_PPQ))
        slot_ticks = max(1, int(round(float(slot.duration_quarters) * MIDI_PPQ)))

        if slot.state == TI:
            note = TI_MIDI_NOTE
            velocity = 112
            duration = max(1, int(slot_ticks * 0.78))
            label = "TI"
        else:
            note = TA_MIDI_NOTE
            velocity = 74
            duration = max(1, int(slot_ticks * 0.34))
            label = "TA"

        events.append((start_tick, 1, _meta_text(0x01, label)))
        events.append((start_tick, 2, bytes((0x90, note, velocity))))
        events.append((start_tick + duration, 0, bytes((0x80, note, 0))))

    end_tick = int(round(float(bar_quarters(pattern)) * MIDI_PPQ))
    events.append((end_tick, 9, b"\xFF\x2F\x00"))
    events.sort(key=lambda item: (item[0], item[1]))

    track = bytearray()
    previous_tick = 0
    for absolute_tick, _priority, payload in events:
        track.extend(_varlen(absolute_tick - previous_tick))
        track.extend(payload)
        previous_tick = absolute_tick

    header = b"MThd" + (6).to_bytes(4, "big") + (0).to_bytes(2, "big") + (1).to_bytes(2, "big") + MIDI_PPQ.to_bytes(2, "big")
    chunk = b"MTrk" + len(track).to_bytes(4, "big") + bytes(track)
    Path(path).write_bytes(header + chunk)


def export_gp5(path: str | Path, pattern: BarPattern, bpm: float) -> None:
    try:
        import guitarpro
    except ImportError as exc:
        raise RuntimeError("PyGuitarPro is not installed. Run ./tt install.") from exc

    pattern = BarPattern.from_dict(pattern.to_dict())
    song = guitarpro.Song(title="TittyTatter", tempo=int(round(bpm)))
    song.artist = "TittyTatter"
    song.instructions = "(ТИ): string 5 fret 7 E3. ТА: dead/muted string 6."

    header = song.measureHeaders[0]
    header.timeSignature = guitarpro.TimeSignature(
        numerator=pattern.numerator,
        denominator=guitarpro.Duration(value=pattern.denominator),
    )

    track = song.tracks[0]
    track.name = "Overdriven Guitar"
    track.channel.instrument = GUITAR_PROGRAM
    track.fretCount = 24

    measure = track.measures[0]
    voice = measure.voices[0]
    voice.beats.clear()

    for slot in iter_bar_slots(pattern):
        gp_time = max(1, int(round(float(slot.duration_quarters) * guitarpro.Duration.quarterTime)))
        duration = guitarpro.Duration.fromTime(gp_time)
        beat = guitarpro.Beat(voice=voice, duration=duration)

        if slot.state == OFF:
            beat.status = guitarpro.BeatStatus.rest
            if slot.muted and slot.step_index == 0:
                beat.text = "MUTE"
        else:
            beat.status = guitarpro.BeatStatus.normal
            if slot.state == TI:
                note = guitarpro.Note(
                    beat=beat,
                    value=7,
                    velocity=guitarpro.Velocities.fortissimo,
                    string=5,
                    type=guitarpro.NoteType.normal,
                )
                beat.text = "(ТИ)"
            else:
                note = guitarpro.Note(
                    beat=beat,
                    value=0,
                    velocity=guitarpro.Velocities.mezzoPiano,
                    string=6,
                    type=guitarpro.NoteType.dead,
                )
                note.effect.palmMute = True
                beat.text = "ТА"
            beat.notes.append(note)

        voice.beats.append(beat)

    guitarpro.write(song, str(path), version=(5, 1, 0), encoding="cp1251")


def _pcm_bytes(samples: np.ndarray, bits: int) -> bytes:
    samples = np.clip(samples, -1.0, 1.0)

    if bits == 16:
        values = np.round(samples * 32767.0).astype("<i2")
        return values.tobytes()

    if bits == 24:
        values = np.round(samples * 8388607.0).astype("<i4")
        packed = values.view(np.uint8).reshape(-1, 4)[:, :3]
        return packed.tobytes()

    values = np.round(samples * 2147483647.0).astype("<i4")
    return values.tobytes()


def export_wav(
    path: str | Path,
    pattern: BarPattern,
    config: EngineConfig,
    duration_seconds: float,
    sample_rate: int = 48_000,
    bits: int = 24,
) -> None:
    pattern = BarPattern.from_dict(pattern.to_dict())
    duration_seconds = max(0.1, float(duration_seconds))
    sample_rate = int(sample_rate)
    bits = 24 if bits == 24 else (32 if bits == 32 else 16)

    renderer = AudioEngine(sample_rate=float(sample_rate))
    renderer.set_pattern(pattern)
    renderer.set_config(**config.__dict__)

    bpm = max(20.0, float(config.bpm))
    quarter_seconds = 60.0 / bpm
    total_samples = max(1, int(round(duration_seconds * sample_rate)))
    bar_seconds = float(bar_quarters(pattern)) * quarter_seconds
    bar_samples = max(1, int(round(bar_seconds * sample_rate)))
    beat_seconds = quarter_seconds * 4.0 / pattern.denominator
    coverage = pattern.coverage()

    scheduled: list[tuple[int, np.ndarray, float]] = []
    max_wave = 1

    if config.metronome_enabled:
        for beat_index in range(pattern.numerator):
            owner = coverage[beat_index]
            owner_index = beat_index if owner is None else owner
            if pattern.beats[owner_index].muted:
                continue
            name = "metro_accent" if beat_index == 0 and config.accent_first_beat else "metro"
            wave_data = renderer._sounds[name]
            offset = int(round(beat_index * beat_seconds * sample_rate))
            scheduled.append((offset, wave_data, float(config.metronome_volume)))
            max_wave = max(max_wave, len(wave_data))

    for slot in iter_bar_slots(pattern):
        if slot.state == TI and config.ti_enabled:
            wave_data = renderer.sound_wave(config.ti_sound)
            gain = float(config.ti_volume)
        elif slot.state == TA and config.ta_enabled:
            wave_data = renderer.sound_wave(config.ta_sound)
            gain = float(config.ta_volume)
        else:
            continue

        offset_seconds = float(slot.start_quarters) * quarter_seconds
        offset = int(round(offset_seconds * sample_rate))
        scheduled.append((offset, wave_data, gain))
        max_wave = max(max_wave, len(wave_data))

    sampwidth = bits // 8
    carry = np.zeros(max_wave, dtype=np.float32)
    written = 0

    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(sampwidth)
        wav.setframerate(sample_rate)

        while written < total_samples:
            current = min(bar_samples, total_samples - written)
            buffer = np.zeros(bar_samples + max_wave, dtype=np.float32)
            take = min(len(carry), len(buffer))
            buffer[:take] += carry[:take]

            for offset, wave_data, gain in scheduled:
                if offset >= len(buffer):
                    continue
                n = min(len(wave_data), len(buffer) - offset)
                buffer[offset : offset + n] += wave_data[:n] * gain

            buffer *= float(config.master_volume)
            np.clip(buffer, -0.995, 0.995, out=buffer)
            wav.writeframesraw(_pcm_bytes(buffer[:current], bits))

            if current < bar_samples:
                break

            carry = buffer[bar_samples : bar_samples + max_wave].copy()
            written += current

        wav.writeframes(b"")
