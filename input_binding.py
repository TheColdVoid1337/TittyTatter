from __future__ import annotations

# Windows Set-1 scan codes for common alphanumeric/game keys. TittyTatter is a
# Windows-first app, and these labels let legacy F/J bindings migrate to
# physical-key bindings that no longer depend on the active keyboard layout.
_SCAN_LABELS = {
    2: "1", 3: "2", 4: "3", 5: "4", 6: "5", 7: "6", 8: "7", 9: "8", 10: "9", 11: "0",
    16: "Q", 17: "W", 18: "E", 19: "R", 20: "T", 21: "Y", 22: "U", 23: "I", 24: "O", 25: "P",
    30: "A", 31: "S", 32: "D", 33: "F", 34: "G", 35: "H", 36: "J", 37: "K", 38: "L",
    44: "Z", 45: "X", 46: "C", 47: "V", 48: "B", 49: "N", 50: "M",
    57: "Space",
    59: "F1", 60: "F2", 61: "F3", 62: "F4", 63: "F5", 64: "F6",
    65: "F7", 66: "F8", 67: "F9", 68: "F10", 87: "F11", 88: "F12",
}
_LABEL_TO_SCAN = {label.upper(): scan for scan, label in _SCAN_LABELS.items()}


def scan_binding(scan_code: int, fallback_label: str = "") -> str:
    scan = max(0, int(scan_code))
    if scan <= 0:
        return ""
    label = _SCAN_LABELS.get(scan) or str(fallback_label or "").strip().upper() or f"Scan {scan}"
    return f"scan:{scan}:{label}"


def normalize_binding(binding: str) -> str:
    value = str(binding or "").strip()
    if not value:
        return ""

    lower = value.lower()
    if lower.startswith("mouse:"):
        try:
            return f"mouse:{max(1, int(value.split(':', 1)[1]))}"
        except Exception:
            return ""

    if lower.startswith("scan:"):
        parts = value.split(":", 2)
        try:
            scan = int(parts[1])
        except Exception:
            return ""
        fallback = parts[2] if len(parts) > 2 else ""
        return scan_binding(scan, fallback)

    if lower.startswith("key:"):
        label = value.split(":", 1)[1].strip().upper()
    elif ":" not in value:
        # 0.0.3 and early post-release builds stored plain QKeySequence text.
        label = value.upper()
    else:
        return value

    if not label:
        return ""

    scan = _LABEL_TO_SCAN.get(label)
    if scan is not None:
        return scan_binding(scan, label)

    # Uncommon legacy keys keep their logical fallback. New captures use scan
    # codes whenever Qt exposes a native scan code.
    return f"key:{label}"


def binding_identity(binding: str) -> str:
    value = normalize_binding(binding)
    lower = value.lower()

    if lower.startswith("scan:"):
        parts = value.split(":", 2)
        return f"scan:{parts[1]}" if len(parts) >= 2 else ""

    if lower.startswith("mouse:"):
        return lower

    if lower.startswith("key:"):
        return f"key:{value.split(':', 1)[1].upper()}"

    return value.lower()


def binding_display(binding: str) -> str:
    value = normalize_binding(binding)
    lower = value.lower()

    if lower.startswith("mouse:"):
        try:
            return f"Mouse {int(value.split(':', 1)[1])}"
        except Exception:
            return value

    if lower.startswith("scan:"):
        parts = value.split(":", 2)
        try:
            scan = int(parts[1])
        except Exception:
            return value
        if len(parts) > 2 and parts[2]:
            return parts[2]
        return _SCAN_LABELS.get(scan, f"Scan {scan}")

    if lower.startswith("key:"):
        return value.split(":", 1)[1]

    return value
