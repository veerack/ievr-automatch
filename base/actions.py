# base/actions.py
import random

import pyautogui

from . import common
from .window_helpers import ensure_game_window, screen_point_from_offset, sleep_with_stop


def click_play_button(stop_event):
    if stop_event.is_set():
        return

    if not ensure_game_window(stop_event):
        return

    play_offset = common.get_play_button_offset()
    pos = screen_point_from_offset(play_offset)
    if pos is None:
        return

    x, y = pos
    common.log(
        "ACTION",
        f"Moving cursor to 'Ranked Match' button (offset {play_offset}) → {pos}"
    )

    try:
        common.PLAY_BUTTON_IDLE_COLOR = pyautogui.pixel(x, y)
        common.log("DEBUG", f"Captured idle Ranked button color: {common.PLAY_BUTTON_IDLE_COLOR}")
    except Exception as e:
        common.log("WARN", f"Could not read Ranked button color: {e}")

    common.input_backend.move_to(x, y, duration=0.25)
    try:
        pos_now = pyautogui.position()
        common.log("DEBUG", f"Arrived at button, current position = {pos_now}")
    except Exception:
        pass

    dx = random.randint(-6, 6)
    dy = random.randint(-6, 6)
    common.input_backend.move_to(x + dx, y + dy, duration=0.12)
    common.input_backend.move_to(x, y, duration=0.10)

    common.input_backend.click_at(x, y, button="left")
    common.log("ACTION", "Clicked 'Ranked Match' button (or attempted, depending on mode).")


def click_left_n_times(n, interval, stop_event):
    if not ensure_game_window(stop_event):
        return

    # choose a safe base position (play button); fallback = current mouse pos
    pos = None
    if common.PLAY_BUTTON_OFFSET is not None:
        pos = screen_point_from_offset(common.PLAY_BUTTON_OFFSET)

    if pos is None:
        pos = pyautogui.position()

    x, y = pos
    common.log(
        "ACTION",
        f"Sending {n} left-clicks, every {interval:.1f}s at base {pos}..."
    )

    for _ in range(n):
        if stop_event.is_set():
            return
        common.input_backend.click_at(x, y, button="left")
        sleep_with_stop(interval, stop_event)


def post_match_clicks(stop_event):
    if not ensure_game_window(stop_event):
        return

    # same safe base coord logic
    pos = None
    if common.PLAY_BUTTON_OFFSET is not None:
        pos = screen_point_from_offset(common.PLAY_BUTTON_OFFSET)
    if pos is None:
        pos = pyautogui.position()

    x, y = pos

    common.log(
        "ACTION",
        f"End of match: sending {common.POST_MATCH_CLICKS} clicks at {pos} "
        f"to return to menu."
    )

    for _ in range(common.POST_MATCH_CLICKS):
        if stop_event.is_set():
            return

        common.input_backend.click_at(x, y, button="left")

        if not common.LVL_75_PLUS:
            common.send_enter()

        sleep_with_stop(common.POST_MATCH_CLICK_INTERVAL, stop_event)


def press_auto_mode(stop_event):
    if stop_event.is_set():
        return
    if not ensure_game_window(stop_event):
        return
    common.log("ACTION", f"Pressing auto-mode: {common.AUTO_MODE_KEY} / pad mapping")
    common.send_auto_mode()
