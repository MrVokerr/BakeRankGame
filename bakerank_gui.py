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
                             QTextEdit, QGroupBox, QMessageBox, QComboBox, QGridLayout)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QFont, QIntValidator
import websockets
from twitchio.ext import commands

CONFIG_FILE = "bakerank_config.json"
DB_PATH = "bakerank_data.txt"
OVERLAY_FOLDER = "overlay"
COOLDOWN = 60

# ============ OPTIMIZED MANAGERS ============
class AssetManager:
    def __init__(self, folder):
        self.folder = folder
        self._normal_items = []
        self._legendary_items = []
        self._last_scan = 0
        self._scan_interval = 60  # Cache for 60 seconds
        self.refresh()

    def _scan_if_needed(self):
        if time.time() - self._last_scan > self._scan_interval:
            self.refresh()

    def refresh(self):
        if not os.path.exists(self.folder):
            self._normal_items = ["croissant.png", "donut.png", "Pancakes.png"]
            self._legendary_items = []
            return

        # 1. Scan Root Folder (Normal Items + Old Legendary)
        root_files = glob.glob(os.path.join(self.folder, "*.png"))
        
        # 2. Scan 'legendary' Subfolder (New Legendary Items)
        legendary_folder = os.path.join(self.folder, "legendary")
        legendary_files = []
        if os.path.exists(legendary_folder):
            legendary_files = glob.glob(os.path.join(legendary_folder, "*.png"))

        self._legendary_items = []
        self._normal_items = []

        # Process Subfolder Legendaries (Preferred)
        for f in legendary_files:
            filename = os.path.basename(f)
            # Use forward slash for web compatibility
            self._legendary_items.append(f"legendary/{filename}")

        # Process Root Files
        for f in root_files:
            filename = os.path.basename(f)
            lower_name = filename.lower()
            
            # Backward compatibility for "Legendary-" prefix in root
            if lower_name.startswith("legendary-"):
                self._legendary_items.append(filename)
            else:
                self._normal_items.append(filename)
        
        # Fallback if no normal items found
        if not self._normal_items:
            self._normal_items = ["croissant.png", "donut.png", "Pancakes.png"]
        
        self._last_scan = time.time()

    @property
    def normal_items(self):
        self._scan_if_needed()
        return self._normal_items

    @property
    def legendary_items(self):
        self._scan_if_needed()
        return self._legendary_items

class PlayerDatabase:
    def __init__(self, filepath):
        self.filepath = filepath
        self.players = {}
        self.load()

    def load(self):
        if not os.path.exists(self.filepath):
            return
        
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    parts = line.split('|')
                    if len(parts) >= 3:
                        username = parts[0].strip()
                        try:
                            self.players[username] = {
                                'bake_score': int(parts[1].strip()),
                                'last_bake_time': float(parts[2].strip()),
                                'luck': float(parts[3].strip()) if len(parts) >= 4 else 0.0,
                                'last_eat_time': float(parts[4].strip()) if len(parts) >= 5 else 0.0,
                                'michelin_stars': int(parts[5].strip()) if len(parts) >= 6 else 0,
                                'shinies': int(parts[6].strip()) if len(parts) >= 7 else 0
                            }
                        except ValueError:
                            continue
        except Exception as e:
            print(f"⚠️ Warning: Could not load database: {e}")

    def save_blocking(self):
        """Blocking save for use in executor"""
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                f.write("# BakeRank Player Database - Edit with Notepad\n")
                f.write("# Format: username | bake_score | last_bake_time | luck | last_eat_time | michelin_stars | shinies\n")
                f.write("# WARNING: Keep the | separators intact!\n\n")
                
                sorted_players = sorted(self.players.items(), key=lambda x: x[1]['bake_score'], reverse=True)
                for username, data in sorted_players:
                    f.write(f"{username} | {data['bake_score']} | {data['last_bake_time']} | "
                            f"{data.get('luck', 0.0)} | {data.get('last_eat_time', 0.0)} | "
                            f"{data.get('michelin_stars', 0)} | {data.get('shinies', 0)}\n")
                
        except Exception as e:
            print(f"❌ Error saving database: {e}")

    async def save(self):
        """Async save wrapper"""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.save_blocking)

# Initialize Managers
asset_manager = AssetManager(OVERLAY_FOLDER)
db = PlayerDatabase(DB_PATH)
player_data = db.players

# ============ BAKED GOODS HELPERS ============
def choose_baked_good(rarity="standard"):
    """Choose a baked good based on rarity"""
    legendary = asset_manager.legendary_items
    normal = asset_manager.normal_items
    
    # Shiny: Pull from BOTH pools
    if rarity == "shiny":
        pool = normal + legendary
        if not pool: 
            return "croissant.png", False
        
        choice = random.choice(pool)
        is_legendary = choice in legendary
        return choice, is_legendary

    # Standard/Golden/Burnt: 0.1% chance of Legendary, else Normal
    if legendary and random.random() < 0.001:
        return random.choice(legendary), True
    else:
        return random.choice(normal), False

def format_item_name(filename):
    """Convert filename to display name"""
    # Handle paths like "legendary/cake.png" - get just the filename
    name = os.path.basename(filename)
    name = os.path.splitext(name)[0]
    
    # Case-insensitive removal of prefix
    lower_name = name.lower()
    if lower_name.startswith("legendary-") or lower_name.startswith("legendary_") or lower_name.startswith("legendary "):
        name = name[10:]
        
    return name.replace("_", " ").replace("-", " ").strip().title()

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
    def __init__(self, token, channel, log_callback, status_callback):
        super().__init__(token=token, prefix="!", initial_channels=[channel])
        self.token = token
        self.log_callback = log_callback
        self.status_callback = status_callback
        self.channel_name = channel
        
        # Event States
        self.rush_hour_active = False
        self.rush_hour_end_time = 0
        
        self.bake_sale_active = False
        self.bake_sale_target = 0
        self.bake_sale_current = 0
        self.bake_sale_end_time = 0
        self.bake_sale_participants = set()
        
        self.food_critic_active = False
        self.food_critic_craving = None
        self.food_critic_end_time = 0

    async def event_ready(self):
        self.log_callback(f"✅ Bot logged in as {self.nick}")
        self.log_callback(f"📺 Connected to channel: {self.channel_name}")
        self.log_callback(f"🎮 Commands: !bake, !TopBakers")
        self.log_callback("-" * 50)
        self.loop.create_task(self.game_loop())

    def _send_status_update(self):
        """Helper to send current event status to GUI"""
        try:
            now = time.time()
            status = {
                "rush_hour_active": self.rush_hour_active,
                "rush_hour_remaining": int(max(0, self.rush_hour_end_time - now)) if self.rush_hour_active else 0,
                "bake_sale_active": self.bake_sale_active,
                "bake_sale_remaining": int(max(0, self.bake_sale_end_time - now)) if self.bake_sale_active else 0,
                "bake_sale_progress": f"{self.bake_sale_current}/{self.bake_sale_target}" if self.bake_sale_active else "Inactive",
                "food_critic_active": self.food_critic_active,
                "food_critic_craving": format_item_name(self.food_critic_craving) if self.food_critic_active else "None",
                "food_critic_remaining": int(max(0, self.food_critic_end_time - now)) if self.food_critic_active else 0
            }
            if self.status_callback:
                self.status_callback(status)
        except Exception as e:
            print(f"Status Update Error: {e}")

    async def game_loop(self):
        """Background task to check event timers and update GUI"""
        while True:
            try:
                now = time.time()
                channel = self.get_channel(self.channel_name)

                # Check Rush Hour Expiry
                if self.rush_hour_active and now > self.rush_hour_end_time:
                    self.rush_hour_active = False
                    self.log_callback("🛑 Rush Hour ended!")
                    if channel:
                        await channel.send("🛑 The Rush Hour has ended! Cooldowns are back to normal.")
                    self._send_status_update()

                # Check Bake Sale Expiry (Failure)
                if self.bake_sale_active and now > self.bake_sale_end_time:
                    self.bake_sale_active = False
                    self.log_callback("😞 Bake Sale Failed (Time out)")
                    if channel:
                        await channel.send(f"😞 The Bake Sale ended! We only sold {self.bake_sale_current}/{self.bake_sale_target}. No stars awarded.")
                    self._send_status_update()

                # Check Food Critic Expiry
                if self.food_critic_active and now > self.food_critic_end_time:
                    self.food_critic_active = False
                    self.food_critic_craving = None
                    self.log_callback("😒 Food Critic left (Time out)")
                    if channel:
                        await channel.send("😒 The Food Critic got tired of waiting and left!")
                    self._send_status_update()

                # Send Status Update to GUI
                self._send_status_update()

                # Dynamic sleep: 1s if active, 5s if inactive to save resources
                if self.rush_hour_active or self.bake_sale_active or self.food_critic_active:
                    await asyncio.sleep(1)
                else:
                    await asyncio.sleep(5)

            except Exception as e:
                print(f"Game Loop Error: {e}")
                await asyncio.sleep(5)

    @commands.command(name="eat")
    async def eat(self, ctx):
        username = ctx.author.name.lower()
        parts = ctx.message.content.split()
        amount = 1
        if len(parts) > 1:
            try:
                amount = int(parts[1])
            except ValueError:
                pass
        
        if amount < 1:
            return

        if username not in player_data:
            await ctx.send(f"@{username}, you need to bake something first!")
            return

        now = time.time()
        last_eat = player_data[username].get('last_eat_time', 0)
        
        # 5 minute cooldown (300 seconds)
        if now - last_eat < 300:
            remaining = int(300 - (now - last_eat))
            await ctx.send(f"⏳ @{username}, you're too full! Wait {remaining}s.")
            return

        current_score = player_data[username]['bake_score']
        if current_score < amount:
            await ctx.send(f"@{username}, you don't have enough points! (Current: {current_score})")
            return

        # Consume points
        player_data[username]['bake_score'] -= amount
        
        # Add luck (5% per point)
        current_luck = player_data[username].get('luck', 0.0)
        added_luck = amount * 5.0
        new_luck = current_luck + added_luck
        player_data[username]['luck'] = new_luck
        player_data[username]['last_eat_time'] = now
        
        await db.save()
        
        await ctx.send(f"🍽️ @{username} ate {amount} points! Luck increased by {int(added_luck)}% (Total: {int(new_luck)}%). Good luck on your next bake!")

    @commands.command(name="bake")
    async def bake(self, ctx):
        username = ctx.author.name.lower()
        now = time.time()

        if username not in player_data:
            player_data[username] = {
                'bake_score': 0, 
                'last_bake_time': 0,
                'luck': 0.0,
                'last_eat_time': 0.0,
                'michelin_stars': 0,
                'shinies': 0
            }
        
        # Ensure all fields exist
        if 'luck' not in player_data[username]: player_data[username]['luck'] = 0.0
        if 'shinies' not in player_data[username]: player_data[username]['shinies'] = 0
        if 'michelin_stars' not in player_data[username]: player_data[username]['michelin_stars'] = 0
        
        bake_score = player_data[username]['bake_score']
        last_bake_time = player_data[username]['last_bake_time']
        luck = player_data[username]['luck']

        # COOLDOWN CHECK
        cooldown_time = COOLDOWN
        
        # Check Rush Hour
        if self.rush_hour_active:
            cooldown_time = 10 # Reduced cooldown
        
        if now - last_bake_time < cooldown_time:
            remaining = int(cooldown_time - (now - last_bake_time))
            await ctx.send(f"⏳ @{username}, oven cooling... wait {remaining}s.")
            return

        old_rank_title = get_rank_title(bake_score)
        
        # Rarity Logic
        shiny_prob = 0.0001 + (luck / 1000.0)
        golden_prob = 0.05 + (luck / 200.0)
        burnt_prob = 0.05
        
        rand_val = random.random()
        
        rarity = "standard"
        points_gained = 1
        
        if rand_val < shiny_prob:
            rarity = "shiny"
            points_gained = 10
            player_data[username]['shinies'] += 1
        elif rand_val < (shiny_prob + burnt_prob):
            rarity = "burnt"
            points_gained = 0
        elif rand_val < (shiny_prob + burnt_prob + golden_prob):
            rarity = "golden"
            points_gained = 3
        else:
            rarity = "standard"
            points_gained = 1
            
        # Reset luck
        player_data[username]['luck'] = 0.0
        
        # Choose item
        bake_item, is_legendary_item = choose_baked_good(rarity)
        item_display_name = format_item_name(bake_item)
        
        # Legendary Bonus (Override points if legendary, unless already higher)
        if is_legendary_item:
            if points_gained < 5:
                points_gained = 5

        # Food Critic Check
        critic_bonus = 0
        critic_msg = ""
        if self.food_critic_active and self.food_critic_craving == bake_item:
            critic_bonus = 50
            points_gained += critic_bonus
            self.food_critic_active = False
            self.food_critic_craving = None
            critic_msg = " 🧐 THE CRITIC IS PLEASED! (+50 Bonus)"
            self.log_callback(f"🧐 {username} satisfied the Food Critic!")
            self._send_status_update()

        bake_score += points_gained
        new_rank_title = get_rank_title(bake_score)

        player_data[username]['bake_score'] = bake_score
        player_data[username]['last_bake_time'] = now
        await db.save()

        ranked_up = old_rank_title != new_rank_title
        
        trigger_explosion = ranked_up or (rarity == "shiny") or (rarity == "golden") or is_legendary_item or (critic_bonus > 0)
        
        # Bake Sale Logic
        bake_sale_msg = ""
        if self.bake_sale_active:
            self.bake_sale_current += 1
            self.bake_sale_participants.add(username)
            remaining_sale = self.bake_sale_target - self.bake_sale_current
            if remaining_sale <= 0:
                self.bake_sale_active = False
                bake_sale_msg = " 🍪 BAKE SALE COMPLETE! All participants get a Michelin Star! ⭐"
                self.log_callback("🍪 Bake Sale Completed!")
                # Award stars
                for participant in self.bake_sale_participants:
                    if participant in player_data:
                        player_data[participant]['michelin_stars'] = player_data[participant].get('michelin_stars', 0) + 1
                await db.save()
            elif self.bake_sale_current % 10 == 0: # Notify every 10 items
                 bake_sale_msg = f" (Bake Sale: {self.bake_sale_current}/{self.bake_sale_target})"
            self._send_status_update()

        # Construct Message
        msg = ""
        if rarity == "burnt":
            msg = f"🔥 @{username} tried to bake a {item_display_name} but fell asleep! It's BURNT! (0 pts)"
            self.log_callback(f"🔥 {username} burnt a {item_display_name}")
        elif rarity == "shiny":
            msg = f"💎✨ SHINY!! @{username} baked a SHINY {item_display_name}! Unlocked a Badge! (+{points_gained} pts){critic_msg}{bake_sale_msg}"
            self.log_callback(f"💎 {username} got a SHINY {item_display_name}")
        elif rarity == "golden":
            msg = f"🌟 MASTERPIECE! @{username} baked a GOLDEN {item_display_name}! (+{points_gained} pts){critic_msg}{bake_sale_msg}"
            self.log_callback(f"🌟 {username} got a GOLDEN {item_display_name}")
        else:
            # Standard
            if is_legendary_item:
                msg = f"✨ @{username} baked a LEGENDARY {item_display_name}! (+{points_gained} pts){critic_msg}{bake_sale_msg}"
                self.log_callback(f"✨ {username} baked a LEGENDARY {item_display_name}")
            else:
                msg = f"🍞 @{username} baked a {item_display_name}! (+{points_gained} pts){critic_msg}{bake_sale_msg}"
                self.log_callback(f"🍞 {username} baked a {item_display_name}")
                
        msg += f" ({new_rank_title}) | Score: {int(bake_score)}"
        await ctx.send(msg)

        message = {
            "event": "bake",
            "user": username,
            "rank": new_rank_title,
            "score": int(bake_score),
            "item": bake_item,
            "is_legendary": is_legendary_item,
            "rarity": rarity,
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
        
        msg_parts = []
        for i, b in enumerate(board):
            username = b['username']
            shinies = player_data[username].get('shinies', 0)
            badge = "💎" if shinies > 0 else ""
            msg_parts.append(f"{medals[i]} {username}{badge} ({b['title']}) - {b['score']}")
            
        msg = " | ".join(msg_parts)
        await ctx.send(msg)

    async def start_rush_hour(self, duration_minutes=2):
        if self.rush_hour_active:
            self.log_callback("⚠️ Rush Hour already active!")
            return
            
        self.rush_hour_active = True
        duration_seconds = duration_minutes * 60
        self.rush_hour_end_time = time.time() + duration_seconds
        self.log_callback(f"🚀 Rush Hour started! ({duration_minutes} mins)")
        self._send_status_update()
        channel = self.get_channel(self.channel_name)
        if channel:
            await channel.send(f"🚀 The Rush Hour has started! Cooldowns are reduced to 10 seconds for the next {duration_minutes} minutes!")

    async def stop_rush_hour(self):
        if not self.rush_hour_active:
            return
        self.rush_hour_active = False
        self.log_callback("🛑 Rush Hour stopped manually.")
        self._send_status_update()
        channel = self.get_channel(self.channel_name)
        if channel:
            await channel.send("🛑 The Rush Hour has been stopped manually.")

    async def start_bake_sale(self, duration_minutes=20):
        if self.bake_sale_active:
            self.log_callback("⚠️ Bake Sale already active!")
            return

        self.bake_sale_active = True
        self.bake_sale_target = 150
        self.bake_sale_current = 0
        duration_seconds = duration_minutes * 60
        self.bake_sale_end_time = time.time() + duration_seconds
        self.bake_sale_participants = set()
        self.log_callback(f"🍪 Bake Sale started! Target: 150 Cookies ({duration_minutes} mins)")
        self._send_status_update()
        channel = self.get_channel(self.channel_name)
        if channel:
            await channel.send(f"🍪 Catering Order: 150 Baked Goods needed! The Bake Sale has started! You have {duration_minutes} minutes! (Reward: Michelin Star)")

    async def stop_bake_sale(self):
        if not self.bake_sale_active:
            return
        self.bake_sale_active = False
        self.log_callback("🛑 Bake Sale stopped manually.")
        self._send_status_update()
        channel = self.get_channel(self.channel_name)
        if channel:
            await channel.send("🛑 The Bake Sale has been stopped manually.")

    async def spawn_food_critic(self, duration_minutes=10):
        if self.food_critic_active:
            self.log_callback("⚠️ Food Critic already here!")
            return

        self.food_critic_active = True
        duration_seconds = duration_minutes * 60
        self.food_critic_end_time = time.time() + duration_seconds
        # Pick a random item
        items = asset_manager.normal_items
        self.food_critic_craving = random.choice(items)
        craving_name = format_item_name(self.food_critic_craving)
        
        self.log_callback(f"🧐 Food Critic arrived! Craving: {craving_name} ({duration_minutes} mins)")
        self._send_status_update()
        channel = self.get_channel(self.channel_name)
        if channel:
            await channel.send(f"🧐 The Food Critic has entered the chat! They crave a {craving_name}. First to bake it gets a bonus!")

    async def stop_food_critic(self):
        if not self.food_critic_active:
            return
        self.food_critic_active = False
        self.food_critic_craving = None
        self.log_callback("🛑 Food Critic left manually.")
        self._send_status_update()
        channel = self.get_channel(self.channel_name)
        if channel:
            await channel.send("🛑 The Food Critic has left the chat.")

# ============ BOT THREAD ============
class BotThread(QThread):
    log_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    status_signal = pyqtSignal(dict)
    
    def __init__(self, token, channel):
        super().__init__()
        self.token = token
        self.channel = channel
        self.bot = None
        self.loop = None
        
    def log(self, message):
        self.log_signal.emit(message)

    def update_status(self, status):
        self.status_signal.emit(status)
        
    def run(self):
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            # Start overlay server
            overlay_task = self.loop.create_task(start_overlay_server())
            self.log("🍞 Overlay server started on ws://localhost:8765")
            
            # Start bot
            self.bot = BakeRankBot(self.token, self.channel, self.log, self.update_status)
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
        self.setWindowTitle("Bake Rank")
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

        # Test Controls Group
        test_group = QGroupBox("Test")
        test_layout = QHBoxLayout()

        # Rarity Dropdown
        test_layout.addWidget(QLabel("Rarity:"))
        self.rarity_combo = QComboBox()
        self.rarity_combo.addItems(["Standard", "Burnt", "Shiny", "Golden", "Legendary"])
        test_layout.addWidget(self.rarity_combo)

        # Item Dropdown
        test_layout.addWidget(QLabel("Item:"))
        self.item_combo = QComboBox()
        # Populate items
        all_items = asset_manager.normal_items + asset_manager.legendary_items
        for filename in all_items:
            display_name = format_item_name(filename)
            self.item_combo.addItem(display_name, filename) # Store filename as user data
        test_layout.addWidget(self.item_combo)

        # Test Button
        self.custom_test_btn = QPushButton("🧪 Test")
        self.custom_test_btn.clicked.connect(self.test_custom_bake)
        self.custom_test_btn.setStyleSheet("background-color: #00BCD4; color: white; font-weight: bold; padding: 8px;")
        test_layout.addWidget(self.custom_test_btn)

        test_group.setLayout(test_layout)
        layout.addWidget(test_group)

        # Events Group
        events_group = QGroupBox("Events")
        events_layout = QGridLayout()
        
        # Validators
        int_validator = QIntValidator(1, 9999)

        # Rush Hour
        events_layout.addWidget(QLabel("🚀 Rush Hour"), 0, 0)
        self.rh_duration = QLineEdit("2")
        self.rh_duration.setValidator(int_validator)
        self.rh_duration.setFixedWidth(50)
        self.rh_duration.setPlaceholderText("Min")
        events_layout.addWidget(self.rh_duration, 0, 1)
        events_layout.addWidget(QLabel("minutes"), 0, 2)
        
        self.rush_hour_btn = QPushButton("Start")
        self.rush_hour_btn.clicked.connect(self.trigger_rush_hour)
        self.rush_hour_btn.setStyleSheet("background-color: #E91E63; color: white; font-weight: bold;")
        events_layout.addWidget(self.rush_hour_btn, 0, 3)

        self.stop_rh_btn = QPushButton("Stop")
        self.stop_rh_btn.clicked.connect(self.stop_rush_hour)
        self.stop_rh_btn.setStyleSheet("background-color: #555; color: white;")
        events_layout.addWidget(self.stop_rh_btn, 0, 4)
        
        # Bake Sale
        events_layout.addWidget(QLabel("🍪 Bake Sale"), 1, 0)
        self.bs_duration = QLineEdit("20")
        self.bs_duration.setValidator(int_validator)
        self.bs_duration.setFixedWidth(50)
        self.bs_duration.setPlaceholderText("Min")
        events_layout.addWidget(self.bs_duration, 1, 1)
        events_layout.addWidget(QLabel("minutes"), 1, 2)

        self.bake_sale_btn = QPushButton("Start")
        self.bake_sale_btn.clicked.connect(self.trigger_bake_sale)
        self.bake_sale_btn.setStyleSheet("background-color: #9C27B0; color: white; font-weight: bold;")
        events_layout.addWidget(self.bake_sale_btn, 1, 3)

        self.stop_bs_btn = QPushButton("Stop")
        self.stop_bs_btn.clicked.connect(self.stop_bake_sale)
        self.stop_bs_btn.setStyleSheet("background-color: #555; color: white;")
        events_layout.addWidget(self.stop_bs_btn, 1, 4)
        
        # Food Critic
        events_layout.addWidget(QLabel("🧐 Food Critic"), 2, 0)
        self.fc_duration = QLineEdit("10")
        self.fc_duration.setValidator(int_validator)
        self.fc_duration.setFixedWidth(50)
        self.fc_duration.setPlaceholderText("Min")
        events_layout.addWidget(self.fc_duration, 2, 1)
        events_layout.addWidget(QLabel("minutes"), 2, 2)

        self.food_critic_btn = QPushButton("Start")
        self.food_critic_btn.clicked.connect(self.trigger_food_critic)
        self.food_critic_btn.setStyleSheet("background-color: #607D8B; color: white; font-weight: bold;")
        events_layout.addWidget(self.food_critic_btn, 2, 3)

        self.stop_fc_btn = QPushButton("Stop")
        self.stop_fc_btn.clicked.connect(self.stop_food_critic)
        self.stop_fc_btn.setStyleSheet("background-color: #555; color: white;")
        events_layout.addWidget(self.stop_fc_btn, 2, 4)
        
        events_group.setLayout(events_layout)
        layout.addWidget(events_group)

        # Active Events Status Group
        status_group = QGroupBox("Active Events Status")
        status_layout = QHBoxLayout()

        # Rush Hour Status
        rh_layout = QVBoxLayout()
        rh_layout.addWidget(QLabel("🚀 Rush Hour"))
        self.rh_status_label = QLabel("Inactive")
        self.rh_status_label.setStyleSheet("color: #888;")
        rh_layout.addWidget(self.rh_status_label)
        status_layout.addLayout(rh_layout)

        # Bake Sale Status
        bs_layout = QVBoxLayout()
        bs_layout.addWidget(QLabel("🍪 Bake Sale"))
        self.bs_status_label = QLabel("Inactive")
        self.bs_status_label.setStyleSheet("color: #888;")
        bs_layout.addWidget(self.bs_status_label)
        status_layout.addLayout(bs_layout)

        # Food Critic Status
        fc_layout = QVBoxLayout()
        fc_layout.addWidget(QLabel("🧐 Food Critic"))
        self.fc_status_label = QLabel("Inactive")
        self.fc_status_label.setStyleSheet("color: #888;")
        fc_layout.addWidget(self.fc_status_label)
        status_layout.addLayout(fc_layout)

        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Log Display
        log_group = QGroupBox("Activity Log")
        log_layout = QVBoxLayout()
        
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_display)
        
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
        self.bot_thread.status_signal.connect(self.update_status_display)
        self.bot_thread.start()
        
        self.start_btn.setEnabled(False)
        
    def stop_bot(self):
        if self.bot_thread:
            self.log("🛑 Stopping bot...")
            self.bot_thread.stop()
            self.bot_thread.wait()
            self.bot_thread = None
        
        self.log("✅ Bot stopped")
        self.start_btn.setEnabled(True)
        self.rh_status_label.setText("Inactive")
        self.bs_status_label.setText("Inactive")
        self.fc_status_label.setText("Inactive")

    def update_status_display(self, status):
        # Rush Hour
        if status["rush_hour_active"]:
            self.rh_status_label.setText(f"ACTIVE\nTime: {status['rush_hour_remaining']}s")
            self.rh_status_label.setStyleSheet("color: #E91E63; font-weight: bold;")
        else:
            self.rh_status_label.setText("Inactive")
            self.rh_status_label.setStyleSheet("color: #888;")

        # Bake Sale
        if status["bake_sale_active"]:
            self.bs_status_label.setText(f"ACTIVE\nProgress: {status['bake_sale_progress']}\nTime: {status['bake_sale_remaining']}s")
            self.bs_status_label.setStyleSheet("color: #9C27B0; font-weight: bold;")
        else:
            self.bs_status_label.setText("Inactive")
            self.bs_status_label.setStyleSheet("color: #888;")

        # Food Critic
        if status["food_critic_active"]:
            self.fc_status_label.setText(f"ACTIVE\nCraving: {status['food_critic_craving']}\nTime: {status['food_critic_remaining']}s")
            self.fc_status_label.setStyleSheet("color: #607D8B; font-weight: bold;")
        else:
            self.fc_status_label.setText("Inactive")
            self.fc_status_label.setStyleSheet("color: #888;")
        
    def test_custom_bake(self):
        rarity_text = self.rarity_combo.currentText().lower()
        item_filename = self.item_combo.currentData()
        
        if not item_filename:
            QMessageBox.warning(self, "No Item", "No baked goods found in overlay folder!")
            return

        is_legendary = False
        rarity = "standard"

        if rarity_text == "legendary":
            is_legendary = True
            rarity = "standard"
        else:
            rarity = rarity_text
        
        message = {
            "event": "bake",
            "user": "TEST_USER",
            "rank": "Test Rank",
            "score": 123,
            "item": item_filename,
            "is_legendary": is_legendary,
            "rarity": rarity,
            "trigger_explosion": True,
            "ranked_up": False
        }
        
        if rarity in ["shiny", "golden"] or is_legendary:
            message["trigger_explosion"] = True
        else:
             message["trigger_explosion"] = False

        asyncio.run(broadcast_to_overlays(message))
        self.log(f"🧪 Custom Test: {rarity_text.upper()} {format_item_name(item_filename)}")

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
        legendary_items = asset_manager.legendary_items
        
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
        
    def closeEvent(self, event):
        # Auto-stop bot when window closes
        if self.bot_thread and self.bot_thread.isRunning():
            self.log("🛑 Closing application - stopping bot...")
            self.stop_bot()
        event.accept()

    def trigger_rush_hour(self):
        if self.bot_thread and self.bot_thread.bot:
            try:
                duration = int(self.rh_duration.text())
            except ValueError:
                duration = 2
            asyncio.run_coroutine_threadsafe(self.bot_thread.bot.start_rush_hour(duration), self.bot_thread.loop)
            self.log(f"🚀 Triggered Rush Hour ({duration} mins)!")
        else:
            QMessageBox.warning(self, "Bot Not Running", "Please start the bot first!")

    def stop_rush_hour(self):
        if self.bot_thread and self.bot_thread.bot:
            asyncio.run_coroutine_threadsafe(self.bot_thread.bot.stop_rush_hour(), self.bot_thread.loop)
            self.log("🛑 Stopped Rush Hour!")

    def trigger_bake_sale(self):
        if self.bot_thread and self.bot_thread.bot:
            try:
                duration = int(self.bs_duration.text())
            except ValueError:
                duration = 20
            asyncio.run_coroutine_threadsafe(self.bot_thread.bot.start_bake_sale(duration), self.bot_thread.loop)
            self.log(f"🍪 Triggered Bake Sale ({duration} mins)!")
        else:
            QMessageBox.warning(self, "Bot Not Running", "Please start the bot first!")

    def stop_bake_sale(self):
        if self.bot_thread and self.bot_thread.bot:
            asyncio.run_coroutine_threadsafe(self.bot_thread.bot.stop_bake_sale(), self.bot_thread.loop)
            self.log("🛑 Stopped Bake Sale!")

    def trigger_food_critic(self):
        if self.bot_thread and self.bot_thread.bot:
            try:
                duration = int(self.fc_duration.text())
            except ValueError:
                duration = 10
            asyncio.run_coroutine_threadsafe(self.bot_thread.bot.spawn_food_critic(duration), self.bot_thread.loop)
            self.log(f"🧐 Triggered Food Critic ({duration} mins)!")
        else:
            QMessageBox.warning(self, "Bot Not Running", "Please start the bot first!")

    def stop_food_critic(self):
        if self.bot_thread and self.bot_thread.bot:
            asyncio.run_coroutine_threadsafe(self.bot_thread.bot.stop_food_critic(), self.bot_thread.loop)
            self.log("🛑 Stopped Food Critic!")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BakeRankGUI()
    window.show()
    sys.exit(app.exec_())
