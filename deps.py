"""Fetch what snip2tex needs on first run: the tectonic LaTeX engine
(standalone binary). The model comes from LM Studio."""
import os, shutil, tempfile, threading, urllib.request, zipfile
from pathlib import Path

BIN = Path.home() / ".snip2tex" / "bin"
TECTONIC_URL = ("https://github.com/tectonic-typesetting/tectonic/releases/download/"
                "tectonic%400.17.0/tectonic-0.17.0-x86_64-pc-windows-msvc.zip")
EXE = "tectonic.exe" if os.name == "nt" else "tectonic"

# what the dashboard and tray show while something is being fetched
progress = {}
_lock = threading.Lock()


def _set(key, text):
    with _lock:
        if text is None:
            progress.pop(key, None)
        else:
            progress[key] = text


def find_tectonic():
    for p in (shutil.which("tectonic"), BIN / EXE):
        if p and os.path.exists(p):
            return str(p)
    return None


def ensure_tectonic():
    """Return a tectonic path, downloading the official binary if there is none."""
    found = find_tectonic()
    if found:
        return found
    _set("tectonic", "downloading LaTeX engine…")
    try:
        BIN.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as d:
            z = Path(d) / "t.zip"
            urllib.request.urlretrieve(TECTONIC_URL, z)
            with zipfile.ZipFile(z) as f:
                name = next(n for n in f.namelist() if Path(n).name == "tectonic.exe")
                f.extract(name, d)
                shutil.move(str(Path(d) / name), BIN / EXE)
        return str(BIN / EXE)
    finally:
        _set("tectonic", None)
