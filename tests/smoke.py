"""Smoke test without a model or tablet: the server answers, uploads decode,
LaTeX renders (tectonic + PyMuPDF), graphs and diagram templates draw, the
models folder scan works, and the Windows-only helpers run.

    uv run python tests/smoke.py
"""
import base64, gzip, io, json, os, sys, tempfile, threading, urllib.error, urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PIL import Image

import diagrams, model, snip2tex, tutor


def check(name, fn):
    try:
        out = fn()
        print(f"ok   {name}" + (f": {out}" if out else ""), flush=True)
    except Exception as e:
        print(f"FAIL {name}: {type(e).__name__}: {e}", flush=True)
        check.failed += 1
check.failed = 0


def png_ok(b):
    im = Image.open(io.BytesIO(b))
    assert im.width > 10 and im.height > 10, im.size
    return f"{im.width}x{im.height}"


def server():
    srv = ThreadingHTTPServer(("127.0.0.1", 18799), snip2tex.H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    with urllib.request.urlopen("http://127.0.0.1:18799/ping", timeout=5) as r:
        assert json.load(r)["ok"]
    with urllib.request.urlopen("http://127.0.0.1:18799/", timeout=5) as r:
        assert b"snip2tex" in r.read()


def remote_listener():
    snip2tex.config.update(remote_token="t0k3n", remote_enabled=True)
    srv = ThreadingHTTPServer(("127.0.0.1", 18798), snip2tex.RemoteH)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    for path, data in (("/", None), ("/api/quit", b"{}"), ("/ask", b"x")):
        try:
            urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:18798" + path, data=data), timeout=5)
            raise AssertionError(f"{path} reachable without token")
        except urllib.error.HTTPError as e:
            assert e.code == 404, e.code


def framebuffer():
    # a 64x40 BGRA "screen" with a black bar, as snip.sh uploads it (gzip + base64)
    w, h = 64, 40
    im = Image.new("RGBA", (w, h), "white")
    for x in range(10, 50):
        for y in range(18, 22):
            im.putpixel((x, y), (0, 0, 0, 255))
    raw = im.tobytes("raw", "BGRA")
    body = base64.b64encode(gzip.compress(raw))
    data = gzip.decompress(base64.b64decode(body))  # what H.read_upload does
    return png_ok(snip2tex.framebuffer_to_png(data, {"stride": w * 4, "rows": h, "x": 0, "w": w, "rot": -90}))


def models_folder():
    with tempfile.TemporaryDirectory() as d:
        v = Path(d, "lmstudio-community", "gemma-4-26B-A4B-it-GGUF")
        v.mkdir(parents=True)
        (v / "gemma-4-26B-A4B-it-Q4_K_M.gguf").write_bytes(b"x")
        (v / "mmproj-gemma-4-26B-A4B-it-f16.gguf").write_bytes(b"x")
        t = Path(d, "someone", "text-only-GGUF")
        t.mkdir(parents=True)
        (t / "model.gguf").write_bytes(b"x")
        found = model.find_models(d)
        assert {"key": "lmstudio-community/gemma-4-26B-A4B-it-GGUF", "vision": True} in found, found
        assert {"key": "someone/text-only-GGUF", "vision": False} in found, found
        return found


def windows_only():
    if os.name != "nt":
        return "skipped (not Windows)"
    import power
    st = power.status()
    ips = snip2tex.local_ips()
    return f"lid {power.lid_actions()}, battery {st['battery']}, {len(ips)} addresses"


check("server", server)
check("remote listener needs token", remote_listener)


def setup_api():
    with urllib.request.urlopen("http://127.0.0.1:18799/api/setup", timeout=10) as r:
        st = json.load(r)
    assert {"needed", "reachable", "running", "log"} <= set(st), st
    return f"needed={st['needed']}, tablet reachable={st['reachable']}"


check("setup API", setup_api)
check("framebuffer upload", framebuffer)
check("LaTeX render", lambda: png_ok(snip2tex.render_png(r"\[ \frac{a}{b} + \sqrt{x^2} \]")))
check("solution render", lambda: png_ok(snip2tex.render_png(tutor.solution_latex(
    {"steps": [{"why": "subtract 3", "math": "2x = 4"}], "answer": "x = 2"}))))
check("graph", lambda: png_ok(snip2tex.render_graph({"title": "", "curves": [{"expr": "x**2", "label": ""}],
    "implicit": [], "points": [], "vlines": [], "xmin": -3, "xmax": 3, "ymin": None, "ymax": None})))
check("flowchart", lambda: png_ok(diagrams.render_flowchart({"title": "Cycle", "direction": "right",
    "nodes": [{"id": str(i), "label": f"Step {i}", "shape": "rounded"} for i in range(4)],
    "edges": [{"from": str(i), "to": str((i + 1) % 4), "label": ""} for i in range(4)]}, 100)[0]))
check("geometry", lambda: diagrams.render_geometry({"figure": "triangle", "a": 3, "b": 4, "c": None, "A": None, "B": None,
    "C": None, "right_angle_at": "C", "radius": None, "width": None, "height": None, "sides": None, "side": None,
    "find": ["c"]}, 100)[1])
check("evaluate", lambda: snip2tex.compute(r"\frac{1}{2} + \frac{1}{3}")[0])
check("models folder scan", models_folder)
check("Windows helpers", windows_only)
sys.exit(1 if check.failed else 0)
