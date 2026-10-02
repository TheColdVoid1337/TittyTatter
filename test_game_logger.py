from __future__ import annotations

import json
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory

from game_logger import GameLogSession


with TemporaryDirectory() as temp:
    root = Path(temp)
    logs = root / "logs"

    disabled = GameLogSession(False, "test", logs)
    disabled.start({"disabled": True})
    assert not logs.exists()

    session = GameLogSession(True, "test", logs)
    session.start({"bpm": 60, "pattern": {"name": "demo"}})
    assert session.active
    raw = session.raw_path
    assert raw is not None and raw.exists()

    session.log("input", state="ti", stream_time=1.25)
    archive = session.finish("test_complete", {"score": 100})
    assert archive is not None and archive.exists()
    assert archive.name.endswith(".tar.gz")
    assert raw is not None and not raw.exists()

    with tarfile.open(archive, "r:gz") as tar:
        names = tar.getnames()
        assert names == [raw.name]
        extracted = tar.extractfile(names[0])
        assert extracted is not None
        lines = [json.loads(line) for line in extracted.read().decode("utf-8").splitlines()]

    assert [line["event"] for line in lines] == [
        "session_start",
        "input",
        "session_end",
    ]
    assert lines[1]["state"] == "ti"
    assert lines[-1]["summary"]["score"] == 100

print("game log tests OK")
