# snip2tex-windows

Lasso handwriting on a reMarkable Paper Pro, tap a button, get the result from a local vision model running in LM Studio on a Windows PC.

## Spec

| | |
|---|---|
| Tablet | reMarkable Paper Pro, firmware 3.27.3.0, developer mode, xovi |
| Computer | Windows 10/11, x64 |
| Model | Any vision model in LM Studio (GGUF with mmproj). Suggested: Gemma 4 26B-A4B or E4B |
| Model folder | LM Studio models folder (default `%USERPROFILE%\.lmstudio\models`), set in the dashboard |
| Link | USB (10.11.99.x, Windows OpenSSH client). Optional Wi-Fi via Tailscale Funnel, off by default ([WIFI.md](WIFI.md)) |
| LaTeX | tectonic (downloaded on first run), PyMuPDF |
| Math | SymPy |
| Plots | matplotlib |
| App | Tray icon, dashboard at http://localhost:8799 |
| Data | `%USERPROFILE%\.snip2tex` (config, snips, log) |

## Buttons (lasso menu)

| Button | Result |
|---|---|
| ∑ | Rendered LaTeX, inserted in place of the handwriting |
| = | Evaluated result (SymPy), popup |
| graph | Function plot, inserted below |
| ? | Short answer in a popup, or a diagram inserted below (function graph, geometry, flowchart / concept map, chart) |
| ✦ Solve steps | Worked solution, inserted below; answer in a popup |
| ✦ Check work | First wrong line, or "looks right", popup |

Popups close on tap or after 30 s.

## Install

1. LM Studio: download a vision model, start the local server (Developer tab, port 1234). Turn off "Enable Thinking" for the model for faster replies.
2. This app:

   ```powershell
   git clone https://github.com/jdtonchi/snip2tex-windows
   cd snip2tex-windows
   powershell -ExecutionPolicy Bypass -File install.ps1            # add -Startup to start with Windows
   ```

   Start menu: Snip2TeX. Dashboard: pick the models folder and model.
3. Before anything on the tablet: back up its root SSH password. It is under Settings > General > Help > Copyrights and licenses (developer mode on). Store it somewhere off the tablet (password manager). You need it to install, to get back in over SSH if the key stops working, and to recover if xovi leaves the tablet in a bad state. It changes after a factory reset.

   Tablet (USB, xovi installed with qt-resource-rebuilder, qt-command-executor, framebuffer-spy, xovi-message-broker): on first launch the dashboard shows "Set up the tablet". Plug the tablet in, enter the root password (used once to install an SSH key, not saved), confirm it is backed up, press Set up tablet. Again later: Connection card, "Set up tablet…". From a terminal instead:

   ```powershell
   uv run install_tablet.py
   ```

xovi does not survive a tablet reboot. While the tablet is plugged in, the app restarts it.

## Settings (dashboard)

| Setting | Default |
|---|---|
| LM Studio models folder | `%USERPROFILE%\.lmstudio\models` |
| Model | whatever LM Studio has loaded; picking one runs `lms load` |
| LM Studio server | http://localhost:1234/v1 |
| ∑ replaces handwriting | on |
| graph replaces handwriting | off |
| Selection padding | 5 px |
| Popup auto-hide | 30 s |
| Stay awake with lid closed | off (power plan lid action, restored on quit and at 15% battery) |
| Wi-Fi mode | off (Tailscale Funnel, token-protected, tablet endpoints only). Setup: [WIFI.md](WIFI.md) |

## Files

| Path | Role |
|---|---|
| `snip2tex.py` | HTTP server, dashboard, pipelines |
| `model.py` | LM Studio backend, models folder scan |
| `diagrams.py` | ? routing and diagram templates |
| `tutor.py` | Solve steps, Check work |
| `tablet.py` | USB watcher: restarts xovi, pushes settings |
| `remote.py` | Tailscale Funnel |
| `power.py` | Lid-closed mode (powercfg) |
| `app.py`, `install.ps1` | Tray app, Start menu shortcut |
| `tablet/` | xovi QML patch, icons, upload script |
| `install_tablet.py` | Tablet installer |
| `tests/smoke.py` | Checks without a model or tablet (CI on windows-latest) |

## License

MIT
