import asyncio
import time
import json
import random
import os
import glob
import sys
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QTextEdit, QGroupBox, QMessageBox)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QFont
import websockets
from twitchio.ext import commands

CONFIG_FILE = "bakerank_config.json"
DB_PATH = "bakerank_data.txt"
OVERLAY_FOLDER = "overlay"
COOLDOWN = 60

# ============ TEXT FILE DATABASE ============
def load_player_data():
    """Load player data from text file"""
    if not os.path.exists(DB_PATH):
        return {}
    
    players = {}
    try:
        with open(DB_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split('|')
                if len(parts) == 3:
                    username = parts[0].strip()
                    bake_score = int(parts[1].strip())
                    last_bake_time = float(parts[2].strip())
                    players[username] = {
                        'bake_score': bake_score,
                        'last_bake_time': last_bake_time
                    }
    except Exception as e:
        print(f"⚠️ Warning: Could not load database: {e}")
    return players

def save_player_data(players):
    """Save player data to text file"""
    try:
        with open(DB_PATH, 'w', encoding='utf-8') as f:
            f.write("# BakeRank Player Database - Edit with Notepad\n")
            f.write("# Format: username | bake_score | last_bake_time\n")
            f.write("# WARNING: Keep the | separators intact!\n\n")
            for username, data in sorted(players.items(), key=lambda x: x[1]['bake_score'], reverse=True):
                f.write(f"{username} | {data['bake_score']} | {data['last_bake_time']}\n")
    except Exception as e:
        print(f"❌ Error saving database: {e}")

player_data = load_player_data()

# ============ BAKED GOODS HELPERS ============
def get_available_baked_goods():
    """Scan overlay folder for normal PNG files"""
    png_files = glob.glob(os.path.join(OVERLAY_FOLDER, "*.png"))
    if not png_files:
        return ["croissant.png", "donut.png", "Pancakes.png"]
    normal_items = [os.path.basename(f) for f in png_files if not os.path.basename(f).startswith("Legendary-")]
    return normal_items if normal_items else [os.path.basename(f) for f in png_files]

def get_legendary_baked_goods():
    """Get legendary baked goods"""
    png_files = glob.glob(os.path.join(OVERLAY_FOLDER, "Legendary-*.png"))
    return [os.path.basename(f) for f in png_files]

def choose_baked_good():
    """Choose a baked good with 1% legendary chance"""
    legendary_items = get_legendary_baked_goods()
    normal_items = get_available_baked_goods()
    
    if legendary_items and random.random() < 0.01:
        return random.choice(legendary_items), True
    else:
        return random.choice(normal_items), False

def format_item_name(filename):
    """Convert filename to display name"""
    name = os.path.splitext(filename)[0]
    return name.replace("_", " ").replace("-", " ").title()

# ============ RANK SYSTEM ============
RANKS = [
    (0, "Floury Beginner"),
    (20, "Amateur Baker"),
    (100, "Pastry Apprentice"),
    (300, "Dough Master"),
    (700, "Dessert Virtuoso"),
    (1400, "Oven Overlord"),
    (3000, "Legendary Patissier"),
    (6000, "Yeast Beast"),
    (12000, "Celestial Confectioner")
]

def get_rank_title(score):
    for threshold, title in reversed(RANKS):
        if score >= threshold:
            return title
    return RANKS[0][1]

# ============ WEBSOCKET SERVER ============
overlay_clients = set()

async def handle_overlay_connection(websocket):
    """Handle incoming overlay connections"""
    overlay_clients.add(websocket)
    try:
        async for _ in websocket:
            pass
    finally:
        overlay_clients.remove(websocket)

async def broadcast_to_overlays(message):
    """Send message to all connected overlays"""
    if overlay_clients:
        data = json.dumps(message)
        await asyncio.gather(*[client.send(data) for client in overlay_clients], return_exceptions=True)

async def start_overlay_server():
    """Start WebSocket server"""
    async with websockets.serve(handle_overlay_connection, "0.0.0.0", 8765):
        await asyncio.Future()

# ============ TWITCH BOT ============
class BakeRankBot(commands.Bot):
    def __init__(self, token, channel, log_callback):
        super().__init__(token=token, prefix="!", initial_channels=[channel])
        self.log_callback = log_callback
        self.channel_name = channel

    async def event_ready(self):
        self.log_callback(f"✅ Bot logged in as {self.nick}")
        self.log_callback(f"📺 Connected to channel: {self.channel_name}")
        self.log_callback(f"🎮 Commands: !bake, !TopBakers")
        self.log_callback("-" * 50)

    @commands.command(name="bake")
    async def bake(self, ctx):
        username = ctx.author.name.lower()
        now = time.time()

        if username not in player_data:
            player_data[username] = {'bake_score': 0, 'last_bake_time': 0}
        
        bake_score = player_data[username]['bake_score']
        last_bake_time = player_data[username]['last_bake_time']

        # COOLDOWN CHECK (60 seconds per user)
        if now - last_bake_time < COOLDOWN:
            remaining = int(COOLDOWN - (now - last_bake_time))
            await ctx.send(f"⏳ @{username}, oven cooling... wait {remaining}s.")
            return

        old_rank_title = get_rank_title(bake_score)
        bake_score += 1
        new_rank_title = get_rank_title(bake_score)

        player_data[username]['bake_score'] = bake_score
        player_data[username]['last_bake_time'] = now
        save_player_data(player_data)

        ranked_up = old_rank_title != new_rank_title
        bake_item, is_legendary = choose_baked_good()
        item_display_name = format_item_name(bake_item)
        trigger_explosion = ranked_up or is_legendary
        
        if is_legendary:
            self.log_callback(f"✨ {username} baked a LEGENDARY {item_display_name}! ✨")
        else:
            self.log_callback(f"🍞 {username} baked a {item_display_name}!")
            
        if ranked_up:
            self.log_callback(f"🎉 {username} ranked up to {new_rank_title}!")
        
        if is_legendary:
            await ctx.send(f"✨ @{username} baked a LEGENDARY {item_display_name}! ✨ ({new_rank_title}) | Score: {int(bake_score)}")
        else:
            await ctx.send(f"🍞 @{username} baked a {item_display_name}! ({new_rank_title}) | Score: {int(bake_score)}")

        message = {
            "event": "bake",
            "user": username,
            "rank": new_rank_title,
            "score": int(bake_score),
            "item": bake_item,
            "is_legendary": is_legendary,
            "trigger_explosion": trigger_explosion,
            "ranked_up": ranked_up
        }
        await broadcast_to_overlays(message)

    @commands.command(name="TopBakers")
    async def topbakers(self, ctx):
        await self.send_leaderboard_to_chat(ctx)

    async def fetch_leaderboard(self):
        sorted_players = sorted(player_data.items(), key=lambda x: x[1]['bake_score'], reverse=True)[:5]
        board = []
        for username, data in sorted_players:
            board.append({
                "username": username,
                "score": int(data['bake_score']),
                "title": get_rank_title(data['bake_score'])
            })
        return board

    async def send_leaderboard_to_chat(self, ctx):
        board = await self.fetch_leaderboard()
        if not board:
            await ctx.send("No bakers yet.")
            return
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        msg = " | ".join(
            f"{medals[i]} {b['username']} ({b['title']}) - {b['score']}"
            for i, b in enumerate(board)
        )
        await ctx.send(msg)

# ============ BOT THREAD ============
class BotThread(QThread):
    log_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    
    def __init__(self, token, channel):
        super().__init__()
        self.token = token
        self.channel = channel
        self.bot = None
        self.loop = None
        
    def log(self, message):
        self.log_signal.emit(message)
        
    def run(self):
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            # Start overlay server
            overlay_task = self.loop.create_task(start_overlay_server())
            self.log("🍞 Overlay server started on ws://localhost:8765")
            
            # Start bot
            self.bot = BakeRankBot(self.token, self.channel, self.log)
            bot_task = self.loop.create_task(self.bot.start())
            
            self.loop.run_until_complete(asyncio.gather(overlay_task, bot_task))
        except Exception as e:
            self.error_signal.emit(str(e))
            
    def stop(self):
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)

# ============ MAIN GUI WINDOW ============
class BakeRankGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.bot_thread = None
        self.config = self.load_config()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("BakeRank Bot - GUI Edition")
        self.setGeometry(100, 100, 700, 600)
        
        # Dark mode stylesheet
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
                font-size: 11pt;
            }
            QGroupBox {
                background-color: #252525;
                border: 2px solid #3d3d3d;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLabel {
                color: #e0e0e0;
                background-color: transparent;
            }
            QLineEdit {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                padding: 5px;
                color: #e0e0e0;
                selection-background-color: #4a4a4a;
            }
            QLineEdit:focus {
                border: 1px solid #0d7377;
            }
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                padding: 8px;
                color: #e0e0e0;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
                border: 1px solid #4d4d4d;
            }
            QPushButton:pressed {
                background-color: #1d1d1d;
            }
            QTextEdit {
                background-color: #0d0d0d;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                color: #e0e0e0;
                selection-background-color: #4a4a4a;
            }
        """)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Configuration Group
        config_group = QGroupBox("Bot Configuration")
        config_layout = QVBoxLayout()
        
        # Token
        token_layout = QHBoxLayout()
        token_layout.addWidget(QLabel("OAuth Token:"))
        self.token_input = QLineEdit()
        self.token_input.setEchoMode(QLineEdit.Password)
        self.token_input.setText(self.config.get('token', ''))
        token_layout.addWidget(self.token_input)
        config_layout.addLayout(token_layout)
        
        # Client ID
        client_layout = QHBoxLayout()
        client_layout.addWidget(QLabel("Client ID:"))
        self.client_input = QLineEdit()
        self.client_input.setEchoMode(QLineEdit.Password)
        self.client_input.setText(self.config.get('client_id', ''))
        client_layout.addWidget(self.client_input)
        config_layout.addLayout(client_layout)
        
        # Channel
        channel_layout = QHBoxLayout()
        channel_layout.addWidget(QLabel("Channel Name:"))
        self.channel_input = QLineEdit()
        self.channel_input.setText(self.config.get('channel', ''))
        channel_layout.addWidget(self.channel_input)
        config_layout.addLayout(channel_layout)
        
        # Save Config Button
        self.save_config_btn = QPushButton("💾 Save Configuration")
        self.save_config_btn.clicked.connect(self.save_configuration)
        config_layout.addWidget(self.save_config_btn)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # Control Buttons
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶ Start Bot")
        self.start_btn.clicked.connect(self.start_bot)
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px; border: none;")
        btn_layout.addWidget(self.start_btn)
        
        self.test_explosion_btn = QPushButton("💥 Test Explosion")
        self.test_explosion_btn.clicked.connect(self.test_explosion)
        self.test_explosion_btn.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold; padding: 10px; border: none;")
        btn_layout.addWidget(self.test_explosion_btn)
        
        self.test_legendary_btn = QPushButton("✨ Test Legendary")
        self.test_legendary_btn.clicked.connect(self.test_legendary)
        self.test_legendary_btn.setStyleSheet("background-color: #FFD700; color: black; font-weight: bold; padding: 10px; border: none;")
        btn_layout.addWidget(self.test_legendary_btn)
        
        layout.addLayout(btn_layout)
        
        # Log Display
        log_group = QGroupBox("Activity Log")
        log_layout = QVBoxLayout()
        
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_display)
        
        self.clear_log_btn = QPushButton("🗑 Clear Log")
        self.clear_log_btn.clicked.connect(self.clear_log)
        log_layout.addWidget(self.clear_log_btn)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        self.log("🍞 BakeRank Bot GUI Ready")
        self.log("Configure your settings and click 'Start Bot'")
        
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_configuration(self):
        config = {
            'token': self.token_input.text(),
            'client_id': self.client_input.text(),
            'channel': self.channel_input.text()
        }
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
            self.log("✅ Configuration saved successfully")
            QMessageBox.information(self, "Success", "Configuration saved!")
        except Exception as e:
            self.log(f"❌ Error saving config: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save config: {e}")
    
    def start_bot(self):
        token = self.token_input.text().strip()
        channel = self.channel_input.text().strip()
        
        if not token or not channel:
            QMessageBox.warning(self, "Missing Info", "Please enter Token and Channel Name!")
            return
        
        self.log("=" * 50)
        self.log("🍞 Starting BakeRank Bot...")
        self.log("=" * 50)
        
        self.bot_thread = BotThread(token, channel)
        self.bot_thread.log_signal.connect(self.log)
        self.bot_thread.error_signal.connect(self.show_error)
        self.bot_thread.start()
        
        self.start_btn.setEnabled(False)
        
    def stop_bot(self):
        if self.bot_thread:
            self.log("🛑 Stopping bot...")
            self.bot_thread.stop()
            self.bot_thread.wait()
            self.bot_thread = None
        
        self.log("✅ Bot stopped")
        
    def test_explosion(self):
        """Send test explosion to overlay (doesn't count toward scores)"""
        bake_item, is_legendary = choose_baked_good()
        item_display_name = format_item_name(bake_item)
        
        message = {
            "event": "bake",
            "user": "TEST",
            "rank": "Test Mode",
            "score": 0,
            "item": bake_item,
            "is_legendary": is_legendary,
            "trigger_explosion": True,
            "ranked_up": False
        }
        
        asyncio.run(broadcast_to_overlays(message))
        self.log(f"💥 TEST EXPLOSION: {item_display_name}")
    
    def test_legendary(self):
        """Send test legendary bake to overlay (doesn't count toward scores)"""
        legendary_items = get_legendary_baked_goods()
        
        if not legendary_items:
            self.log("⚠️ No legendary items found! Add Legendary-*.png files to overlay folder.")
            QMessageBox.warning(self, "No Legendaries", "No legendary items found!\n\nAdd PNG files starting with 'Legendary-' to the overlay folder.")
            return
        
        # Pick random legendary item
        bake_item = random.choice(legendary_items)
        item_display_name = format_item_name(bake_item)
        
        message = {
            "event": "bake",
            "user": "TEST",
            "rank": "Test Mode",
            "score": 0,
            "item": bake_item,
            "is_legendary": True,
            "trigger_explosion": True,
            "ranked_up": False
        }
        
        asyncio.run(broadcast_to_overlays(message))
        self.log(f"✨ TEST LEGENDARY: {item_display_name} ✨")
        
    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_display.append(f"[{timestamp}] {message}")
        self.log_display.verticalScrollBar().setValue(
            self.log_display.verticalScrollBar().maximum()
        )
        
    def show_error(self, error):
        self.log(f"❌ ERROR: {error}")
        QMessageBox.critical(self, "Bot Error", f"An error occurred:\n{error}")
        self.stop_bot()
        
    def clear_log(self):
        self.log_display.clear()
        
    def closeEvent(self, event):
        # Auto-stop bot when window closes
        if self.bot_thread and self.bot_thread.isRunning():
            self.log("🛑 Closing application - stopping bot...")
            self.stop_bot()
        event.accept()

# ============ MAIN ============
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BakeRankGUI()
    window.show()
    sys.exit(app.exec_())
