import time
import pyautogui
import pygetwindow as gw

GAME_WINDOW_TITLE = "INAZUMA ELEVEN: Victory Road"  # same as in settings.py

print("Make sure the RESULT screen is visible.")
print("Place your mouse EXACTLY on the yellow cup you want to detect.")
input("When you're ready, press ENTER here and DON'T MOVE THE MOUSE...")

# Get mouse position
mx, my = pyautogui.position()
print(f"Mouse position: {mx}, {my}")

# Find game window
wins = [w for w in gw.getAllWindows() if GAME_WINDOW_TITLE in w.title]
if not wins:
    raise SystemExit("Game window not found – check GAME_WINDOW_TITLE.")
win = wins[0]

dx = mx - win.left
dy = my - win.top
r, g, b = pyautogui.pixel(mx, my)

print("\nPut these into settings.py:")
print(f"END_BUTTON_OFFSET = ({dx}, {dy})")
print(f"END_BUTTON_COLOR = ({r}, {g}, {b})")