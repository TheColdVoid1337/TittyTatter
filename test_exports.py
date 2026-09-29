from pathlib import Path
from tempfile import TemporaryDirectory
import wave

import guitarpro

from audio_engine import EngineConfig
from exports import export_gp5, export_midi, export_wav
from model import BarPattern, BeatPattern
from presets import TA, TI

pattern = BarPattern(
    [
        BeatPattern("quad", [TI, TA, TI, TA]),
        BeatPattern("triplet", [TA, TI, TA]),
        BeatPattern("duplet", [TI, TA]),
        BeatPattern("beat", [TI], True),
    ],
    4,
    4,
)

with TemporaryDirectory() as temp:
    root = Path(temp)

    midi = root / "test.mid"
    export_midi(midi, pattern, 60, repeats=3, include_labels=True)
    data = midi.read_bytes()
    assert data.startswith(b"MThd")
    assert b"MTrk" in data
    assert data.count(b"Bar ") >= 3

    gp = root / "test.gp5"
    export_gp5(gp, pattern, 60, repeats=3, include_labels=True)
    parsed = guitarpro.parse(str(gp), encoding="cp1252")
    assert parsed.tempo == 60
    assert len(parsed.measureHeaders) == 3
    assert len(parsed.tracks[0].measures) == 3
    assert parsed.measureHeaders[0].timeSignature.numerator == 4
    assert parsed.measureHeaders[0].timeSignature.denominator.value == 4
    assert parsed.tracks[0].channel.instrument == 29
    assert "TI:" in parsed.instructions

    text_by_measure = []
    dead_notes = []
    for measure in parsed.tracks[0].measures:
        measure_text = []
        for beat in measure.voices[0].beats:
            if beat.text:
                measure_text.append(beat.text)
            for note in beat.notes:
                if note.type == guitarpro.NoteType.dead:
                    dead_notes.append(note)
        text_by_measure.append(measure_text)

    assert text_by_measure[0]
    assert all("[" not in text and "]" not in text for text in text_by_measure[0])
    assert text_by_measure[1] == []
    assert text_by_measure[2] == []
    assert dead_notes
    assert all(not note.effect.palmMute for note in dead_notes)

    wav_path = root / "test.wav"
    config = EngineConfig(
        bpm=60,
        ti_sound="Wood",
        ta_sound="Low tick",
        ti_enabled=True,
        ta_enabled=True,
        metronome_enabled=True,
    )
    export_wav(wav_path, pattern, config, 0.25, 44_100, 16)
    with wave.open(str(wav_path), "rb") as wav:
        assert wav.getframerate() == 44_100
        assert wav.getsampwidth() == 2
        assert wav.getnchannels() == 1
        assert wav.getnframes() > 0

print("export tests OK")
