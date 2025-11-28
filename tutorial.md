
![ChatGPT Image Nov 28, 2025, 05_13_57 PM](https://github.com/user-attachments/assets/c46cc579-1e2a-440a-8bf4-3bca1da849c2)

# Start Here
> [!CAUTION]
> First and foremost: this script is provided solely for accessibility purposes, and whoever decides to follow through is aware of the risk. The author (me) will not be responsible for any issue with the user's accounts in the future.
> We're not injecting or editing the game in any sort of way, but the EAC (might) still consider this in the "Macroes" category of things. That's your warning, proceed only if you understand this.

# Installation
Before proceeding to install, make sure your computer has atleast the following required things:
- Windows **ONLY** (10/11)
- No software that could block the execution of automated inputs (virtual inputs). If so, allow `IEVR.exe` in the software to not end up in weird issues.

Once those are set, proceed with downloading the application from the following link, and make sure you're always downloading the **Latest** (labeled in green) release:
https://github.com/veerack/ievr-automatch/releases
<img width="898" height="129" alt="image" src="https://github.com/user-attachments/assets/803c0ad2-bb4b-479f-b142-81a0bc463b6e" />

Once downloaded, extract the `.zip` file, place the folder you got by extracting the zip anywhere easily accessible. Open it and you should be having the following folder content
<img width="643" height="90" alt="image" src="https://github.com/user-attachments/assets/8c713d3c-d2cf-4737-8c32-3af3d604bc52" />

Open `IEVR.exe` and that is the main application, containing all the logic and the settings. First thing first, let's make a small walkthrough of the App.

## Structure
<img width="1198" height="711" alt="Screenshot_22" src="https://github.com/user-attachments/assets/ca2634bb-496a-4b23-855b-2d82a3451957" />
The application is divided in clean sections, each one containing "things" and each one of those have a purpose, starting with:

- 🟨 **Mode Selector**: This is where you can select which type of script/automation you want to run. It contains all the different trainers and its your only way to change the app mode.

- 🟪 **Start & Stop**: After selecting which mode to run the script on, use these two buttons to Start and/or Stop it from running, effectively giving you full control over it.

- 🩷 **System Info** (sorry, no pink square emoji lol): Here the application will display general information about the system. You can consult it if you think something's not being registered correctly (such as mouse clicks and/or keyboard inputs).

- 🟧 **Footer & Quit**: As simple as that. Quit closes the application even if something's still running.
 
- 🟥 **Tabs**: The application features are divided in different tabs. For example, the `Logs` tab will show only things related to general app Logging, such as app startup message, script logs, script actions and so on.
 
  - 🟩 **Logs Tab Tools**: These buttons will show up only when you're using the `Logs` tab. They are simple utilites which can be handy in specific situations. For example, if you see the script moving the mouse and clicking in the wrong place on the game window, you can use `Recalibrate Offsets` to, well, recalibrate the "coordinates" on the screen where the script has to interact (when using the `Ranked Match` mode).

- ⏺️ **Logs Terminal** (sorry, no cyan box emoji lol): This is where all the internal app logs will be shown. This is particularly useful to catch on errors, see whats the app doing exactly in that moment and, if needed, copy the current logs and send it over when creating an issue here/reporting a bug.

- 🟦 **Matches Tracker**: This is located in the bottom right of the app as i didn't want it to take up much space. A simple and (maybe useful) tracking for your ranked matches, which tells you how many matches has the script done since it was first ran, as well as the `Average` match time and `Last match` time (time as how long did the match last).

This brief explaination should have gotten you to a point where you now know how's the app structured and you should be able to navigate it easily and comfortably. Going further i will cover in depth the `Settings` tab and how to make this work also for **Playstation** users (yes, we have a way!), so follow on if you're interested, otherwise enjoy using it! :)

## Settings Tab
![2025-11-28 22-54-32 (2)](https://github.com/user-attachments/assets/22ab8c90-e527-4032-918a-9fb2433d3887)

This is the `Settings` tab, which contains ALL the stored settings needed for the app to work. While making the app, i kept in mind that everyone's computer is different and i wanted to make this as accessible and modular as i could, to let everyone tweak it to their liking.

> [!NOTE]
> All the default settings **usually** work for every machine, but in case something doesn't work properly, i strongly advise trying to tweak those settings before opening an issue here, it might save both of us some time!
> The settings of the app are, basically, `for how long`, `how much time i need to wait` kind of stuff for/after each specific action. The setting name should give it away, but to make it clear: each action the scripts do have a set time / set wait before executing the next one / set amount of clicks. All of that is what constructs the `Settings` tab, making it pratically fully customizable for everyone!
> For example: if the `AFTER_FINAL_ENTER` = **4s** for the **Blue Beans Trainer** is too low because your computer loads the map in 5 seconds after the training is done, you can just raise that value to **6.5s** for safety, `Apply Settings` (**ALWAYS**. Edited settings wont be saved if the `Apply Settings` button is not clicked) and try to start the script again, and you'll see the **Blue Beans Trainer** working flawlessly :)

# Core Timings / Safety & Limits
Both these sections cover settings related to `Ranked Match`, such as `POST_MATCH_CLICKS`, `TIMEOUT_MARGIN` and `FIRST_WAIT` / `SECOND_WAIT` / `EXPECTED_MATCH_DURATION`. The default values usually are fine and work for everyone, so i suggest to almost never tweak those, but feel free to do so if you need to.

# Ramen NPC Trainer
These settings are **specific** for the `Ramen Trainer` mode. You'd want to edit those if the `Ramen Trainer` mode doesn't work properly.

# Beans Settings
Below those two, will be listed different tabs for all the different `<bean_type> Beans Trainer` modes, each one having its own modular settings. This has been done this way since each special training for beans requires different timings and inputs, and so having a central settings for those wasn't ideal.

# Chiaki4Deck (Playstation Remote Play)
I had many people asking me for a Playstation integration for this script, but i couldn't properly make one due to.. well, i don't own one! Thanks to one of my friends who worked for 6h straight as my "laboratory guinea pig" and let me test my script using his PS5, we've achieved support also for that!

> [!IMPORTANT]
How's this done is basically: we'll remote into your PS5 using a program called `Chiaki4Deck` (or `chiaki-ng`) rather than `PS Remote Play`.. why? `PS Remote Play` does **NOT** support virutal controllers (which is what we're using here) and instead wants a physically cabled controller connected to the PC in order to work, so we had to find an alternative. Setting up `Chiaki` is very straightforward, but to not let people go in the dark, [a complete setup guide](https://streetpea.github.io/chiaki-ng/setup/configuration/#registering-your-playstation) is available here from their official documentation to help you configure the application!

Once done, opening back `IEVR.exe`, you want to enable the following setting in the `Settings` tab:
<img width="1375" height="147" alt="image" src="https://github.com/user-attachments/assets/6abdef57-2915-4878-b09d-c53db769bbc1" />

After enabling it and clicking `Apply Settings`, the application will ask for your consent to download the required packages/drivers for the `Virtual Controllers` (`vgamepad` + `ViGeMbUs`) to work. Simply accept and install whatever the app asks you to, and after doing so, restart the application, go into the `Settings` tab again, change the window title setting to `chiaki-ng`, enable the `Chiaki4Deck` setting and `Apply Settings`.

Once done, you're all set! Open `chiaki-ng`, connect to your playstation, open `Inazuma Eleven: Victory Road` and enjoy the app! 😄

