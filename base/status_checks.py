# base/status_checks.py
import pyautogui

from . import common
from .window_helpers import ensure_game_window, screen_point_from_offset, sleep_with_stop, get_game_window


def rgb_dist(a, b):
    """Euclidean distance between two (r,g,b) tuples."""
    return ((a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2) ** 0.5


def is_match_over(stop_event):
    """
    Returns True if the 'Next' button pixel is visible (end of match).
    Also sends one click inside the game window each time we check,
    so that 'opponent quit' / confirmation dialogs can be advanced.
    """
    if not ensure_game_window(stop_event, timeout=5):
        common.log("DEBUG", "is_match_over: game window not available")
        return False

    win = get_game_window()
    if not win:
        common.log("DEBUG", "is_match_over: game window not found after ensure_game_window()")
        return False

    # keep-alive click first
    try:
        pyautogui.click(button="left")
        common.log("ACTION", "is_match_over: sent keep-alive click inside game window.")
    except Exception as e:
        common.log("DEBUG", f"is_match_over: failed to send keep-alive click: {e}")

    end_offset, end_color = common.get_end_button()

    x = win.left + end_offset[0]
    y = win.top + end_offset[1]

    try:
        pixel = pyautogui.pixel(x, y)
    except Exception as e:
        common.log("DEBUG", f"is_match_over: failed to read pixel: {e}")
        return False

    tol = 22
    diffs = tuple(abs(pixel[i] - end_color[i]) for i in range(3))
    match = all(d <= tol for d in diffs)

    common.log(
        "DEBUG",
        f"is_match_over: pixel={pixel}, expected={end_color}, "
        f"diff={diffs}, tol={tol}, match={match}"
    )

    return match

def is_still_searching(stop_event):
    """
    Returns:
        True  -> still searching
        False -> opponent found
    """
    if stop_event.is_set():
        return False

    offset, color = common.get_annul_pixel()
    if offset is None:
        common.log("WARN", "ANNUL pixel offset not set — skipping search check.")
        return False

    if not ensure_game_window(stop_event, timeout=None):
        common.log("WARN", "Game window unavailable while checking search.")
        return False

    pos = screen_point_from_offset(offset)
    if pos is None:
        return True

    x, y = pos
    MAX_DIST = 80.0

    try:
        pixel = pyautogui.pixel(x, y)
    except Exception as e:
        common.log("WARN", f"Error reading search pixel: {e}")
        return True

    dist = rgb_dist(pixel, color)

    common.log(
        "DEBUG",
        f"Search pixel check single: {pixel}, target={color}, dist={dist:.1f}"
    )

    if dist <= MAX_DIST:
        return True

    common.log("DEBUG", "Search DONE (instant check).")
    return False


def is_back_in_lobby(stop_event):
    """
    Returns True if the Ranked Match button looks like its idle lobby color again.
    Used to detect when the player cancels search or the game drops back to menu.
    """
    if stop_event.is_set():
        return False

    if common.PLAY_BUTTON_OFFSET is None or common.PLAY_BUTTON_IDLE_COLOR is None:
        return False

    if not ensure_game_window(stop_event, timeout=2):
        return False

    pos = screen_point_from_offset(common.PLAY_BUTTON_OFFSET)
    if pos is None:
        return False

    x, y = pos
    try:
        pixel = pyautogui.pixel(x, y)
    except Exception as e:
        common.log("DEBUG", f"is_back_in_lobby: pixel read failed: {e}")
        return False

    dist = rgb_dist(pixel, common.PLAY_BUTTON_IDLE_COLOR)
    common.log(
        "DEBUG",
        f"is_back_in_lobby: current={pixel}, idle={common.PLAY_BUTTON_IDLE_COLOR}, dist={dist:.1f}"
    )

    return dist < 40.0


def detect_search_failed_popup(stop_event):
    """
    Returns True if the big white 'Failed to connect' bar is visible.
    """
    if stop_event.is_set():
        return False

    if not ensure_game_window(stop_event, timeout=3):
        return False

    win = get_game_window()
    if not win:
        return False

    band_y = win.top + int(win.height * 0.50)

    xs = [
        win.left + win.width // 4,
        win.left + win.width // 2,
        win.left + (3 * win.width) // 4,
    ]

    bright_hits = 0
    max_brightness = 0.0

    for x in xs:
        try:
            r, g, b = pyautogui.pixel(x, band_y)
        except Exception as e:
            common.log("WARN", f"Failed-popup pixel read error at ({x},{band_y}): {e}")
            continue

        brightness = (r + g + b) / 3.0
        gray_delta = max(abs(r - g), abs(g - b), abs(r - b))
        max_brightness = max(max_brightness, brightness)

        common.log(
            "DEBUG",
            f"Failed-popup sample @({x},{band_y}) rgb=({r},{g},{b}) "
            f"bright={brightness:.1f} grayΔ={gray_delta}"
        )

        if brightness > 230 and gray_delta < 18:
            bright_hits += 1

    if bright_hits >= 2:
        common.log(
            "DEBUG",
            f"Failed-popup detected: {bright_hits} bright gray samples "
            f"(max bright {max_brightness:.1f})."
        )
        return True

    common.log(
        "DEBUG",
        f"Failed-popup NOT detected (hits={bright_hits}, max bright {max_brightness:.1f})."
    )
    return False
