# base/ramen_trainer.py

import time
import random

import pyautogui

from . import common
from .window_helpers import ensure_game_window, sleep_with_stop

import win32api
import win32con


def alt_c_pressed():
    ALT = win32api.GetAsyncKeyState(win32con.VK_MENU) & 0x8000
    C   = win32api.GetAsyncKeyState(ord('C')) & 0x8000
    return ALT and C


def _press_key(key: str, times: int, delay: float, stop_event):
    """
    Press a key 'times' with controlled delay.
    Checks ALT+C and stop_event frequently to remain responsive.
    """
    for _ in range(times):
        if stop_event.is_set() or alt_c_pressed():
            common.log("WARN", "Ramen trainer: stop requested during key press.")
            stop_event.set()
            return

        common.input_backend.press_key(key)

        waited = 0.0
        while waited < delay:
            if stop_event.is_set() or alt_c_pressed():
                common.log("WARN", "Ramen trainer: stop requested during key delay.")
                stop_event.set()
                return
            step = min(0.05, delay - waited)
            time.sleep(step)
            waited += step


def run_ramen_trainer(stop_event):
    """
    Fully configurable Ramen NPC Trainer loop.
    Uses settings from settings.py / GUI.
    """

    # ---- LOAD SETTINGS ----
    initial_delay        = common.RAMEN_INITIAL_DELAY

    first_enter_count    = common.RAMEN_FIRST_ENTER_COUNT
    first_enter_delay    = common.RAMEN_FIRST_ENTER_DELAY
    after_first_wait     = common.RAMEN_AFTER_FIRST_WAIT

    w_min                = common.RAMEN_W_MIN
    w_max                = common.RAMEN_W_MAX
    w_delay              = common.RAMEN_W_DELAY

    long_wait_min        = common.RAMEN_LONG_WAIT_MIN
    long_wait_max        = common.RAMEN_LONG_WAIT_MAX

    final_enter_count    = common.RAMEN_FINAL_ENTER_COUNT
    final_enter_delay    = common.RAMEN_FINAL_ENTER_DELAY
    after_final_wait     = common.RAMEN_AFTER_FINAL_WAIT

    # ---- LOG START ----
    common.log(
        "STATE",
        f"Ramen trainer activated. Make sure to be in front of the Ramen NPC, trainer will start in {initial_delay}s."
    )
    common.log(
        "INFO",
        "To stop the Ramen NPC Trainer, simply press ALT+C or close the app."
    )

    if not ensure_game_window(stop_event, timeout=10.0):
        common.log("ERROR", "Ramen trainer: game window not found or could not be focused.")
        return

    sleep_with_stop(initial_delay, stop_event)

    if stop_event.is_set():
        common.log("INFO", "Ramen trainer: stopped before starting loop.")
        return

    common.log("STATE", "Ramen trainer: loop started.")

    cycle = 0

    while not stop_event.is_set():

        if alt_c_pressed():
            common.log("WARN", "ALT+C detected → stopping Ramen Trainer.")
            stop_event.set()
            break

        cycle += 1
        common.log("STATE", f"Ramen trainer: starting cycle #{cycle}")

        # ---- STEP 1: FIRST ENTER ----
        common.log("ACTION", f"ENTER x{first_enter_count}")
        _press_key("enter", first_enter_count, first_enter_delay, stop_event)
        if stop_event.is_set():
            break

        # ---- STEP 2: WAIT ----
        common.log("DEBUG", f"Waiting {after_first_wait}s")
        sleep_with_stop(after_first_wait, stop_event)
        if stop_event.is_set() or alt_c_pressed():
            stop_event.set()
            break

        # ---- STEP 3: WALK ----
        w_times = random.randint(w_min, w_max)
        common.log("ACTION", f"W x{w_times}")
        _press_key("w", w_times, w_delay, stop_event)
        if stop_event.is_set():
            break

        # ---- STEP 4: LONG WAIT ----
        long_wait = random.uniform(long_wait_min, long_wait_max)
        common.log("DEBUG", f"Ramen animation wait: {long_wait:.1f}s")
        sleep_with_stop(long_wait, stop_event)
        if stop_event.is_set() or alt_c_pressed():
            stop_event.set()
            break

        # ---- STEP 5: FINAL ENTER ----
        common.log("ACTION", f"Final ENTER x{final_enter_count}")
        _press_key("enter", final_enter_count, final_enter_delay, stop_event)

        common.log("DEBUG", f"Post-cycle wait {after_final_wait}s")
        sleep_with_stop(after_final_wait, stop_event)

        common.log("STATE", f"Ramen trainer: cycle #{cycle} completed")

    common.log("INFO", "Ramen trainer: stopped.")
