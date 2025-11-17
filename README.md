# ⚡ IEVR Auto Match Helper  
*A lightweight input-automation utility for Inazuma Eleven: Victory Road (PC)*  

---

## ⚠️ Disclaimer  
This tool is provided **strictly for educational and accessibility purposes**.

It **does NOT**:
- modify game files
- alter memory
- interfere with network traffic
- inject code
- bypass protections

It simply automates **mouse/keyboard input** at the OS level (similar to AutoHotkey).

The author is **not affiliated with LEVEL-5**.  
Users are fully responsible for how they use this software.  
If LEVEL-5 or GitHub requests removal, the repository will be taken down.

---

## ✨ Features  
- ✔ Fully GUI-based (no terminal needed)  
- ✔ Auto matchmaking loop  
- ✔ Detects match start/end via pixel scanning  
- ✔ Interactive window-offset calibration  
- ✔ Works on borderless/windowed mode  
- ✔ Editable configuration via `settings.py`  
- ✔ Lightweight, no dependencies to install for the EXE version  
- ✔ Single file portable executable (see Releases)

---

## IMPORTANT 
- The game resolution must be set to: Windowed & 1024x576. This script hasn't been tested on any other resolution, so i advise using the one mentioned. Feel free to try in different ones and open issues on this repo so i can adapt it!

## 📦 Download  
➡ Download the latest release [here!](https://github.com/veerack/ievr-automatch/releases)

➡ Simply download the release and run the **.exe** file, the script is already compiled!

---

## 🖥 Requirements 
- Windows 10 or 11  
- Inazuma Eleven: Victory Road (PC)
- Must say: a connected Mouse & Keyboard to your device 😅

---

## 🚀 How to Use  
1. Launch **Inazuma Eleven: Victory Road**  
2. Set the game to **Windowed → 1024x576**  
3. Place the window on any monitor
4. Go on "Competitive Game" -> "Online Match"
5. Run `ievr.exe`  
6. Press **Start Bot**  
7. The tool will automatically:
   - Detect the game window  
   - Ask you to hover over specific buttons to capture offsets (if not already registered)  
   - Begin the matchmaking loop
   - Detects when matchmaking fails for whatever reason  
   - Detect when a match starts  
   - Detect when a match ends / opponent leaves  
   - Repeat until you stop it  

---

## 🛠 Customization

If you want more freedom with the settings, you can edit them at the source in `base/settings.py`. This folder gets created after you've ran the script once and its where all the settings for the script are stored:

```python
GAME_WINDOW_TITLE = 'Inazuma Eleven: Victory Road' # title of the windows window of the game (don't change)
AUTO_MODE_KEY = 'u'                                # which key to press to enable commander mode

DELAY_BEFORE_START = 5.0                           # how many seconds to wait before starting the script after clicking "Start"
FIRST_WAIT = 15.0                                  # how many seconds to wait between the checks to see if a game has been found or not
SECOND_WAIT = 80.0                                 # how many seconds to wait after FIRST_WAIT completed before activating commander mode
MATCH_DURATION = 780                               # estimated duration of the matches, usually fine to leave it at 780
POST_MATCH_CLICKS = 20                             # how many clicks the script does at the end of the match to go back to the home screen
POST_MATCH_CLICK_INTERVAL = 0.3                    # interval between the POST_MATCH_CLICKS
SEARCH_CHECK_INTERVAL = 20.0                       # interval between the checks in-match to confirm wether the match is still going or not

PLAY_BUTTON_OFFSET = (292, 247)                    # offset for the button to start queueing
ANNUL_PIXEL_OFFSET = (499, 375)                    # offset for the button to cancel matchmaking
ANNUL_PIXEL_COLOR = (250, 253, 254)                # rgb color of ANNUL_PIXEL_OFFSET
END_BUTTON_OFFSET = (60, 57)                       # offset of the pixel we check to validate wether a match ended or not
END_BUTTON_COLOR = (172, 158, 48)                  # rgb color of END_BUTTON_OFFSET
LVL_75_PLUS = False                                # toggle for teams with all characters above lvl. 75. performs more clicks at the end if disabled
MATCH_TIMEOUT_MARGIN = 120.0                       # how much marging we give before assuming the match ended/never started and re-starting the cycle. this adds uo to MATCH_DURATION
MAX_MATCHES_PER_RUN = None                         # how many matches the script will record before stopping by itself. leave "None" or 0 for infinite
MAX_RUNTIME_MINUTES = None                         # how many minutes the script will run before stopping by itself. leave "None" or 0 for infinite
```
