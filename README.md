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
4. Run `ievr.exe`  
5. Press **Start Bot**  
6. The tool will automatically:
   - Detect the game window  
   - Ask you to hover over specific buttons to capture offsets  
   - Begin the matchmaking loop  
   - Detect when a match starts  
   - Detect when a match ends  
   - Repeat until you stop it  

All timing behaviors are customizable inside `_internal/settings.py`.

---

## 🛠 Customization

You can freely tweak all timings and behaviors:

```python
AUTO_MODE_KEY = "u"         # key to enable auto-mode
FIRST_WAIT = 45             # wait after clicking "Ranked Match"
SECOND_WAIT = 80            # wait before enabling auto-mode
MATCH_DURATION = 780        # fallback time if HUD detection fails
SEARCH_CHECK_INTERVAL = 20  # how often to check match status
POST_MATCH_CLICKS = 20      # number of clicks to return to menu
```
