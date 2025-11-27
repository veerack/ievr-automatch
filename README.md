# ⚡ IEVR Helper – Inazuma Eleven Victory Road Automation

*A modern, GUI-based automation toolkit for Inazuma Eleven: Victory Road (PC)*

---

## ⚠️ Disclaimer

This project is provided **strictly for educational, research and accessibility purposes**.

It **does NOT**:

* modify game files
* edit or scan memory
* inject code
* hook APIs or bypass protections
* interfere with network traffic

IEVR Helper only automates **human-like input at OS level** (mouse, keyboard or virtual controller), similar to tools like AutoHotkey or macro software.

The author is **not affiliated with LEVEL‑5** or any publisher.
Users are solely responsible for their usage.
If LEVEL‑5 or GitHub request removal, the repository will be taken down immediately.

---

## ✨ Features

### Core

* ✅ Fully graphical interface (no CLI required)
* ✅ Ranked Match auto-loop
* ✅ Automatic game window detection & focusing
* ✅ Smart pixel detection for:

  * Match finding
  * Match start
  * Match end / opponent disconnect
* ✅ Interactive calibration system for offsets
* ✅ Persistent settings system
* ✅ Safe input abstraction layer

### Trainers

* 🟢 **Blue Beans Trainer** – automated cycle
* 💗 **Pink Beans Trainer** – automated cycle
* 🍜 **Ramen Trainer** – automation logic
* 🔧 Additional bean trainers marked as **W.I.P**

### Advanced

* 🎮 Optional Virtual Controller mode (Chiaki4Deck + ViGEmBus)
* 🔄 Dynamic mode switching
* 💾 Auto-saving configuration
* 📋 Log panel + clipboard export
* 🧠 Smart fail-recovery logic

---

## 📦 Download

➡ **Latest Release:**
[https://github.com/veerack/ievr-automatch/releases](https://github.com/veerack/ievr-automatch/releases)

Simply download and run:

```
IEVR.exe
```

---

## 🖥 Requirements

* Windows 10 / 11
* Inazuma Eleven: Victory Road (PC)
* Keyboard & Mouse

---

## 🎮 Game Setup (IMPORTANT)

The tool is currently calibrated for:

```
Window Mode: Windowed
Resolution: 1024 x 576
```

Other resolutions may partially work, but are **not officially supported yet**.
If you test alternative resolutions, please open an issue so support can be added.

---

## 🚀 How To Use (Ranked Example)

1. Launch **Inazuma Eleven: Victory Road**
2. Set resolution to:
   * Windowed
   * 1024×576
3. Go to:
   `Competitive Game → Online Match`
4. Run **IEVR.exe**
5. Choose the mode:
   * Ranked Match
6. Press **Start Bot**

The tool will then automatically:

* Detect the game window
* Focus it if needed
* Ask for calibration (first run only (not always))
* Start automation
* Detect match flow & failures
* Loop indefinitely until stopped

---

## 🧠 Modes Explained

| Mode                     | Status       | Description                      
| ------------------------ | ------------ | -------------------------------- 
| Ranked Match             | ✅ Stable    | Fully automated matchmaking loop
| Ramen Trainer            | ✅ ON        | Automated ramen training routine
| Blue Beans Trainer       | ✅ ON        | Farming routine for Blue Beans  
| Pink Beans Trainer       | ✅ ON        | Farming routine for Pink beans           
| Red Beans Trainer        | 🚧 W.I.P     | In development                   
| Green Beans Trainer      | 🚧 W.I.P     | In development                   
| Yellow Beans Trainer     | 🚧 W.I.P     | In development                   
| Orange Beans Trainer     | 🚧 W.I.P     | In development                   
| Light Blue Beans Trainer | 🚧 W.I.P     | Planned                          

---

## 🛠 Advanced Configuration

After first launch, a folder will appear:

```
IEVR/base/settings.py
```

You can manually tweak behaviour here:

```python
GAME_WINDOW_TITLE = 'Inazuma Eleven: Victory Road'
AUTO_MODE_KEY = 'u'

DELAY_BEFORE_START = 5.0
FIRST_WAIT = 15.0
SECOND_WAIT = 80.0
MATCH_DURATION = 780.0
POST_MATCH_CLICKS = 20
POST_MATCH_CLICK_INTERVAL = 0.3
SEARCH_CHECK_INTERVAL = 20.0

PLAY_BUTTON_OFFSET = (292, 247)
ANNUL_PIXEL_OFFSET = (499, 375)
ANNUL_PIXEL_COLOR = (250, 253, 254)
END_BUTTON_OFFSET = (60, 57)
END_BUTTON_COLOR = (172, 158, 48)
LVL_75_PLUS = False
MATCH_TIMEOUT_MARGIN = 120.0
MAX_MATCHES_PER_RUN = None
MAX_RUNTIME_MINUTES = None

RAMEN_INITIAL_DELAY = 10.0
RAMEN_FIRST_ENTER_COUNT = 4
RAMEN_FIRST_ENTER_DELAY = 1.0
RAMEN_AFTER_FIRST_WAIT = 5.0
RAMEN_W_MIN = 7
RAMEN_W_MAX = 8
RAMEN_W_DELAY = 1.5
RAMEN_LONG_WAIT_MIN = 15.0
RAMEN_LONG_WAIT_MAX = 16.0
RAMEN_FINAL_ENTER_COUNT = 2
RAMEN_FINAL_ENTER_DELAY = 1.5
RAMEN_AFTER_FINAL_WAIT = 5.0
CHIAKI4DECK = False

# ------- Pink Beans trainer defaults -------
PINK_INITIAL_DELAY = 5.0              

PINK_ENTER1_DELAY = 1.2               
PINK_ENTER2_DELAY = 0.7               
PINK_UP_DELAY = 0.1                  
PINK_ENTER3_DELAY = 0.2               
PINK_ENTER4_DELAY = 7.0              

PINK_ESC_AFTER_DELAY = 0.1            
PINK_V_AFTER_DELAY = 2.0              

PINK_V_HOLD_DURATION = 2.0           
PINK_AFTER_HOLD_DELAY = 3.0           

PINK_DOWN_DELAY = 0.5                
PINK_FINAL_ENTER_DELAY = 4.0          

# ---- Blue Beans trainer (Hecaton Stairway) ----
BLUE_INITIAL_DELAY    = 5.0   

BLUE_ENTER1_DELAY     = 1.2   
BLUE_ENTER2_DELAY     = 0.7   
BLUE_UP_DELAY         = 0.3   
BLUE_ENTER3_DELAY     = 0.3   
BLUE_ENTER4_DELAY     = 7.0   

BLUE_A1_DELAY         = 4.5   
BLUE_S1_DELAY         = 8.5   
BLUE_A2_DELAY         = 4.0   
BLUE_S2_DELAY         = 10.0 
BLUE_A3_DELAY         = 3.0   
BLUE_S3_DELAY         = 5.0   
BLUE_A4_DELAY         = 12.0  

BLUE_ENTER5_DELAY     = 1.5   
BLUE_COOLDOWN_DELAY   = 70.0 
```

⚠ Editing incorrect values may break automation behaviour.

---

## 🧩 Input System

IEVR Helper dynamically switches between:

* Keyboard & mouse input
* Virtual DS4 controller (via ViGEmBus)

This allows it to work with:

* Normal PC play
* Chiaki4Deck streaming setups

---

## 📊 Logging

The interface includes a real-time log panel that shows:

* Actions taken
* State changes
* Errors & warnings
* Window focus results

Logs can be exported to clipboard with one click.

---

## 🗺 Roadmap

* ✅ Multiple trainer systems
* ✅ Improved UI/UX
* 🔄 Resolution auto-scaling
* 🎯 Smart AI training detection
* 🌐 Multi-monitor optimization
* 📦 Preset profiles

---

## 💬 Support & Issues

Found a bug or want feature support?

Open an issue here:
👉 [https://github.com/veerack/ievr-automatch/issues](https://github.com/veerack/ievr-automatch/issues)

---

## 📜 License

MIT License

You are free to fork, modify and experiment with this project, provided attribution is maintained.

---

*IEVR Helper is a passion project built for automation experimentation, not competitive exploitation. Use responsibly.*
