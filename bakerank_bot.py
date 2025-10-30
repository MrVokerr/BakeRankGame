import asyncio
import time
import json
import random
import os
import glob
import socket
import sys

# Check for required packages BEFORE importing them
try:
    import websockets
except ImportError:
    print("=" * 50)
    print("❌ MISSING PACKAGE: websockets")
    print("=" * 50)
    print("Please run: install_requirements.bat")
    print("Or manually: pip install websockets")
    print("=" * 50)
    input("\nPress Enter to exit...")
    sys.exit(1)

try:
    from twitchio.ext import commands
except ImportError:
    print("=" * 50)
    print("❌ MISSING PACKAGE: twitchio")
    print("=" * 50)
    print("Please run: install_requirements.bat")
    print("Or manually: pip install twitchio==2.9.1")
    print("=" * 50)
    input("\nPress Enter to exit...")
    sys.exit(1)


TOKEN = "ta715ejsep8ves6gl9d4wer1kptbcc"
CLIENT_ID = "gp762nuuoqcoxypju8c569th9wz7q5"
CHANNEL = "vokerr"
COOLDOWN = 60

DB_PATH = "bakerank_data.txt"
OVERLAY_FOLDER = "overlay"

# ============ WEBSOCKET SERVER (BUILT-IN) ============
overlay_clients = set()

async def handle_overlay_connection(websocket):
    """Handle incoming overlay connections"""
    overlay_clients.add(websocket)
    # Silently handle overlay connections
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
    """Start the WebSocket server for overlays"""
    async with websockets.serve(handle_overlay_connection, "0.0.0.0", 8765):
        print("🍞 Overlay server started on ws://localhost:8765")
        await asyncio.Future()  # Run forever

# ======================================================

def get_available_baked_goods():
    """Scan the overlay folder for PNG files and return list of available items (excluding legendaries)"""
    png_files = glob.glob(os.path.join(OVERLAY_FOLDER, "*.png"))
    if not png_files:
        # Fallback to default list if no PNGs found
        return ["croissant.png", "donut.png", "Pancakes.png"]
    # Exclude legendary items from normal pool
    normal_items = [os.path.basename(f) for f in png_files if not os.path.basename(f).startswith("Legendary-")]
    return normal_items if normal_items else [os.path.basename(f) for f in png_files]

def get_legendary_baked_goods():
    """Get list of legendary baked goods (files starting with 'Legendary-')"""
    png_files = glob.glob(os.path.join(OVERLAY_FOLDER, "Legendary-*.png"))
    return [os.path.basename(f) for f in png_files]

def choose_baked_good():
    """Choose a baked good with 1% chance for legendary"""
    legendary_items = get_legendary_baked_goods()
    normal_items = get_available_baked_goods()
    
    # 1% chance for legendary (if any exist)
    if legendary_items and random.random() < 0.01:
        return random.choice(legendary_items), True
    else:
        return random.choice(normal_items), False

def format_item_name(filename):
    """Convert filename to display name (e.g., 'croissant.png' -> 'Croissant')"""
    name = os.path.splitext(filename)[0]  # Remove .png extension
    return name.replace("_", " ").replace("-", " ").title()

# ============ TEXT FILE DATABASE ============
def load_player_data():
    """Load player data from text file (editable with Notepad)"""
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

# Load initial data
player_data = load_player_data()

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

class BakeRankBot(commands.Bot):
    def __init__(self):
        super().__init__(token=TOKEN, prefix="!", initial_channels=[CHANNEL])

    async def event_ready(self):
        print(f"✅ Bot logged in as {self.nick}")
        print(f"📺 Listening to channel: {CHANNEL}")
        print(f"🎮 Commands: !bake, !TopBakers")
        print("-" * 50)

    # ------------- CORE COMMANDS -----------------
    @commands.command(name="bake")
    async def bake(self, ctx):
        username = ctx.author.name.lower()
        now = time.time()

        # Get player data
        if username not in player_data:
            player_data[username] = {'bake_score': 0, 'last_bake_time': 0}
        
        bake_score = player_data[username]['bake_score']
        last_bake_time = player_data[username]['last_bake_time']

        # ===== COOLDOWN ENABLED (60 seconds per user) =====
        if now - last_bake_time < COOLDOWN:
            remaining = int(COOLDOWN - (now - last_bake_time))
            await ctx.send(f"⏳ @{username}, oven cooling... wait {remaining}s.")
            return
        # ==================================================

        old_rank_title = get_rank_title(bake_score)
        bake_score += 1
        new_rank_title = get_rank_title(bake_score)

        # Update player data
        player_data[username]['bake_score'] = bake_score
        player_data[username]['last_bake_time'] = now
        save_player_data(player_data)

        # Check if player ranked up
        ranked_up = old_rank_title != new_rank_title
        
        # Choose baked good (1% chance for legendary)
        bake_item, is_legendary = choose_baked_good()
        item_display_name = format_item_name(bake_item)
        
        # Determine if explosion should trigger
        trigger_explosion = ranked_up or is_legendary
        
        # Console output for streamer visibility
        if is_legendary:
            print(f"✨ {username} baked a LEGENDARY {item_display_name}! ✨")
        else:
            print(f"🍞 {username} baked a {item_display_name}!")
            
        if ranked_up:
            print(f"🎉 {username} ranked up to {new_rank_title}!")
        
        # Chat message
        if is_legendary:
            await ctx.send(f"✨ @{username} baked a LEGENDARY {item_display_name}! ✨ ({new_rank_title}) | Score: {int(bake_score)}")
        else:
            await ctx.send(f"🍞 @{username} baked a {item_display_name}! ({new_rank_title}) | Score: {int(bake_score)}")

        # Send bake event to overlay
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
        print(f"📤 Sending to overlay: {bake_item}")
        await broadcast_to_overlays(message)

    @commands.command(name="TopBakers")
    async def topbakers(self, ctx):
        await self.send_leaderboard_to_chat(ctx)

    # ------------- HELPER METHODS -----------------
    async def fetch_leaderboard(self):
        # Sort players by score, get top 5
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

# ------------------------------
async def main():
    """Run both the bot and overlay server together"""
    # Start overlay server in background
    overlay_task = asyncio.create_task(start_overlay_server())
    
    # Start bot
    bot = BakeRankBot()
    bot_task = asyncio.create_task(bot.start())
    
    # Run both forever
    await asyncio.gather(overlay_task, bot_task)

if __name__ == "__main__":
    # Single instance check - ensure only one bot runs at a time
    lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # Try to bind to a unique port
        lock_socket.bind(('127.0.0.1', 47200))
        print("=" * 50)
        print("🍞 BakeRank Bot Starting...")
        print("=" * 50)
    except socket.error:
        print("=" * 50)
        print("❌ ERROR: Bot is already running!")
        print("=" * 50)
        print("Another instance of BakeRank Bot is active.")
        print("Close the other window first, or it will auto-close.")
        print()
        
        # Try to kill other Python processes
        import subprocess
        try:
            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV'],
                capture_output=True,
                text=True
            )
            # Count Python processes (excluding this one)
            python_count = result.stdout.count('python.exe') - 1
            if python_count > 0:
                print(f"Found {python_count} other Python process(es).")
                print("Attempting to close previous instance...")
                subprocess.run(['taskkill', '/F', '/IM', 'python.exe', '/FI', 'PID ne %s' % os.getpid()],
                             capture_output=True)
                print("Previous instance closed. Please restart this bot.")
        except:
            pass
        
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user.")
    except Exception as e:
        print("\n" + "=" * 50)
        print("❌ FATAL ERROR")
        print("=" * 50)
        print(f"Error: {e}")
        print()
        import traceback
        traceback.print_exc()
        print()
        print("=" * 50)
        input("Press Enter to exit...")
    finally:
        try:
            lock_socket.close()
        except:
            pass
