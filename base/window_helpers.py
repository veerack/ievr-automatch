# base/window_helpers.py
import threading
import time

import pyautogui
import pygetwindow as gw

from . import common
import win32gui
from ctypes import windll, wintypes, byref

def get_client_size(hwnd):
    """
    Ritorna (client_width, client_height) dell’area interna della finestra.
    Non include bordo né barra del titolo.
    """
    rect = wintypes.RECT()
    windll.user32.GetClientRect(hwnd, byref(rect))
    width = rect.right - rect.left
    height = rect.bottom - rect.top
    return width, height

def get_game_window():
    for w in gw.getAllWindows():
        if common.GAME_WINDOW_TITLE.lower() in w.title.lower():
            return w
    return None


def focus_game_window():
    win = get_game_window()
    if win:
        try:
            win.activate()
            time.sleep(0.2)
        except Exception as e:
            common.log("WARN", f"Could not activate game window: {e}")
    else:
        common.log("WARN", "Game window not found. Check GAME_WINDOW_TITLE in settings.py.")


def sleep_with_stop(seconds, stop_event, step=0.25):
    """Sleep in small chunks so we can react to 'Stop' quickly."""
    end = time.time() + seconds
    while time.time() < end:
        if stop_event.is_set():
            return
        time.sleep(step)


def ensure_game_window(stop_event, timeout=None, check_interval=2.0):
    """
    Wait until the game window exists and is focused, then move mouse inside it.

    - timeout=None  => wait indefinitely (until stop_event is set)
    - timeout>0     => wait up to that many seconds, then fail

    Returns True if window is found & focused, False otherwise.
    """
    start_logged = False
    end_time = None if timeout is None else time.time() + timeout

    while not stop_event.is_set():
        win = get_game_window()
        if win:
            try:
                if hasattr(win, "isMinimized") and win.isMinimized:
                    win.restore()
                    time.sleep(0.3)

                win.activate()
                time.sleep(0.25)

                cx = win.left + max(20, win.width // 2)
                cy = win.top + max(20, win.height // 2)
                pyautogui.moveTo(cx, cy, duration=0.15)
                common.log("DEBUG", f"ensure_game_window: activated '{win.title}'")

                return True
            except Exception as e:
                common.log("WARN", f"ensure_game_window: failed to activate window: {e}")
                sleep_with_stop(check_interval, stop_event)
                continue

        if not start_logged:
            common.log("STATE", "Waiting for game window to appear...")
            start_logged = True
        else:
            common.log("DEBUG", "Game window not found yet, still waiting...")

        if timeout is not None and time.time() > end_time:
            common.log("ERROR", "Timed out waiting for the game window.")
            return False

        sleep_with_stop(check_interval, stop_event)

    return False


def screen_point_from_offset(offset):
    """Convert a window-relative offset (dx, dy) into absolute screen coordinates."""
    win = get_game_window()
    if not win:
        common.log("WARN", "Game window not found when converting offset to screen coords.")
        return None
    dx, dy = offset
    return (win.left + dx, win.top + dy)


def capture_offsets_if_needed(stop_event):
    """
    Calibrate PLAY_BUTTON_OFFSET and ANNUL_PIXEL_OFFSET/COLOR if they are None.
    Persists to settings.py via common.save_settings_to_file.
    """
    from .common import save_settings_to_file  # avoid circular at top

    if not ensure_game_window(stop_event, timeout=None):
        common.log("ERROR", "Game window NOT found. Start the game and try again.")
        return False

    win = get_game_window()
    if not win:
        common.log("ERROR", "Game window NOT found after ensure_game_window().")
        return False

    common.log("INFO", f"Game window found: '{win.title}'")
    common.log("DEBUG", f"Window position (left, top) = ({win.left}, {win.top})")

    # 1) Ranked match button offset
    if common.PLAY_BUTTON_OFFSET is None:
        common.log("STATE", "In 10 seconds I will record the 'Ranked Match' button position.")
        common.log("INFO", "Place your cursor over the button to queue for a ranked match.")
        sleep_with_stop(10, stop_event)
        if stop_event.is_set():
            return False
        pos = pyautogui.position()
        common.PLAY_BUTTON_OFFSET = (pos.x - win.left, pos.y - win.top)
        common.log("INFO", f"PLAY_BUTTON_OFFSET captured = {common.PLAY_BUTTON_OFFSET}")
        pyautogui.click(button="left")

    # 2) Cancel button offset + color
    if common.ANNUL_PIXEL_OFFSET is None:
        common.log("STATE", "In 10 seconds I will record the 'Cancel' button position (while searching).")
        common.log("INFO", "Place your cursor on the CANCEL button (don't click).")
        sleep_with_stop(10, stop_event)
        if stop_event.is_set():
            return False

        mouse = pyautogui.position()
        sample_x = mouse.x
        sample_y = mouse.y + 5

        common.ANNUL_PIXEL_OFFSET = (sample_x - win.left, sample_y - win.top)
        common.ANNUL_PIXEL_COLOR = pyautogui.pixel(sample_x, sample_y)

        common.log("INFO", f"ANNUL_PIXEL_OFFSET captured = {common.ANNUL_PIXEL_OFFSET}")
        common.log("INFO", f"ANNUL_PIXEL_COLOR  captured = {common.ANNUL_PIXEL_COLOR}")
        common.log("DEBUG", f"Calibrated CANCEL at abs=({sample_x}, {sample_y}) in window '{win.title}'")

    common.log(
        "INFO",
        "Offsets configured for this run. "
        "If you want them permanent, copy these values into settings.py."
    )

    cancel_abs = screen_point_from_offset(common.ANNUL_PIXEL_OFFSET)
    if cancel_abs is not None:
        common.log("ACTION", f"Clicking calibrated CANCEL at {cancel_abs} to stop search.")
        pyautogui.click(cancel_abs[0], cancel_abs[1], button="left")

    save_settings_to_file({
        "GAME_WINDOW_TITLE": common.GAME_WINDOW_TITLE,
        "AUTO_MODE_KEY": common.AUTO_MODE_KEY,
        "DELAY_BEFORE_START": common.DELAY_BEFORE_START,
        "FIRST_WAIT": common.FIRST_WAIT,
        "SECOND_WAIT": common.SECOND_WAIT,
        "MATCH_DURATION": common.MATCH_DURATION,
        "POST_MATCH_CLICKS": common.POST_MATCH_CLICKS,
        "POST_MATCH_CLICK_INTERVAL": common.POST_MATCH_CLICK_INTERVAL,
        "SEARCH_CHECK_INTERVAL": common.SEARCH_CHECK_INTERVAL,
        "PLAY_BUTTON_OFFSET": common.PLAY_BUTTON_OFFSET,
        "ANNUL_PIXEL_OFFSET": common.ANNUL_PIXEL_OFFSET,
        "ANNUL_PIXEL_COLOR": common.ANNUL_PIXEL_COLOR,
        "END_BUTTON_OFFSET": common.END_BUTTON_OFFSET,
        "END_BUTTON_COLOR": common.END_BUTTON_COLOR,
        "LVL_75_PLUS": common.LVL_75_PLUS,
        "CHIAKI4DECK": common.CHIAKI4DECK,
        "MATCH_TIMEOUT_MARGIN": common.MATCH_TIMEOUT_MARGIN,
        "MAX_MATCHES_PER_RUN": common.MAX_MATCHES_PER_RUN,
        "MAX_RUNTIME_MINUTES": common.MAX_RUNTIME_MINUTES,
    })

    return True

def recalibrate_offsets_via_gui():
    """Reset offsets and run the capture flow again."""
    temp_event = threading.Event()
    common.PLAY_BUTTON_OFFSET = None
    common.ANNUL_PIXEL_OFFSET = None
    # reset to original settings.py default (could be None)
    common.ANNUL_PIXEL_COLOR = common.cfg.ANNUL_PIXEL_COLOR
    common.log("INFO", "Recalibration started. Follow the instructions in the log.")
    if capture_offsets_if_needed(temp_event):
        common.log("INFO", "Recalibration finished. New offsets are now active for this session.")
    else:
        common.log("WARN", "Recalibration was cancelled or failed.")
