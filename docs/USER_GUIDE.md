# User guide

## Running from WSL as a native Windows application

The supported development workflow is:

- repository commands are issued from WSL;
- Git runs in WSL;
- TittyTatter itself runs with the Windows Python virtual environment;
- PySide6 and sounddevice therefore use native Windows GUI/audio.

Project paths:

```text
Windows: F:\_PROJECT\TittyTatter
WSL:     /mnt/f/_PROJECT/TittyTatter
```

First setup:

```bash
cd /mnt/f/_PROJECT/TittyTatter
./tt install
./tt doctor
```

Normal use:

```bash
./tt run
```

Useful development commands:

```bash
./tt test
./tt check
./tt pip list
./tt python
./tt update
```

There is no need to run `source .venv/bin/activate`. That would refer to a Linux virtual environment, while TittyTatter deliberately uses the Windows interpreter at `.venv/Scripts/python.exe`.

## Building a bar

A TittyTatter exercise is a four-beat 4/4 bar.

For each beat:

1. choose **16ths** or **triplet**;
2. select a built-in pattern or edit the subdivisions manually;
3. set each subdivision to **TI**, **TA**, or silence.

Different beats may use different subdivision types.

## TI and TA

TI and TA are intentionally abstract rhythm roles.

A common practice setup is:

- **TI**: clap-like sound;
- **TA**: sound disabled;
- metronome: enabled.

This makes the target hits stand out while the meter remains audible.

## A/B practice

The A/B builder is intended for rapid combination work.

Typical shapes include:

- A B A B
- A B B A
- A A B B

A and B may use different subdivision types.

## Practice ramps

Useful modes include:

- full 4/4 loop;
- 1/4 → 2/4 → 3/4 → 4/4;
- 2/4 → 4/4.

The number of bars per stage should be configurable.

## Tempo

BPM can be changed while playback is running.

Recommended controls:

- direct BPM value;
- slider;
- ±1 BPM;
- ±5 BPM;
- tap tempo.

The tempo trainer can increase BPM automatically after a chosen number of bars until a target BPM is reached.

## Sessions

A session should preserve at minimum:

- BPM;
- four-beat pattern;
- subdivision type per beat;
- practice mode;
- stage length;
- sound configuration;
- trainer configuration.

Session files are user data and are not part of the repository.
