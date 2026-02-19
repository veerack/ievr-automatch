# base/beans/pink.py

from threading import Event

from .. import common
from .. import window_helpers as wh


def _tap(key: str, delay: float, stop_event: Event) -> bool:
    """
    Press a single key through the unified input backend,
    then sleep for `delay` seconds, but always respecting stop_event.
    """
    if stop_event.is_set():
        return False

    common.input_backend.press_key(key)
    wh.sleep_with_stop(delay, stop_event)
    return not stop_event.is_set()


def _hold_v(stop_event: Event) -> bool:
    """
    Proper HOLD implementation for V:
    - kb/mouse: real 'v' keyDown / keyUp
    - gamepad: hold mapped button (triangle / X) for ~2s
    """
    if stop_event.is_set():
        return False

    hold_time = common.PINK_V_HOLD_DURATION

    if common.input_backend.mode == "kbmouse":
        import pyautogui
        pyautogui.keyDown("v")
        wh.sleep_with_stop(hold_time, stop_event)
        pyautogui.keyUp("v")
        return not stop_event.is_set()

    # --- gamepad mode ---
    if common.input_backend.pad_type == "ds4":
        btn = "triangle"   # V -> triangle
    else:
        btn = "x"          # V -> X on Xbox layout

    common.input_backend.hold_button_name(btn)
    wh.sleep_with_stop(hold_time, stop_event)
    common.input_backend.release_button_name(btn)

    return not stop_event.is_set()


def run_pink_beans_trainer(stop_event: Event) -> None:
    """
    Pink Beans trainer loop.
    [...]
    """
    common.log(
        "STATE",
        'Pink Beans trainer starting in '
        f'{common.PINK_INITIAL_DELAY:.1f} seconds. '
        'Make sure you are in front of the "Courtyard Track" training before we begin.'
    )
    wh.sleep_with_stop(common.PINK_INITIAL_DELAY, stop_event)
    if stop_event.is_set():
        common.log("STATE", "Pink Beans trainer cancelled before start.")
        return

    common.log("STATE", "Pink Beans trainer loop started.")

    while not stop_event.is_set():
        # Make sure game window exists + is focused before each cycle
        if not wh.ensure_game_window(stop_event, timeout=10.0):
            common.log("ERROR", "Game window not found / focus failed for Pink Beans. Stopping.")
            break
        else:
            common.log("DEBUG", "Game window found, proceeding...")

        # ----- MAIN SEQUENCE -----

        # enter
        if not _tap("enter", common.PINK_ENTER1_DELAY, stop_event):
            break

        # enter
        if not _tap("enter", common.PINK_ENTER2_DELAY, stop_event):
            break

        # up
        if not _tap("up", common.PINK_UP_DELAY, stop_event):
            break

        # enter
        if not _tap("enter", common.PINK_ENTER3_DELAY, stop_event):
            break

        # enter → wait animation
        if not _tap("enter", common.PINK_ENTER4_DELAY, stop_event):
            break

        # esc (simple tap)
        if stop_event.is_set():
            break
        common.input_backend.press_key("esc")
        wh.sleep_with_stop(common.PINK_ESC_AFTER_DELAY, stop_event)
        if stop_event.is_set():
            break

        # single 'v' press
        common.input_backend.press_key("v")
        wh.sleep_with_stop(common.PINK_V_AFTER_DELAY, stop_event)
        if stop_event.is_set():
            break

        # hold v (keyboard: real hold, gamepad: triangle/X)
        if not _hold_v(stop_event):
            break

        # extra wait after the hold
        if stop_event.is_set():
            break
        wh.sleep_with_stop(common.PINK_AFTER_HOLD_DELAY, stop_event)
        if stop_event.is_set():
            break

        # down
        if not _tap("down", common.PINK_DOWN_DELAY, stop_event):
            break

        # final enter
        if not _tap("enter", common.PINK_FINAL_ENTER_DELAY, stop_event):
            break

        common.log("STATE", "Pink Beans cycle completed.")

    common.log("STATE", "Pink Beans trainer stopped.")