# base/tools.py
import threading

from . import common
from .window_helpers import get_game_window, focus_game_window, screen_point_from_offset
from .actions import click_play_button
import pyautogui

def resource_path(relative):
    import sys, os
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative)
    return os.path.join(os.path.abspath("."), relative)

def gui_test_focus():
    win = get_game_window()
    if win:
        focus_game_window()
        common.log("INFO", f"Focus test: activated window '{win.title}'.")
    else:
        common.log("WARN", "Focus test: game window not found.")


def gui_test_play_click():
    if common.PLAY_BUTTON_OFFSET is None:
        common.log("WARN", "Play button offset not set. Run calibration first.")
        return
    temp_event = threading.Event()
    click_play_button(temp_event)
    common.log("INFO", "Test click sent to 'Ranked Match' button.")


def gui_test_search_pixel():
    if common.ANNUL_PIXEL_OFFSET is None:
        common.log("WARN", "Search pixel offset not set. Run calibration first.")
        return
    pos = screen_point_from_offset(common.ANNUL_PIXEL_OFFSET)
    if pos is None:
        return
    x, y = pos
    try:
        pixel = pyautogui.pixel(x, y)
    except Exception as e:
        common.log("WARN", f"Search pixel test failed: {e}")
        return
    diff = tuple(pixel[i] - common.ANNUL_PIXEL_COLOR[i] for i in range(3))
    dist = sum(abs(d) for d in diff)
    common.log("INFO", f"Search pixel test: current {pixel}, expected {common.ANNUL_PIXEL_COLOR}, |Δ| sum = {dist}.")
