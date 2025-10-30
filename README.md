# BakeRank Bot - Complete Setup Guide

## 🎮 What is BakeRank?
An interactive Twitch stream game where viewers bake virtual pastries, climb ranks, and trigger animations on your stream overlay!

---

## 📦 NEW: GUI Version (Standalone EXE)

### For Users (No Python Required):
1. Run `BakeRankBot.exe` from the `dist` folder
2. Enter your credentials:
   - **OAuth Token**: Get from https://twitchtokengenerator.com/
   - **Client ID**: Get from Twitch Developer Console
   - **Channel Name**: Your Twitch username
3. Click "💾 Save Configuration"
4. Click "▶ Start Bot"
5. Add overlay to OBS: Browser Source → `http://localhost:8765`

### For Developers (Building the EXE):
1. Run `install_requirements.bat` (installs PyQt5, TwitchIO, etc.)
2. Run `build_exe.bat` (creates standalone .exe in `dist` folder)
3. Distribute `BakeRankBot.exe` + `overlay` folder to users

---

## 🔧 Original Terminal Version Setup

### Step 1: Install Dependencies
Double-click `install_requirements.bat` or run:
```
py -m pip install twitchio==2.9.1 websockets
```

### Step 2: Configure Bot
Edit `bakerank_bot.py` and set:
- `TOKEN` - Your OAuth token
- `CLIENT_ID` - Your Twitch Client ID  
- `CHANNEL` - Your channel name

### Step 3: Run Bot
Double-click `bakerank_bot.py` or run:
```
py bakerank_bot.py
```

---

## 🎨 Adding Custom Baked Goods

1. Add PNG images to the `overlay` folder
2. For **normal items**: Name them anything (e.g., `donut.png`, `cookie.png`)
3. For **legendary items** (1% chance): Name with `Legendary-` prefix (e.g., `Legendary-GoldenCake.png`)

Bot automatically detects all PNG files!

---

## 🎮 Twitch Commands

- **!bake** - Bake a pastry, gain 1 point, rank up
- **!TopBakers** - Show top 5 bakers on leaderboard

---

## 📊 Rank System

| Points | Rank |
|--------|------|
| 0 | Floury Beginner |
| 20 | Amateur Baker |
| 100 | Pastry Apprentice |
| 300 | Dough Master |
| 700 | Dessert Virtuoso |
| 1400 | Oven Overlord |
| 3000 | Legendary Patissier |
| 6000 | Yeast Beast |
| 12000 | Celestial Confectioner |

---

## 💥 Special Effects

- **Legendary Bake** (1% chance): Golden glow + explosion
- **Rank Up**: Pastry explosion animation
- **Explosion**: 12 pastries burst across the screen

---

## 🗄️ Database Management

Player data is stored in `bakerank_data.txt` - editable with Notepad!

Format:
```
username | bake_score | last_bake_time
vokerr | 150 | 1698674532.5
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
