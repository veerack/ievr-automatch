# base/beans/blue.py

import threading

import pyautogui

from .. import common
from ..window_helpers import ensure_game_window, sleep_with_stop


def _press(key: str):
    """
    Press a key using the shared input backend if present, otherwise pyautogui.
    """
    backend = getattr(common, "input_backend", None)

    if backend is not None:
        try:
            # adapt to whatever your backend exposes
            if hasattr(backend, "press_key"):
                backend.press_key(key)
            elif hasattr(backend, "tap_key"):
                backend.tap_key(key)
            else:
                # no known method, fallback
                raise RuntimeError("InputBackend has no press_key/tap_key")
            return
        except Exception as e:
            common.log(
                "WARN",
                f"Blue Beans: backend key press failed for {key!r}: {e}; "
                "falling back to pyautogui."
            )

    pyautogui.press(key)

def run_blue_beans_trainer(stop_event: threading.Event):
    """
    Auto-farmer for BLUE beans.

    Port of your prototype, integrated with:
      - ensure_game_window()
      - sleep_with_stop()
      - common.input_backend
      - common.log()
    """

    # ---- Load timing config once at start ----
    initial_delay  = float(getattr(common, "BLUE_INITIAL_DELAY", 5.0))

    d_enter1       = float(getattr(common, "BLUE_ENTER1_DELAY", 1.2))
    d_enter2       = float(getattr(common, "BLUE_ENTER2_DELAY", 0.7))
    d_up           = float(getattr(common, "BLUE_UP_DELAY", 0.3))
    d_enter3       = float(getattr(common, "BLUE_ENTER3_DELAY", 0.3))
    d_enter4       = float(getattr(common, "BLUE_ENTER4_DELAY", 7.0))

    d_a1           = float(getattr(common, "BLUE_A1_DELAY", 4.5))
    d_s1           = float(getattr(common, "BLUE_S1_DELAY", 8.5))
    d_a2           = float(getattr(common, "BLUE_A2_DELAY", 4.0))
    d_s2           = float(getattr(common, "BLUE_S2_DELAY", 10.0))
    d_a3           = float(getattr(common, "BLUE_A3_DELAY", 3.0))
    d_s3           = float(getattr(common, "BLUE_S3_DELAY", 5.0))
    d_a4           = float(getattr(common, "BLUE_A4_DELAY", 12.0))

    d_enter5       = float(getattr(common, "BLUE_ENTER5_DELAY", 1.5))
    d_cooldown     = float(getattr(common, "BLUE_COOLDOWN_DELAY", 70.0))

    common.log(
        "STATE",
        "Blue Beans trainer starting in "
        f"{initial_delay:.1f} seconds. Make sure you're in front of the "
        '"Hecaton Stairway" training before we begin.'
    )
    sleep_with_stop(initial_delay, stop_event)
    if stop_event.is_set():
        common.log("STATE", "Blue Beans trainer aborted before start.")
        return

    # Make sure the game is there and focused before we begin at all
    if not ensure_game_window(stop_event, timeout=15.0):
        common.log("ERROR", "Blue Beans: game window not found / not focusable, aborting.")
        return

    common.log("STATE", "Blue Beans trainer loop started.")

    while not stop_event.is_set():
        # Re-ensure window each cycle
        if not ensure_game_window(stop_event, timeout=5.0):
            common.log("ERROR", "Blue Beans: lost game window, stopping.")
            break

        # === SEQUENCE ===================================================
        _press("enter")
        sleep_with_stop(d_enter1, stop_event)
        if stop_event.is_set(): break

        _press("enter")
        sleep_with_stop(d_enter2, stop_event)
        if stop_event.is_set(): break

        _press("up")
        sleep_with_stop(d_up, stop_event)
        if stop_event.is_set(): break

        _press("enter")
        sleep_with_stop(d_enter3, stop_event)
        if stop_event.is_set(): break

        _press("enter")
        sleep_with_stop(d_enter4, stop_event)
        if stop_event.is_set(): break

        _press("a")
        sleep_with_stop(d_a1, stop_event)
        if stop_event.is_set(): break

        _press("s")
        sleep_with_stop(d_s1, stop_event)
        if stop_event.is_set(): break

        _press("a")
        sleep_with_stop(d_a2, stop_event)
        if stop_event.is_set(): break

        _press("s")
        sleep_with_stop(d_s2, stop_event)
        if stop_event.is_set(): break

        _press("a")
        sleep_with_stop(d_a3, stop_event)
        if stop_event.is_set(): break

        _press("s")
        sleep_with_stop(d_s3, stop_event)
        if stop_event.is_set(): break

        _press("a")
        sleep_with_stop(d_a4, stop_event)
        if stop_event.is_set(): break

        _press("enter")
        sleep_with_stop(d_enter5, stop_event)
        if stop_event.is_set(): break

        _press("enter")

        common.log(
            "ACTION",
            f"Blue Beans: beans obtained, waiting {d_cooldown:.1f}s for training reset…"
        )

        # Cooldown before restarting loop
        sleep_with_stop(d_cooldown, stop_event)

    common.log("STATE", "Blue Beans trainer stopped.")

