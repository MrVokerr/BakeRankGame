# BakeRank Bot - Streamer Edition 🍞

# New project found at: https://github.com/MrVokerr/ChatCollect

## 🎮 What is BakeRank?
An interactive Twitch stream game where viewers bake virtual pastries, climb ranks, and trigger animations on your stream overlay! 

**Optimized for Streamers:** Designed to run lightly in the background without affecting your gaming performance.

---

## 🚀 Quick Start (GUI Version)

### 1. Setup
1. Run `BakeRankBot.exe` (Found in the main folder).
2. Enter your credentials:
   - **OAuth Token**: Get from [TwitchTokenGenerator](https://twitchtokengenerator.com/) (Select 'Custom Scope' -> enable `chat:read` and `chat:edit`).
   - **Channel Name**: Your Twitch username.
3. **Overlay Settings**:
   - **Show Banner in Overlay**: Toggle this checkbox to enable/disable the top notification banner in the overlay.
4. Click **"💾 Save Configuration"**.
5. Click **"▶ Start Bot"**.

### 2. Overlay Setup (OBS/Streamlabs)
1. Add a **Browser Source**.
2. Set URL to: `http://localhost:8765/overlay.html` (or point to the local file `overlay/overlay.html`).
3. Set Width/Height to your canvas size (e.g., 1920x1080).
4. Check "Shutdown source when not visible" and "Refresh browser when scene becomes active".

---

## 🎛️ GUI Controls

The new interface gives you full control over the game:

### **Events Control Panel**
Trigger special events to boost engagement. You can now set custom durations (in minutes) for each event!

*   **🚀 Rush Hour**: Reduces bake cooldowns to 10 seconds.
    *   *Input:* Duration in minutes.
    *   *Action:* Click **Start** to begin, **Stop** to end early.
*   **🍪 Bake Sale**: Community challenge to bake X items total.
    *   *Input:* Duration in minutes (Default: 20).
    *   *Action:* Participants get a **Michelin Star ⭐** if the goal is met.
*   **🧐 Food Critic**: The critic craves a specific item.
    *   *Input:* Duration in minutes.
    *   *Action:* First person to bake the craving gets a **+50 Point Bonus**.
*   **⚔️ Bake Off**: A PvP baking tournament!
    *   *Input:* Join duration in minutes.
    *   *Action:* Viewers type `!bakeoff` to join (Cost: 10 pts). Winner takes the entire pot!
    *   *Note:* A reminder is sent to chat halfway through the joining period.

### **Test Lab**
Test your overlay alerts without affecting player scores.
*   **Rarity**: Choose from Standard, Burnt, Shiny, Golden, or Legendary.
*   **Item**: Select any image from your overlay folder.
*   **Test Button**: Triggers the alert on stream immediately.

---

## 🎨 Customizing Baked Goods

1. Open the `overlay` folder.
2. **Normal Items**: Add any `.png` image (e.g., `croissant.png`, `bagel.png`) directly in the `overlay` folder.
3. **Legendary Items**: 
    *   **Option A (Recommended):** Place images in the `overlay/legendary/` subfolder.
    *   **Option B (Legacy):** Place images in the root folder with the prefix `Legendary-` (e.g., `Legendary-WeddingCake.png`).
    *   *Chance:* Viewers have a base 1% chance to bake these.

### 💎 Shiny Logic
When a viewer rolls a **Shiny** rarity (0.1% chance + Luck), the item is chosen from **BOTH** the Normal and Legendary pools! This means a Shiny bake could be a Shiny Croissant OR a Shiny Excalibur!

---

## 🎮 Twitch Commands for Viewers

*Commands are case-insensitive (e.g., `!bake`, `!BAKE`, `!Bake` all work).*

- **!bake** - Bake a pastry! Cooldown: 60s (10s during Rush Hour).
- **!eat [amount]** - Eat points to gain **Luck**.
    *   *1 Point = 5% Luck*.
    *   Higher luck increases chances for **Shiny** and **Golden** items on the *next* bake.
- **!topbakers** (Aliases: `!topbaker`, `!leaderboard`) - Displays the top 5 leaderboard in chat.
- **!bakeoff** - Join an active Bake Off tournament (Cost: 10 pts).

---

## 📊 Rank System

| Points | Rank |
|--------|------|
| 0 | Floury Beginner |
| 50 | Amateur Baker |
| 250 | Pastry Apprentice |
| 750 | Dough Master |
| 2000 | Dessert Virtuoso |
| 5000 | Oven Overlord |
| 10000 | Legendary Patissier |
| 25000 | Yeast Beast |
| 50000 | Celestial Confectioner |
| 100000 | God of Grain |

---

## 🛠️ For Developers / Building from Source

If you want to modify the code and rebuild the EXE:

1. **Install Python 3.x**.
2. **Install Dependencies**:
   ```bat
   install_requirements.bat
   ```
3. **Build EXE**:
   ```bat
   build_exe.bat
   ```
   *   This will compile the code, optimize assets, and place `BakeRankBot.exe` in the root folder.
   *   It automatically cleans up build artifacts.

### ⚡ Performance Notes
*   **Resource Optimization**: The bot uses a dynamic sleep cycle. It sleeps for 5 seconds when idle and switches to 1-second checks only when events are active.
*   **Asset Caching**: Images are cached to prevent disk lag during gameplay.
*   **Async I/O**: Database saves are non-blocking to ensure zero frame drops.

---

## 📂 File Structure
*   `BakeRankBot.exe` - The main application.
*   `bakerank_data.txt` - Player database (Do not edit while bot is running).
*   `bakerank_config.json` - Saves your token/channel.
*   `overlay/` - Folder for your images and the HTML overlay.

- **🚀 Rush Hour**: Cooldowns reduced to 10s for 2 minutes.
- **🍪 Bake Sale**: Community goal (150 items). Reward: **Michelin Star** ⭐.
- **🧐 Food Critic**: Spawns a critic craving a specific item. First to bake it gets **+50 Points**.

---

## 💥 Special Effects

- **Shiny Bake** (0.1% + Luck): Color-shifting glow + badge + explosion
- **Golden Bake** (5% + Luck): Golden glow + 3x points
- **Burnt Bake** (5%): Charred item + 0 points
- **Legendary Bake** (1% chance): Giant size + explosion + 5 points
- **Rank Up**: Pastry explosion animation
- **Explosion**: 12 pastries burst across the screen

---

## 🗄️ Database Management

Player data is stored in `bakerank_data.txt` - editable with Notepad!

Format:
```
username | bake_score | last_bake_time | luck | last_eat_time | michelin_stars | shinies
vokerr | 150 | 1698674532.5 | 25.0 | 1698674600.0 | 1 | 2
```

**WARNING**: Keep the `|` separators intact!

---

## ⚙️ Settings

### Enable Cooldown (60 seconds)
In `bakerank_bot.py` or `bakerank_gui.py`, find the section:
```python
# if now - last_bake_time < COOLDOWN:
#     remaining = int(COOLDOWN - (now - last_bake_time))
#     await ctx.send(f"⏳ @{username}, oven cooling... wait {remaining}s.")
#     return
```
Uncomment these 4 lines to enable cooldown.

---

## 🎥 OBS Overlay Setup

1. Add a **Browser Source** in OBS
2. Set URL to: `http://localhost:8765`
3. Width: `1920`, Height: `1080`
4. Check "Shutdown source when not visible"
5. Check "Refresh browser when scene becomes active"

For custom HTML: Use `overlay/overlay.html`

---

## 🐛 Troubleshooting

### "Missing package: websockets" or "Missing package: twitchio"
Run `install_requirements.bat`

### "Bot is already running"
Close all Python windows or run in PowerShell:
```
taskkill /F /IM python.exe
```

### .exe closes immediately
Make sure `overlay` folder is in the same directory as the .exe

### Python not found on different drive
The batch file auto-detects Python in common locations. If it fails, manually run:
```
py -m pip install -r requirements.txt
```

---

## 📁 File Structure

```
BakeRankGame/
├── bakerank_gui.py          # GUI version (PyQt5)
├── bakerank_bot.py          # Terminal version
├── overlay/
│   ├── overlay.html         # Browser source overlay
│   ├── donut.png
│   ├── croissant.png
│   ├── Legendary-GoldenCake.png
│   └── ... (your PNG files)
├── bakerank_data.txt        # Player database (auto-created)
├── bakerank_config.json     # GUI config (auto-created)
├── requirements.txt         # Python dependencies
├── install_requirements.bat # Dependency installer
├── build_exe.bat           # EXE builder
└── dist/
    └── BakeRankBot.exe     # Standalone executable
```

---

## 🚀 Quick Start for Streamers

1. Download `BakeRankBot.exe` + `overlay` folder
2. Run `BakeRankBot.exe`
3. Enter Token, Client ID, Channel Name
4. Click "Save Configuration" then "Start Bot"
5. Add overlay to OBS: Browser Source → `http://localhost:8765`
6. Done! Viewers can now use `!bake` command

---

## 💡 Tips

- Use "💥 Test Explosion" button in GUI to test overlay without counting toward scores
- Edit `bakerank_data.txt` with Notepad to manually adjust player scores
- Legendary items are rare (1% chance) but trigger explosions
- Rank-ups trigger explosions automatically
- All PNG files in `overlay` folder are auto-detected

---

## 📝 License

Free to use and modify for personal and commercial streaming!

---

## 🆘 Support

If you encounter issues:
1. Check the Activity Log in the GUI
2. Verify your Token and Channel Name are correct
3. Ensure `overlay` folder contains PNG files
4. Check OBS Browser Source is pointing to `http://localhost:8765`

For Token: https://twitchtokengenerator.com/
Select "Chat Bot" and copy the "Access Token"
