"""snip2tex tray app for Windows: runs the server (snip2tex.py) with a ∑ in the
notification area. The dashboard opens in the browser. Started by the Start
menu shortcut that install.ps1 makes (pythonw, no console).

    python app.py                 run
    python app.py --icon PATH     write the ∑ icon (.ico) for the shortcut
"""
import os, subprocess, sys, threading, urllib.request, webbrowser
from pathlib import Path

# pythonw has no console; without this every ssh/powercfg/tectonic call
# would flash a console window
if os.name == "nt":
    _popen_init = subprocess.Popen.__init__

    def _no_window(self, *a, **kw):
        kw.setdefault("creationflags", 0x08000000)  # CREATE_NO_WINDOW
        _popen_init(self, *a, **kw)
    subprocess.Popen.__init__ = _no_window

from PIL import Image, ImageDraw

SIGMA = [(10, 6), (38, 6), (38, 14), (35, 14), (35, 9), (15.6, 9), (28.1, 24), (15.6, 39), (35, 39),
         (35, 34), (38, 34), (38, 42), (10, 42), (10, 40.4), (24.2, 24), (10, 7.6)]
LOG = Path.home() / ".snip2tex" / "app.log"


def sigma_image(size=64, fg="white", bg=(40, 40, 40, 255)):
    # light glyph on a dark tile: readable on light and dark taskbars
    im = Image.new("RGBA", (size, size), bg)
    k = size / 48
    ImageDraw.Draw(im).polygon([(x * k, y * k) for x, y in SIGMA], fill=fg)
    return im


def write_icon(path):
    sigma_image(256, fg="black", bg="white").save(path, sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])


def already_running(port):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/ping", timeout=1):
            return True
    except OSError:
        return False


def main():
    LOG.parent.mkdir(parents=True, exist_ok=True)
    if sys.stdout is None or "pythonw" in Path(sys.executable).name.lower():
        sys.stdout = sys.stderr = open(LOG, "a", buffering=1, encoding="utf-8")

    import snip2tex
    port = snip2tex.config["port"]
    url = f"http://localhost:{port}/"
    if already_running(port):
        # second launch (Start menu again): just show the dashboard
        webbrowser.open(url)
        return

    import pystray
    import power

    snip2tex.show_hook = lambda: webbrowser.open(url)
    snip2tex.start(open_browser=True)

    def model_line(_):
        m = snip2tex.llm().status()
        progress = list(snip2tex.deps.progress.values())
        return progress[0] if progress else f"Model: {m['state']}" + (f" · {m['model']}" if m.get("model") else "")

    def tablet_line(_):
        return f"Tablet: {snip2tex.watcher.status()['state']}"

    def toggle_lid(icon, _):
        threading.Thread(target=power.set_sleep_disabled, args=(not power.sleep_disabled(),), daemon=True).start()

    def quit_app(icon, _):
        power.restore()
        icon.stop()
        os._exit(0)

    menu = pystray.Menu(
        pystray.MenuItem(model_line, None, enabled=False),
        pystray.MenuItem(tablet_line, None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Open Snip2TeX", lambda icon, _: webbrowser.open(url), default=True),
        pystray.MenuItem("Reload Model", lambda icon, _: snip2tex.load_model()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Stay Awake with Lid Closed", toggle_lid, checked=lambda _: power.sleep_disabled()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit Snip2TeX", quit_app),
    )
    icon = pystray.Icon("snip2tex", sigma_image(), "Snip2TeX", menu)

    def refresh():
        # the status lines are computed when the menu is rebuilt
        import time
        while True:
            time.sleep(3)
            try:
                icon.update_menu()
            except Exception:
                pass
    threading.Thread(target=refresh, daemon=True).start()
    icon.run()


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--icon":
        write_icon(sys.argv[2])
    else:
        main()
