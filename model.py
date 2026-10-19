"""Vision model backend for snip2tex on Windows: LM Studio.

The model runs in LM Studio (GPU handled there). snip2tex scans the LM Studio
models folder (config `models_dir`) for vision models, asks LM Studio to load
the chosen one (`lms load`), and talks to its OpenAI-compatible server.
chat(prompt, image_png=None, schema=None) -> str.
"""
import base64, json, os, re, shutil, subprocess, urllib.request
from pathlib import Path

DEFAULT_MODELS_DIR = Path.home() / ".lmstudio" / "models"
LMS_PATHS = [Path.home() / ".lmstudio" / "bin" / "lms.exe", Path.home() / ".lmstudio" / "bin" / "lms"]


def strip_thinking(s):
    # Gemma 4 thinking leaks as "<|channel>thought ... <channel|>answer"
    if "<channel|>" in s:
        s = s.rsplit("<channel|>", 1)[1]
    return s.strip()


def find_models(models_dir=DEFAULT_MODELS_DIR):
    """Vision models in an LM Studio models folder (publisher/name/...). A GGUF
    model has vision when an mmproj-*.gguf sits next to it; MLX folders (if any)
    when config.json has a vision_config. Returns [{"key", "vision"}]."""
    root = Path(models_dir).expanduser()
    found = []
    for d in sorted(p for p in root.glob("*/*") if p.is_dir()):
        ggufs = list(d.glob("*.gguf"))
        weights = [g for g in ggufs if not g.name.lower().startswith("mmproj")]
        vision = any(g.name.lower().startswith("mmproj") for g in ggufs)
        cfg = d / "config.json"
        if not weights and cfg.exists():
            try:
                vision = "vision_config" in json.loads(cfg.read_text())
                weights = [cfg]
            except (OSError, ValueError):
                continue
        if weights:
            found.append({"key": f"{d.parent.name}/{d.name}", "vision": vision})
    return found


def _norm(s):
    s = s.lower().split("/")[-1]
    return re.sub(r"[-_.](gguf|mlx|\d+bit|q\d.*)$", "", s)


def lms():
    for p in LMS_PATHS:
        if p.exists():
            return str(p)
    return shutil.which("lms")


class LMStudioModel:
    def __init__(self, url, model="", models_dir=DEFAULT_MODELS_DIR):
        self.url, self.model, self.models_dir = url, model, models_dir

    def _get(self, path):
        with urllib.request.urlopen(self.url + path, timeout=3) as r:
            return json.load(r)

    def ids(self):
        return [m["id"] for m in self._get("/models")["data"] if "embed" not in m["id"]]

    def pick(self):
        """The LM Studio id for the chosen model (a folder key like
        publisher/name maps onto LM Studio's own id), or the first one loaded."""
        ids = self.ids()
        if self.model:
            if self.model in ids:
                return self.model
            want = _norm(self.model)
            for i in ids:
                if _norm(i) == want or want in _norm(i) or _norm(i) in want:
                    return i
            return self.model  # LM Studio may still load it just in time
        if not ids:
            raise RuntimeError("LM Studio has no model loaded; pick one in the dashboard")
        return ids[0]

    def load(self):
        """Ask LM Studio to load the chosen model now (instead of on the first
        press). Uses the lms CLI that ships with LM Studio. Returns a message."""
        exe = lms()
        if not (exe and self.model):
            return "lms not found; LM Studio will load the model on first use"
        r = subprocess.run([exe, "load", self.model, "-y"], capture_output=True, text=True, timeout=600)
        return (r.stdout + r.stderr).strip()[-300:]

    def chat(self, prompt, image_png=None, schema=None, temperature=0.0, max_tokens=800):
        content = [{"type": "text", "text": prompt}]
        if image_png is not None:
            content.insert(0, {"type": "image_url", "image_url": {
                "url": "data:image/png;base64," + base64.b64encode(image_png).decode()}})
        body = {"model": self.pick(), "temperature": temperature, "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": content}]}
        if schema is not None:
            body["response_format"] = {"type": "json_schema", "json_schema": {
                "name": "out", "strict": True, "schema": schema}}
        req = urllib.request.Request(self.url + "/chat/completions", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=300) as r:
            return strip_thinking(json.load(r)["choices"][0]["message"]["content"])

    def status(self):
        try:
            ids = self.ids()
            return {"backend": "lmstudio", "state": "ready" if ids or self.model else "no model",
                    "error": "", "model": self.model or "(first loaded)", "lmstudio_models": ids}
        except Exception as e:
            return {"backend": "lmstudio", "state": "LM Studio not running", "error": str(e),
                    "model": self.model}


class EngineModel:
    """The running snip2tex app's model, over its localhost-only /api/chat (for scripts)."""

    def __init__(self, url="http://127.0.0.1:8799"):
        self.url = url

    def chat(self, prompt, image_png=None, schema=None, temperature=0.0, max_tokens=800):
        body = {"prompt": prompt, "schema": schema, "temperature": temperature, "max_tokens": max_tokens,
                "image_b64": base64.b64encode(image_png).decode() if image_png is not None else None}
        req = urllib.request.Request(self.url + "/api/chat", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.load(r)["reply"]
