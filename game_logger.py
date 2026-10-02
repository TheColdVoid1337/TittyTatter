from __future__ import annotations

import json
import platform
import sys
import tarfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_LOGS_DIR = Path(__file__).with_name("logs")


class GameLogSession:
    """Optional per-game JSONL diagnostic logger.

    A raw .jsonl file exists only while the game is active. On finish it is
    packed into a uniquely named .tar.gz archive and the raw file is removed.
    Logging failures are intentionally non-fatal to gameplay.
    """

    def __init__(
        self,
        enabled: bool,
        app_version: str,
        logs_dir: Path | None = None,
    ) -> None:
        self.enabled = bool(enabled)
        self.app_version = str(app_version)
        self.logs_dir = Path(logs_dir) if logs_dir is not None else DEFAULT_LOGS_DIR
        self.started_perf = 0.0
        self.raw_path: Path | None = None
        self.archive_path: Path | None = None
        self._handle = None
        self._failed = False

    @property
    def active(self) -> bool:
        return bool(self.enabled and self._handle is not None and not self._failed)

    def start(self, metadata: dict[str, Any]) -> None:
        if not self.enabled or self.active:
            return
        try:
            self.logs_dir.mkdir(parents=True, exist_ok=True)
            now = datetime.now().astimezone()
            stem = "game_" + now.strftime("%Y-%m-%d_%H-%M-%S_%f")
            raw = self.logs_dir / f"{stem}.jsonl"
            suffix = 1
            while raw.exists() or raw.with_suffix(".tar.gz").exists():
                raw = self.logs_dir / f"{stem}_{suffix:02d}.jsonl"
                suffix += 1

            self.raw_path = raw
            self.started_perf = time.perf_counter()
            self._handle = raw.open("w", encoding="utf-8", buffering=1)
            self.log(
                "session_start",
                app_version=self.app_version,
                created_at=now.isoformat(),
                python=sys.version,
                platform=platform.platform(),
                argv=list(sys.argv),
                metadata=metadata,
            )
        except Exception:
            self._failed = True
            self._safe_close()

    def log(self, event: str, **data: Any) -> None:
        if not self.active:
            return
        try:
            now = datetime.now().astimezone()
            record = {
                "event": str(event),
                "wall_time": now.isoformat(),
                "elapsed_ms": round((time.perf_counter() - self.started_perf) * 1000.0, 3),
            }
            record.update(data)
            self._handle.write(
                json.dumps(record, ensure_ascii=False, separators=(",", ":"), default=str)
                + "\n"
            )
        except Exception:
            self._failed = True
            self._safe_close()

    def finish(self, reason: str, summary: dict[str, Any] | None = None) -> Path | None:
        if not self.enabled:
            return None

        if self.active:
            self.log("session_end", reason=str(reason), summary=summary or {})
        self._safe_close()

        raw = self.raw_path
        if raw is None or not raw.exists():
            return self.archive_path

        try:
            archive = Path(str(raw.with_suffix("")) + ".tar.gz")
            with tarfile.open(archive, "w:gz") as tar:
                tar.add(raw, arcname=raw.name)
            raw.unlink()
            self.archive_path = archive
            return archive
        except Exception:
            # Preserve the raw JSONL if compression failed: losing diagnostics
            # is worse than temporarily using more disk space.
            return None

    def _safe_close(self) -> None:
        handle = self._handle
        self._handle = None
        if handle is not None:
            try:
                handle.flush()
                handle.close()
            except Exception:
                pass
