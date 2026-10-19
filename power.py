"""Keep the laptop running with the lid closed, so the tablet buttons keep
working from a bag. Sets the current power plan's lid-close action to "Do
nothing" (powercfg, no admin needed) and puts the previous action back.

Safeguards: restored when the app quits, and when on battery at or below
LOW_BATTERY percent."""
import ctypes, json, re, subprocess, threading, time
from pathlib import Path

BACKUP = Path.home() / ".snip2tex" / "lid_action.json"
LOW_BATTERY = 15
NO_WINDOW = 0x08000000  # CREATE_NO_WINDOW

note = ""  # last thing worth telling the user (shown in the dashboard)


def _powercfg(*args):
    return subprocess.run(["powercfg", *args], capture_output=True, text=True, creationflags=NO_WINDOW)


def lid_actions():
    """(ac, dc) lid-close action: 0 nothing, 1 sleep, 2 hibernate, 3 shut down."""
    out = _powercfg("/query", "SCHEME_CURRENT", "SUB_BUTTONS", "LIDACTION").stdout
    vals = re.findall(r":\s*0x([0-9a-fA-F]+)\s*$", out, re.M)
    # the last two hex values are the current AC and DC indexes
    if len(vals) >= 2:
        return int(vals[-2], 16), int(vals[-1], 16)
    return None, None


def sleep_disabled():
    ac, dc = lid_actions()
    return ac == 0 and dc == 0


def battery():
    """(percent, on_battery) or (None, False) without a battery."""
    class Status(ctypes.Structure):
        _fields_ = [("ACLineStatus", ctypes.c_byte), ("BatteryFlag", ctypes.c_byte),
                    ("BatteryLifePercent", ctypes.c_byte), ("SystemStatusFlag", ctypes.c_byte),
                    ("BatteryLifeTime", ctypes.c_ulong), ("BatteryFullLifeTime", ctypes.c_ulong)]
    st = Status()
    if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(st)):
        return None, False
    pct = st.BatteryLifePercent & 0xFF
    return (None if pct == 255 else pct), st.ACLineStatus == 0


def _set(ac, dc):
    r1 = _powercfg("/setacvalueindex", "SCHEME_CURRENT", "SUB_BUTTONS", "LIDACTION", str(ac))
    r2 = _powercfg("/setdcvalueindex", "SCHEME_CURRENT", "SUB_BUTTONS", "LIDACTION", str(dc))
    _powercfg("/setactive", "SCHEME_CURRENT")
    return r1.returncode == 0 and r2.returncode == 0


def set_sleep_disabled(disabled):
    global note
    if disabled:
        ac, dc = lid_actions()
        if ac is None:
            note = "couldn't read the power plan's lid setting"
            return False
        if not (ac == 0 and dc == 0):
            BACKUP.write_text(json.dumps({"ac": ac, "dc": dc}))
        ok = _set(0, 0)
    else:
        try:
            old = json.loads(BACKUP.read_text())
        except (OSError, ValueError):
            old = {"ac": 1, "dc": 1}  # Windows default: sleep
        ok = _set(old["ac"], old["dc"])
    note = "" if ok else "powercfg refused the change"
    return ok and sleep_disabled() == disabled


def status():
    pct, on_batt = battery()
    return {"sleep_disabled": sleep_disabled(), "battery": pct, "on_battery": on_batt,
            "low_battery": LOW_BATTERY, "note": note}


def guard(interval=60):
    """Put the lid action back when the battery runs low while it's disabled."""
    global note

    def run():
        while True:
            try:
                pct, on_batt = battery()
                if on_batt and pct is not None and pct <= LOW_BATTERY and sleep_disabled():
                    if set_sleep_disabled(False):
                        note = f"sleep turned back on: battery at {pct}%"
            except Exception:
                pass
            time.sleep(interval)
    threading.Thread(target=run, daemon=True).start()


def restore():
    """On quit: never leave the laptop unable to sleep."""
    try:
        if sleep_disabled():
            set_sleep_disabled(False)
    except Exception:
        pass
