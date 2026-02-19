# base/bot.py
import time

import pyautogui

from . import common
from .window_helpers import sleep_with_stop, capture_offsets_if_needed
from .status_checks import (
    is_still_searching,
    is_back_in_lobby,
    detect_search_failed_popup,
    is_match_over,
)
from .actions import click_play_button, click_left_n_times, press_auto_mode, post_match_clicks


def bot_main(stop_event):
    try:
        common.log("INFO", f"Bot will start in {common.DELAY_BEFORE_START} seconds.")
        common.log("INFO", "Make sure the game window is open (windowed 1024x576).")
        common.log("INFO", "Fail-safe: move the mouse to any screen corner to stop PyAutoGUI.")
        sleep_with_stop(common.DELAY_BEFORE_START, stop_event)
        if stop_event.is_set():
            common.log("INFO", "Bot start cancelled.")
            return

        if not capture_offsets_if_needed(stop_event):
            common.log("ERROR", "Offset capture failed or was cancelled.")
            return

        session_start = time.time()
        matches_this_session = 0

        while not stop_event.is_set():

            click_play_button(stop_event)
            if stop_event.is_set():
                break

            common.log("STATE", f"Waiting {common.FIRST_WAIT} seconds for initial matchmaking search...")
            sleep_with_stop(common.FIRST_WAIT, stop_event)
            if stop_event.is_set():
                break

            while not stop_event.is_set() and is_still_searching(stop_event):
                common.log("STATE", f"Still searching for an opponent, waiting another {common.SEARCH_CHECK_INTERVAL} seconds...")
                sleep_with_stop(common.SEARCH_CHECK_INTERVAL, stop_event)

            if stop_event.is_set():
                break

            if is_back_in_lobby(stop_event):
                common.log("STATE", "Search ended but lobby is visible (cancelled / no match). Re-queuing.")
                continue

            if detect_search_failed_popup(stop_event):
                common.log("STATE", "Matchmaking failed (no opponent). Closing popup and re-queuing.")
                click_left_n_times(3, 0.3, stop_event)
                continue

            common.log("STATE", "Opponent found. Running pre-match sequence.")

            click_left_n_times(10, 1.0, stop_event)
            if stop_event.is_set():
                break

            sleep_with_stop(4, stop_event)
            if stop_event.is_set():
                break

            common.log("ACTION", "Skipping formation screen (ALT / START)...")
            common.skip_formation()

            common.log("STATE", f"Waiting {common.SECOND_WAIT} seconds before enabling auto-mode (U)...")
            sleep_with_stop(common.SECOND_WAIT, stop_event)
            if stop_event.is_set():
                break

            press_auto_mode(stop_event)
            if stop_event.is_set():
                break

            match_start = time.time()
            HARD_LIMIT = common.MATCH_DURATION + common.MATCH_TIMEOUT_MARGIN

            common.log(
                "STATE",
                f"Match in progress… checking for end button every "
                f"{int(common.SEARCH_CHECK_INTERVAL)}s (timeout at {HARD_LIMIT:.0f}s)."
            )

            timed_out = False

            while not stop_event.is_set():
                elapsed = time.time() - match_start

                if is_match_over(stop_event):
                    common.log("STATE", "Detected end-screen! Starting post-match actions...")
                    break

                if elapsed >= HARD_LIMIT:
                    timed_out = True
                    common.log(
                        "WARN",
                        f"No end button after {elapsed:.0f}s (limit {HARD_LIMIT:.0f}s). "
                        "Assuming match is stuck / failed, forcing post-match cleanup."
                    )
                    break

                common.log(
                    "STATE",
                    f"Match still in progress ({elapsed:.0f}s elapsed), "
                    f"checking again in {int(common.SEARCH_CHECK_INTERVAL)}s..."
                )
                sleep_with_stop(common.SEARCH_CHECK_INTERVAL, stop_event)

            if stop_event.is_set():
                break

            match_duration = time.time() - match_start
            common.log("INFO", f"Match finished (or timed out) in {match_duration:.1f} seconds.")
            common.stats_queue.put(match_duration)

            # update session counters
            matches_this_session += 1
            elapsed_minutes = (time.time() - session_start) / 60.0

            if common.MAX_MATCHES_PER_RUN is not None and matches_this_session >= common.MAX_MATCHES_PER_RUN:
                common.log("STATE", f"Reached max matches per run ({common.MAX_MATCHES_PER_RUN}). Stopping bot.")
                break

            if common.MAX_RUNTIME_MINUTES is not None and elapsed_minutes >= common.MAX_RUNTIME_MINUTES:
                common.log(
                    "STATE",
                    f"Reached max runtime ({elapsed_minutes:.1f} / {common.MAX_RUNTIME_MINUTES:.1f} min). Stopping bot."
                )
                break

            if timed_out:
                common.log("STATE", "Match appears to have timed out. Running recovery clicks...")
            else:
                common.log("STATE", "End-screen confirmed. Running post-match clicks...")

            post_match_clicks(stop_event)
            if stop_event.is_set():
                break

            common.log("INFO", "Cycle completed. Going back to menu and starting over.\n")

        common.log("INFO", "Bot loop finished.")

    except pyautogui.FailSafeException:
        common.log("INFO", "PyAutoGUI fail-safe triggered (mouse moved to a screen corner). Bot stopped.")
    except Exception as e:
        common.log("ERROR", f"Unexpected error in bot thread: {e}")
