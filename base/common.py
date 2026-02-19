import queue
from datetime import datetime
import os
import sys
import platform
import json
import urllib.request
import time

import pyautogui
from .tools import resource_path

# ========== LOGGING ==========

log_queue = queue.Queue()
stats_queue = queue.Queue()


def log(level: str, msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    icons = {
        "INFO": "ℹ️ ",
        "STATE": "⏱️ ",
        "ACTION": "🎯 ",
        "DEBUG": "🔍 ",
        "WARN": "⚠️ ",
        "ERROR": "🛑 ",
    }
    icon = icons.get(level, "")
    full = f"[{ts}] [{level:5}] {icon}{msg}"

    # Print to console, but be robust to non-UTF-8 terminals (PyInstaller + cp1252)
    try:
        print(full)
    except UnicodeEncodeError:
        # Strip non-encodable chars and print a degraded version
        safe = full.encode("ascii", "ignore").decode("ascii", "ignore")
        print(safe)

    # Internal queue keeps full Unicode (GUI log is fine)
    log_queue.put((level.upper(), full + "\n"))

# virtual gamepad (optional, for CHIAKI4DECK mode)
vg = None

def get_vgamepad():
    global vg
    if vg is not None:
        return vg
    try:
        import vgamepad as _vg
        vg = _vg
        return vg
    except Exception as e:
        log("ERROR", f"vgamepad import failed: {e}")
        return None

def check_chiaki4deck_env() -> str:
    """
    Checks whether Chiaki4Deck environment is ready.

    Returns:
        "ok"             -> vgamepad + ViGEmBus ready
        "no_vgamepad"    -> vgamepad package missing
        "no_driver"      -> ViGEmBus driver missing / not running
        "unsupported_os" -> not Windows
    """
    if platform.system() != "Windows":
        return "unsupported_os"

    # First: is the *package* there?
    try:
        import vgamepad as vg_mod
    except ImportError as e:
        log("ERROR", f"'vgamepad' is not installed: {e}")
        return "no_vgamepad"
    except Exception as e:
        # Non-ImportError during import is almost always ViGEmBus problems
        log("ERROR", f"'vgamepad' import failed (likely ViGEmBus missing): {e}")
        return "no_driver"

    # Second: can we actually create a pad? (tests the bus/driver)
    try:
        pad = vg_mod.VDS4Gamepad()
        del pad
        return "ok"
    except Exception as e:
        log("ERROR", f"ViGEmBus check failed: {e}")
        return "no_driver"

# ---- App metadata / updates ----
APP_VERSION = "v1.0.3a"
GITHUB_REPO = "veerack/ievr-automatch"
APP_RELEASE_URL = f"https://github.com/{GITHUB_REPO}/releases"
APP_LATEST_RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

# ---------------- SETTINGS IMPORT (DEV + FROZEN) ----------------

def _load_settings_module():
    """
    Load settings, preferring the external base/settings.py
    when running as a PyInstaller exe.
    """
    import importlib.util

    # If running as PyInstaller exe, look for ./base/settings.py
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        base_dir = os.path.join(exe_dir, "base")
        settings_path = os.path.join(base_dir, "settings.py")

        if os.path.exists(settings_path):
            spec = importlib.util.spec_from_file_location(
                "user_settings", settings_path
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module

        # Fallback to bundled defaults if external file missing
        from base import settings as module
        return module

    # --- normal dev / non-frozen ---
    try:
        from base import settings as module
    except ImportError:
        import settings as module
    return module


settings = _load_settings_module()
cfg = settings

def reload_settings():
    """
    Reload the settings module (dev or frozen) and update `cfg`.
    Uses the already-imported `settings` object, so it works
    whether it's `base.settings` or plain `settings`.
    """
    global settings, cfg
    settings = _load_settings_module()
    cfg = settings

# ========== GLOBAL CONFIG FROM settings.py ==========

GAME_WINDOW_TITLE = getattr(cfg, "GAME_WINDOW_TITLE", "Inazuma Eleven: Victory Road")
AUTO_MODE_KEY = getattr(cfg, "AUTO_MODE_KEY", "u")
CHIAKI4DECK = getattr(cfg, "CHIAKI4DECK", False)

DELAY_BEFORE_START = getattr(cfg, "DELAY_BEFORE_START", 5.0)
FIRST_WAIT = getattr(cfg, "FIRST_WAIT", 15.0)
SECOND_WAIT = getattr(cfg, "SECOND_WAIT", 80.0)
MATCH_DURATION = getattr(cfg, "MATCH_DURATION", 780.0)
POST_MATCH_CLICKS = getattr(cfg, "POST_MATCH_CLICKS", 20)
POST_MATCH_CLICK_INTERVAL = getattr(cfg, "POST_MATCH_CLICK_INTERVAL", 0.3)
SEARCH_CHECK_INTERVAL = getattr(cfg, "SEARCH_CHECK_INTERVAL", 20.0)

PLAY_BUTTON_OFFSET = getattr(cfg, "PLAY_BUTTON_OFFSET", (292, 247))
ANNUL_PIXEL_OFFSET = getattr(cfg, "ANNUL_PIXEL_OFFSET", (499, 375))
ANNUL_PIXEL_COLOR = getattr(cfg, "ANNUL_PIXEL_COLOR", (250, 253, 254))

PLAY_BUTTON_OFFSET_CHIAKI = getattr(cfg, "PLAY_BUTTON_OFFSET_CHIAKI", (358, 263))
ANNUL_PIXEL_OFFSET_CHIAKI = getattr(cfg, "ANNUL_PIXEL_OFFSET_CHIAKI", (475, 384))
ANNUL_PIXEL_COLOR_CHIAKI = getattr(cfg, "ANNUL_PIXEL_COLOR_CHIAKI", (0, 174, 206))

END_BUTTON_OFFSET = getattr(cfg, "END_BUTTON_OFFSET", (60, 57))
END_BUTTON_COLOR = getattr(cfg, "END_BUTTON_COLOR", (172, 158, 48))

LVL_75_PLUS = getattr(cfg, "LVL_75_PLUS", False)
MATCH_TIMEOUT_MARGIN = getattr(cfg, "MATCH_TIMEOUT_MARGIN", 120.0)

MAX_MATCHES_PER_RUN = getattr(cfg, "MAX_MATCHES_PER_RUN", None)
MAX_RUNTIME_MINUTES = getattr(cfg, "MAX_RUNTIME_MINUTES", None)

PLAY_BUTTON_IDLE_COLOR = getattr(cfg, "PLAY_BUTTON_IDLE_COLOR", None)

RAMEN_INITIAL_DELAY = getattr(cfg, "RAMEN_INITIAL_DELAY", 10.0)
RAMEN_FIRST_ENTER_COUNT = getattr(cfg, "RAMEN_FIRST_ENTER_COUNT", 4)
RAMEN_FIRST_ENTER_DELAY = getattr(cfg, "RAMEN_FIRST_ENTER_DELAY", 1.0)
RAMEN_AFTER_FIRST_WAIT = getattr(cfg, "RAMEN_AFTER_FIRST_WAIT", 5.0)

RAMEN_W_MIN = getattr(cfg, "RAMEN_W_MIN", 7)
RAMEN_W_MAX = getattr(cfg, "RAMEN_W_MAX", 8)
RAMEN_W_DELAY = getattr(cfg, "RAMEN_W_DELAY", 1.5)

RAMEN_LONG_WAIT_MIN = getattr(cfg, "RAMEN_LONG_WAIT_MIN", 15.0)
RAMEN_LONG_WAIT_MAX = getattr(cfg, "RAMEN_LONG_WAIT_MAX", 16.0)

RAMEN_FINAL_ENTER_COUNT = getattr(cfg, "RAMEN_FINAL_ENTER_COUNT", 2)
RAMEN_FINAL_ENTER_DELAY = getattr(cfg, "RAMEN_FINAL_ENTER_DELAY", 1.5)
RAMEN_AFTER_FINAL_WAIT = getattr(cfg, "RAMEN_AFTER_FINAL_WAIT", 5.0)

# ================= PINK BEANS TRAINER =================

PINK_INITIAL_DELAY = getattr(cfg, "PINK_INITIAL_DELAY", 5.0)

PINK_ENTER1_DELAY = getattr(cfg, "PINK_ENTER1_DELAY", 1.2)
PINK_ENTER2_DELAY = getattr(cfg, "PINK_ENTER2_DELAY", 0.7)
PINK_UP_DELAY = getattr(cfg, "PINK_UP_DELAY", 0.1)
PINK_ENTER3_DELAY = getattr(cfg, "PINK_ENTER3_DELAY", 0.2)
PINK_ENTER4_DELAY = getattr(cfg, "PINK_ENTER4_DELAY", 7.0)

PINK_ESC_AFTER_DELAY = getattr(cfg, "PINK_ESC_AFTER_DELAY", 0.1)
PINK_V_AFTER_DELAY = getattr(cfg, "PINK_V_AFTER_DELAY", 2.0)
PINK_V_HOLD_DURATION = getattr(cfg, "PINK_V_HOLD_DURATION", 2.0)
PINK_AFTER_HOLD_DELAY = getattr(cfg, "PINK_AFTER_HOLD_DELAY", 3.0)

PINK_DOWN_DELAY = getattr(cfg, "PINK_DOWN_DELAY", 0.5)
PINK_FINAL_ENTER_DELAY = getattr(cfg, "PINK_FINAL_ENTER_DELAY", 4.0)

# ================= BLUE BEANS TRAINER =================

BLUE_INITIAL_DELAY = getattr(cfg, "BLUE_INITIAL_DELAY", 5.0)

BLUE_ENTER1_DELAY = getattr(cfg, "BLUE_ENTER1_DELAY", 1.2)
BLUE_ENTER2_DELAY = getattr(cfg, "BLUE_ENTER2_DELAY", 0.7)
BLUE_UP_DELAY = getattr(cfg, "BLUE_UP_DELAY", 0.3)
BLUE_ENTER3_DELAY = getattr(cfg, "BLUE_ENTER3_DELAY", 0.3)
BLUE_ENTER4_DELAY = getattr(cfg, "BLUE_ENTER4_DELAY", 7.0)

BLUE_A1_DELAY = getattr(cfg, "BLUE_A1_DELAY", 4.5)
BLUE_S1_DELAY = getattr(cfg, "BLUE_S1_DELAY", 8.5)
BLUE_A2_DELAY = getattr(cfg, "BLUE_A2_DELAY", 4.0)
BLUE_S2_DELAY = getattr(cfg, "BLUE_S2_DELAY", 10.0)
BLUE_A3_DELAY = getattr(cfg, "BLUE_A3_DELAY", 3.0)
BLUE_S3_DELAY = getattr(cfg, "BLUE_S3_DELAY", 5.0)
BLUE_A4_DELAY = getattr(cfg, "BLUE_A4_DELAY", 12.0)

BLUE_ENTER5_DELAY = getattr(cfg, "BLUE_ENTER5_DELAY", 1.5)
BLUE_COOLDOWN_DELAY = getattr(cfg, "BLUE_COOLDOWN_DELAY", 70.0)

def get_play_button_offset():
    """Return the correct Ranked Match button offset for current mode."""
    if CHIAKI4DECK:
        return PLAY_BUTTON_OFFSET_CHIAKI
    return PLAY_BUTTON_OFFSET


def get_annul_pixel():
    """Return (offset, color) for the search CANCEL button for current mode."""
    if CHIAKI4DECK:
        return ANNUL_PIXEL_OFFSET_CHIAKI, ANNUL_PIXEL_COLOR_CHIAKI
    return ANNUL_PIXEL_OFFSET, ANNUL_PIXEL_COLOR


def get_end_button():
    """
    Return (offset, color) for the 'Next' / end-of-match button
    for current mode. You can later add *_CHIAKI values in settings
    if needed.
    """
    offset = getattr(cfg, "END_BUTTON_OFFSET_CHIAKI", END_BUTTON_OFFSET)
    color  = getattr(cfg, "END_BUTTON_COLOR_CHIAKI", END_BUTTON_COLOR)
    if CHIAKI4DECK:
        return offset, color
    return END_BUTTON_OFFSET, END_BUTTON_COLOR

# ========== PYAUTOGUI GLOBALS ==========

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.05

# ========== INPUT BACKEND (KB/MOUSE vs VIRTUAL GAMEPAD) ==========

class InputBackend:
    """
    Unified input layer.
    - Default: mouse/keyboard via pyautogui
    - CHIAKI4DECK: virtual controller via vgamepad (DS4 preferred)
    """

    def __init__(self, use_chiaki4deck: bool):
        self.mode = "kbmouse"
        self.gamepad = None
        self.pad_type = "none"
        self.vg_mod = None

        # Logical → backend constant
        self.button_map = {}  # e.g. "cross" -> DS4_BUTTON_CROSS / XUSB_GAMEPAD_A
        self.dpad_map   = {}  # e.g. "up"    -> DS4_DPAD_NORTH / XUSB_GAMEPAD_DPAD_UP

        vg_mod = get_vgamepad()
        if use_chiaki4deck and vg_mod is not None and platform.system() == "Windows":
            try:
                # Prefer DS4
                self.gamepad = vg_mod.VDS4Gamepad()
                self.pad_type = "ds4"
                self.vg_mod = vg_mod
                self._init_maps()
                log("INFO", "CHIAKI4DECK mode enabled: DS4 virtual controller.")
                self.mode = "gamepad"
            except Exception as e:
                log("WARN", f"Failed to init virtual gamepad, falling back to mouse/keyboard: {e}")
                self.mode = "kbmouse"

        elif use_chiaki4deck and vg_mod is None:
            log("WARN", "CHIAKI4DECK is True but vgamepad is not available. Using mouse/keyboard.")
        else:
            log("INFO", "Using mouse/keyboard input backend.")

    # ---------- mapping initialisation ----------

    def _init_maps(self):
        """
        Fill self.button_map and self.dpad_map with logical names.
        Logical names are what you'll use everywhere in the app.
        """
        if self.pad_type == "ds4":
            b = self.vg_mod.DS4_BUTTONS
            d = self.vg_mod.DS4_DPAD_DIRECTIONS
            s = self.vg_mod.DS4_SPECIAL_BUTTONS

            self.button_map = {
                # face
                "cross":    b.DS4_BUTTON_CROSS,
                "circle":   b.DS4_BUTTON_CIRCLE,
                "square":   b.DS4_BUTTON_SQUARE,
                "triangle": b.DS4_BUTTON_TRIANGLE,

                # synonyms
                "x":        b.DS4_BUTTON_CROSS,
                "o":        b.DS4_BUTTON_CIRCLE,
                "a":        b.DS4_BUTTON_SQUARE,
                "s":        b.DS4_BUTTON_CROSS,

                # shoulders / thumbs
                "l1":       b.DS4_BUTTON_SHOULDER_LEFT,
                "r1":       b.DS4_BUTTON_SHOULDER_RIGHT,
                "l3":       b.DS4_BUTTON_THUMB_LEFT,
                "r3":       b.DS4_BUTTON_THUMB_RIGHT,

                # meta
                "share":    b.DS4_BUTTON_SHARE,
                "options":  b.DS4_BUTTON_OPTIONS,
                "ps":       s.DS4_SPECIAL_BUTTON_PS,
            }

            self.dpad_map = {
                "up":       d.DS4_BUTTON_DPAD_NORTH,
                "down":     d.DS4_BUTTON_DPAD_SOUTH,
                "left":     d.DS4_BUTTON_DPAD_WEST,
                "right":    d.DS4_BUTTON_DPAD_EAST,
                "none":     d.DS4_BUTTON_DPAD_NONE,
            }

        else:
            # XInput (Xbox layout)
            xb = self.vg_mod.XUSB_BUTTON

            self.button_map = {
                # face
                "a":        xb.XUSB_GAMEPAD_A,
                "b":        xb.XUSB_GAMEPAD_B,
                "x":        xb.XUSB_GAMEPAD_X,
                "y":        xb.XUSB_GAMEPAD_Y,

                # shoulders / thumbs
                "lb":       xb.XUSB_GAMEPAD_LEFT_SHOULDER,
                "rb":       xb.XUSB_GAMEPAD_RIGHT_SHOULDER,
                "ls":       xb.XUSB_GAMEPAD_LEFT_THUMB,
                "rs":       xb.XUSB_GAMEPAD_RIGHT_THUMB,

                # meta
                "start":    xb.XUSB_GAMEPAD_START,
                "back":     xb.XUSB_GAMEPAD_BACK,

                # dpad as buttons (for XInput)
                "dpad_up":    xb.XUSB_GAMEPAD_DPAD_UP,
                "dpad_down":  xb.XUSB_GAMEPAD_DPAD_DOWN,
                "dpad_left":  xb.XUSB_GAMEPAD_DPAD_LEFT,
                "dpad_right": xb.XUSB_GAMEPAD_DPAD_RIGHT,
            }

            self.dpad_map = {
                "up":    xb.XUSB_GAMEPAD_DPAD_UP,
                "down":  xb.XUSB_GAMEPAD_DPAD_DOWN,
                "left":  xb.XUSB_GAMEPAD_DPAD_LEFT,
                "right": xb.XUSB_GAMEPAD_DPAD_RIGHT,
                "none":  None,
            }

    # ---------- low-level helpers ----------

    def _tap_button_raw(self, btn, duration: float):
        if self.gamepad is None or btn is None:
            return
        self.gamepad.press_button(button=btn)
        self.gamepad.update()
        time.sleep(duration)
        self.gamepad.release_button(button=btn)
        self.gamepad.update()

    def _tap_button_name(self, name: str, duration: float = 0.12):
        """
        Tap a logical button name: e.g. "cross", "triangle", "l1", "start".
        """
        if self.mode != "gamepad":
            log("DEBUG", f"tap_button({name}): kbmouse mode, ignoring.")
            return

        key = (name or "").lower()
        btn = self.button_map.get(key)
        if not btn:
            log("WARN", f"tap_button: unknown logical button {name!r} for pad_type={self.pad_type}")
            return

        log("DEBUG", f"tap_button({name}) -> {btn}")
        self._tap_button_raw(btn, duration)

    def _tap_dpad_name(self, direction: str, duration: float = 0.20):
        """
        Tap a D-Pad direction by logical name: "up", "down", "left", "right".
        """
        if self.mode != "gamepad":
            log("DEBUG", f"tap_dpad({direction}): kbmouse mode, ignoring.")
            return

        dir_key = (direction or "").lower()
        if dir_key not in self.dpad_map:
            log("WARN", f"tap_dpad: unknown direction {direction!r}")
            return

        if self.pad_type == "ds4":
            d_const = self.dpad_map[dir_key]
            none_const = self.dpad_map["none"]
            log("DEBUG", f"tap_dpad({direction}) DS4 -> {d_const}")
            self.gamepad.directional_pad(direction=d_const)
            self.gamepad.update()
            time.sleep(duration)
            self.gamepad.directional_pad(direction=none_const)
            self.gamepad.update()
        else:
            # XInput D-Pad is a set of buttons
            btn = self.dpad_map[dir_key]
            log("DEBUG", f"tap_dpad({direction}) XInput -> {btn}")
            self._tap_button_raw(btn, duration)

    def hold_button_name(self, name: str):
        """
        Hold a logical button (e.g. 'circle', 'b', 'triangle') until release_button_name is called.
        """
        if self.mode != "gamepad" or self.gamepad is None:
            log("DEBUG", f"hold_button({name}): kbmouse mode, ignoring.")
            return

        key = (name or "").lower()
        btn = self.button_map.get(key)
        if not btn:
            log("WARN", f"hold_button: unknown logical button {name!r} for pad_type={self.pad_type}")
            return

        self.gamepad.press_button(button=btn)
        self.gamepad.update()

    def release_button_name(self, name: str):
        """
        Release a logical button previously held with hold_button_name.
        """
        if self.mode != "gamepad" or self.gamepad is None:
            log("DEBUG", f"release_button({name}): kbmouse mode, ignoring.")
            return

        key = (name or "").lower()
        btn = self.button_map.get(key)
        if not btn:
            log("WARN", f"release_button: unknown logical button {name!r} for pad_type={self.pad_type}")
            return

        self.gamepad.release_button(button=btn)
        self.gamepad.update()

    # ---------- high-level semantics ----------

    def skip_formation(self):
        """
        Equivalent of ALT skip:
        - KB/mouse: ALT
        - Gamepad: 'options' / 'start'.
        """
        if self.mode == "kbmouse":
            pyautogui.keyDown("altleft")
            time.sleep(0.25)
            pyautogui.keyUp("altleft")
            return

        # DS4: 'options', XInput: 'start'
        if self.pad_type == "ds4":
            self._tap_button_name("options", duration=0.10)
        else:
            self._tap_button_name("start", duration=0.10)

    def press_key(self, key: str):
        """
        Abstracted 'press key':
        - KB/mouse: pyautogui.press(key)
        - Gamepad: mapped semantics (auto-mode, enter, ramen 'w', etc.)
        """
        key_low = (key or "").lower()

        # ---------- KB / MOUSE MODE ----------
        if self.mode == "kbmouse":
            pyautogui.press(key)
            return

        # ---------- GAMEPAD MODE ----------

        # --- AUTO MODE (your bot key, usually "u") ---
        if key_low == AUTO_MODE_KEY.lower():
            log("DEBUG", "press_key(auto): DPad DOWN")
            self._tap_dpad_name("down", duration=0.25)
            return

        # --- ENTER semantics (Ranked menus, ramen, etc.) ---
        if key_low in ("enter", "\n"):
            if self.pad_type == "ds4":
                log("DEBUG", "press_key('enter'): DS4 CROSS")
                self._tap_button_name("cross", duration=0.10)
            else:
                log("DEBUG", "press_key('enter'): XInput A")
                self._tap_button_name("a", duration=0.10)
            return

        # --- ESCAPE ---
        if key_low in ("esc", "escape"):
            if self.pad_type == "ds4":
                log("DEBUG", "press_key('esc'): DS4 OPTIONS")
                self._tap_button_name("options", duration=0.10)
            else:
                log("DEBUG", "press_key('esc'): XInput B")
                self._tap_button_name("b", duration=0.10)
            return

        # --- Pink beans 'v' key ---
        if key_low == "v":
            if self.pad_type == "ds4":
                log("DEBUG", "press_key('v'): DS4 TRIANGLE")
                self._tap_button_name("triangle", duration=0.10)
            else:
                log("DEBUG", "press_key('v'): XInput X")
                self._tap_button_name("x", duration=0.10)
            return

        # --- Arrow keys → D-Pad ---
        if key_low in ("up", "down", "left", "right"):
            log("DEBUG", f"press_key('{key_low}'): DPad {key_low.upper()}")
            self._tap_dpad_name(key_low, duration=0.20)
            return

        # --- Ramen 'w' semantics ---
        if key_low == "w":
            if self.pad_type == "ds4":
                log("DEBUG", "press_key('w'): DS4 TRIANGLE (ramen)")
                self._tap_button_name("triangle", duration=0.10)
            else:
                log("DEBUG", "press_key('w'): XInput Y (ramen)")
                self._tap_button_name("y", duration=0.10)
            return

        # --- Beans 'a' / 's' semantics (reuse DS4/XInput mappings) ---
        if key_low in ("a", "s"):
            # For DS4:
            #   "a" -> SQUARE, "s" -> CROSS (already defined in button_map)
            # For XInput:
            #   "a" -> A, "s" is not mapped and will warn internally.
            log("DEBUG", f"press_key('{key_low}'): mapped to gamepad face button via button_map")
            self._tap_button_name(key_low, duration=0.10)
            return

        # Fallback
        log("WARN", f"press_key({key!r}) not mapped in gamepad mode; ignoring.")

    def click_at(self, x: int, y: int, button: str = "left"):
        """
        Abstracted click.
        - KB/mouse: real screen click
        - Gamepad: simulate confirmation (Cross / A).
        """
        if self.mode == "kbmouse":
            pyautogui.click(x=x, y=y, button=button)
            return

        log("DEBUG", f"click_at({x}, {y}) -> pad 'confirm'")
        # DS4 'cross', XInput 'a'
        if self.pad_type == "ds4":
            self._tap_button_name("cross", duration=0.08)
        else:
            self._tap_button_name("a", duration=0.08)

    def move_to(self, x: int, y: int, **kwargs):
        if self.mode == "kbmouse":
            pyautogui.moveTo(x, y, **kwargs)
        else:
            log("DEBUG", "move_to() called in gamepad mode - ignored.")

    def right_click(self):
        if self.mode == "kbmouse":
            pyautogui.click(button="right")
        else:
            # Cancel semantics: Circle / B
            if self.pad_type == "ds4":
                self._tap_button_name("circle", duration=0.08)
            else:
                self._tap_button_name("b", duration=0.08)

    def _hold_button_raw(self, btn):
        if self.gamepad is None or btn is None:
            return
        self.gamepad.press_button(button=btn)
        self.gamepad.update()

    def _release_button_raw(self, btn):
        if self.gamepad is None or btn is None:
            return
        self.gamepad.release_button(button=btn)
        self.gamepad.update()


    def hold_button_name(self, name: str):
        """Hold a logical button (press without release)."""
        if self.mode != "gamepad":
            return
        btn = self.button_map.get(name.lower())
        if not btn:
            log("WARN", f"hold_button: unknown logical button {name!r}")
            return
        log("DEBUG", f"hold_button({name})")
        self._hold_button_raw(btn)


    def release_button_name(self, name: str):
        """Release a logical button."""
        if self.mode != "gamepad":
            return
        btn = self.button_map.get(name.lower())
        if not btn:
            log("WARN", f"release_button: unknown logical button {name!r}")
            return
        log("DEBUG", f"release_button({name})")
        self._release_button_raw(btn)

    def center_left_stick(self):
        """Return left stick to neutral (0,0)."""
        if self.mode != "gamepad" or self.gamepad is None:
            return
        self.gamepad.left_joystick(x_value=0, y_value=0)
        self.gamepad.update()
        
    def set_left_stick(self, x: float, y: float):
        """
        Move left stick using normalized values in [-1.0, 1.0].

        We just forward to vgamepad.left_joystick(x_value, y_value).
        The sign convention you saw (x>0 = left, y>0 = up) is preserved by
        using the same signs here; we just scale to -32768..32767.
        """
        if self.mode != "gamepad" or self.gamepad is None:
            log("DEBUG", f"set_left_stick({x}, {y}): kbmouse mode, ignoring.")
            return

        # clamp
        x = max(-1.0, min(1.0, x))
        y = max(-1.0, min(1.0, y))

        max_val = 32767
        x_i = int(x * max_val)
        y_i = int(y * max_val)

        # vgamepad API
        self.gamepad.left_joystick(x_value=x_i, y_value=y_i)
        self.gamepad.update()
        
# Create a singleton backend used by the bot
input_backend = InputBackend(CHIAKI4DECK)

# ------------- Convenience helpers (global) -------------

def pad_tap(button_name: str, duration: float = 0.12):
    """
    From anywhere: tap a controller button if in gamepad mode.
    Example:
        common.pad_tap("triangle")
        common.pad_tap("cross")
        common.pad_tap("l1")
    """
    if input_backend.mode != "gamepad":
        log("DEBUG", f"pad_tap({button_name}): not in gamepad mode, ignoring.")
        return
    input_backend._tap_button_name(button_name, duration=duration)


def pad_dpad(direction: str, duration: float = 0.20):
    """
    From anywhere: tap a D-Pad direction.
    Example:
        common.pad_dpad("up")
        common.pad_dpad("down")
    """
    if input_backend.mode != "gamepad":
        log("DEBUG", f"pad_dpad({direction}): not in gamepad mode, ignoring.")
        return
    input_backend._tap_dpad_name(direction, duration=duration)

def install_vigem_driver() -> tuple[bool, str]:
    """
    Launch ViGEmBus_1.22.0_x64_x86_arm64.exe (ViGEmBus installer).
    Returns (started_ok, message).
    """
    import subprocess

    exe_path = resource_path(os.path.join("tools", "ViGEmBus_1.22.0_x64_x86_arm64.exe"))

    if not os.path.exists(exe_path):
        return False, f"ViGEmBus_1.22.0_x64_x86_arm64.exe not found at: {exe_path}"

    try:
        # Let Legacinator handle UAC elevation itself
        subprocess.Popen([exe_path], shell=False)
        return True, "ViGEmBus installer launched."
    except Exception as e:
        return False, f"Failed to launch ViGEmBus installer: {e}"

def install_vgamepad_blocking() -> tuple[bool, str]:
    import subprocess
    import sys
    import shutil

    """
    Try to install vgamepad using pip.
    Returns (success, output).
    """

    def run_cmd(cmd):
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            out, _ = proc.communicate()
            return proc.returncode == 0, out
        except Exception as e:
            return False, f"Failed to run {' '.join(cmd)}: {e}"

    # ---- 1) Non-frozen: dev mode, use sys.executable ----
    if not getattr(sys, "frozen", False):
        cmd = [sys.executable, "-m", "pip", "install", "vgamepad"]
        return run_cmd(cmd)

    # ---- 2) Frozen (PyInstaller): try external Python interpreters ----
    candidates = []

    if shutil.which("py"):
        candidates.append(["py", "-3"])
    if shutil.which("python"):
        candidates.append(["python"])
    if shutil.which("python3"):
        candidates.append(["python3"])

    for base in candidates:
        cmd = base + ["-m", "pip", "install", "vgamepad"]
        ok, out = run_cmd(cmd)
        if ok:
            return True, out or "vgamepad installed successfully."

    # If we get here, nothing worked
    msg = (
        "Could not run pip automatically from the EXE.\n\n"
        "Please install vgamepad manually by running one of these commands in a terminal:\n"
        "  py -3 -m pip install vgamepad\n"
        "  python -m pip install vgamepad\n"
        "  python3 -m pip install vgamepad\n"
    )
    return False, msg

def send_auto_mode():
    """
    Send the auto-mode input through the active backend
    (mouse/keyboard or virtual gamepad).
    """
    input_backend.press_key(AUTO_MODE_KEY)

def skip_formation():
    input_backend.skip_formation()

def press_enter():
    input_backend.press_key("enter")

# backwards-compat alias for old code
def send_enter():
    press_enter()

def _guess_connection_from_string(s: str) -> str:
    """
    Prova a inferire il tipo di connessione a partire da PNPDeviceID + Name.

    Ritorna stringhe user-friendly tipo:
    - "Wireless (Bluetooth)"
    - "Wireless (USB receiver)"
    - "Wired (USB)"
    - "Wired (integrated)"
    - "Unknown"
    """
    if not s:
        return "Unknown"

    s_low = s.lower()

    # ---- wireless / bluetooth ----
    if "bthenum" in s_low or "bluetooth" in s_low:
        return "Wireless (Bluetooth)"

    # dongle tipo Logitech / RF 2.4GHz
    if "nano receiver" in s_low or "unifying receiver" in s_low:
        return "Wireless (USB receiver)"

    if "wireless" in s_low or "2.4ghz" in s_low or "rf receiver" in s_low:
        return "Wireless"

    # ---- usb / hid ----
    # molti device appaiono come HID o con VID_/PID_
    if "usb" in s_low or "hid\\" in s_low or "vid_" in s_low:
        return "Wired (USB)"

    # ---- integrato su mobo / ps2-like ----
    # esempi classici: ACPI\PNP0303 (keyboard), ACPI\PNP0F13 (mouse)
    if "acpi" in s_low or "pnp0" in s_low or "pnp03" in s_low or "pnp0f" in s_low:
        return "Wired (integrated)"

    return "Unknown"


def detect_hardware() -> dict:
    """
    Best-effort detection of OS, keyboard and mouse info on Windows.
    Falls back to 'Unknown' if anything fails.
    """
    os_label = f"{platform.system()} {platform.release()}"
    kb_label = "Unknown"
    kb_conn = "Unknown"
    mouse_label = "Unknown"
    mouse_conn = "Unknown"

    try:
        import wmi
        c = wmi.WMI()

        keyboards = list(c.Win32_Keyboard())
        mice = list(c.Win32_PointingDevice())

        log("DEBUG", f"Hardware WMI: {len(keyboards)} keyboards, {len(mice)} mice detected")

        # --- Keyboard ---
        if keyboards:
            kb = keyboards[0]
            kb_label = kb.Name or kb.Description or "Unknown"
            pnp = getattr(kb, "PNPDeviceID", "") or ""
            kb_conn = _guess_connection_from_string(pnp + " " + kb_label)

        # --- Mouse / pointing device ---
        if mice:
            m = mice[0]
            mouse_label = m.Name or m.Description or "Unknown"
            pnp = getattr(m, "PNPDeviceID", "") or ""
            mouse_conn = _guess_connection_from_string(pnp + " " + mouse_label)

    except Exception as e:
        log("DEBUG", f"Hardware detection failed: {e!r}")

    return {
        "os": os_label,
        "keyboard": kb_label,
        "keyboard_conn": kb_conn,
        "mouse": mouse_label,
        "mouse_conn": mouse_conn,
    }


HARDWARE_INFO = detect_hardware()

def fetch_latest_version() -> str | None:
    """
    Returns latest release tag from GitHub or None on failure.
    """
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "IEVR-Helper"}
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        tag = (data.get("tag_name") or data.get("name") or "").strip()
        return tag or None
    except Exception:
        return None


# ========== SAVE SETTINGS (SIMPLE MODE) ==========

def save_settings_to_file(values: dict):
    """
    Save values back into base/settings.py (both dev and frozen).
    Writes all ALL-CAPS keys it receives.
    """
    try:
        # Handle frozen mode (EXE)
        if getattr(sys, "frozen", False):
            base_dir = os.path.join(os.path.dirname(sys.executable), "base")
        else:
            base_dir = os.path.dirname(os.path.abspath(settings.__file__))

        path = os.path.join(base_dir, "settings.py")
        os.makedirs(base_dir, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            f.write("# Saved settings for IEVR Helper\n\n")

            # only write ALL-CAPS keys, sorted for stable order
            for key in sorted(k for k in values.keys() if k.isupper()):
                val = values[key]
                f.write(f"{key} = {repr(val)}\n")

        # reload after write so common.cfg picks up changes
        try:
            reload_settings()
        except Exception as e:
            log("WARN", f"Failed to reload settings module: {e}")

        log("INFO", f"Settings saved to: {path}")

    except Exception as e:
        log("ERROR", f"Failed to save settings: {e}")
