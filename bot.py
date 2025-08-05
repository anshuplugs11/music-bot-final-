import os
import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from database import Database
from music_player import MusicPlayer
from youtube_downloader import YouTubeDownloader
from auth_manager import AuthManager
from broadcast_manager import BroadcastManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MusicBot:
    def __init__(self):
        self.app = Client(
            "music_bot",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN,
            plugins=dict(root="plugins")
        )
        self.db = Database()
        self.music_player = MusicPlayer()
        self.youtube_dl = YouTubeDownloader()
        self.auth_manager = AuthManager(self.db)
        self.broadcast_manager = BroadcastManager(self.app, self.db)
        self.maintenance_mode = False
        self.logging_enabled = True

    async def start_bot(self):
        await self.app.start()
        await self.db.connect()
        logger.info("🎵 Music Bot Started Successfully!")
        
        # Send startup message to owner
        try:
            await self.app.send_photo(
                Config.OWNER_ID,
                photo="https://telegra.ph/file/c6e1041c6c9a12913f57a.jpg",
                caption="🎵 **Music Bot Connected!**\n\n✅ Bot is now online and ready to serve music!",
                reply_markup=self.get_main_keyboard()
            )
        except Exception as e:
            logger.error(f"Failed to send startup message: {e}")

    def get_main_keyboard(self):
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎵 Music Commands", callback_data="music_commands"),
                InlineKeyboardButton("👑 Admin Commands", callback_data="admin_commands")
            ],
            [
                InlineKeyboardButton("🔐 Auth Commands", callback_data="auth_commands"),
                InlineKeyboardButton("📢 Broadcast Commands", callback_data="broadcast_commands")
            ],
            [
                InlineKeyboardButton("📊 Bot Stats", callback_data="bot_stats"),
                InlineKeyboardButton("❓ Help", callback_data="help_menu")
            ],
            [
                InlineKeyboardButton("🔧 Settings", callback_data="settings"),
                InlineKeyboardButton("📝 Logs", callback_data="view_logs")
            ]
        ])

    @staticmethod
    def is_sudoer(user_id):
        return user_id in Config.SUDOERS

    @staticmethod
    def maintenance_check():
        def decorator(func):
            async def wrapper(client, message):
                bot_instance = client.bot_instance
                if bot_instance.maintenance_mode and not MusicBot.is_sudoer(message.from_user.id):
                    await message.reply_text("🔧 Bot is under maintenance. Please try again later.")
                    return
                return await func(client, message)
            return wrapper
        return decorator

# Initialize bot instance
bot = MusicBot()

@bot.app.on_message(filters.command("start"))
@bot.maintenance_check()
async def start_command(client, message: Message):
    user_id = message.from_user.id
    await bot.db.add_user(user_id, message.from_user.first_name)
    
    welcome_text = f"""
🎵 **Welcome to Advanced Music Bot!**

Hello {message.from_user.mention}!

**🎧 Music Features:**
• Download songs from YouTube
• Play music in voice chats
• Video playback support
• Queue management
• Speed control
• Loop functionality

**📱 How to use:**
• `/song` - Download songs
• `/play` - Play music
• `/vplay` - Play with video
• `/queue` - View queue
• `/help` - Get help

**🔗 Add me to your group and enjoy unlimited music!**
    """
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{client.me.username}?startgroup=true"),
            InlineKeyboardButton("📢 Channel", url="https://t.me/your_channel")
        ],
        [
            InlineKeyboardButton("❓ Help", callback_data="help_menu"),
            InlineKeyboardButton("🎵 Commands", callback_data="music_commands")
        ]
    ])
    
    await message.reply_photo(
        photo="https://telegra.ph/file/c6e1041c6c9a12913f57a.jpg",
        caption=welcome_text,
        reply_markup=keyboard
    )

@bot.app.on_message(filters.command("help"))
async def help_command(client, message: Message):
    help_text = """
🎵 **Music Bot Help**

**🎧 Music Commands:**
• `/song <query>` - Download song (MP3/MP4)
• `/play <query>` - Play music in VC
• `/vplay <query>` - Play video in VC
• `/playforce` - Force play (skip queue)
• `/vplayforce` - Force video play
• `/queue` - Show current queue
• `/shuffle` - Shuffle queue

**⚡ Control Commands:**
• `/pause` - Pause playback
• `/resume` - Resume playback
• `/skip` - Skip current song
• `/stop` - Stop playback
• `/speed <1-3>` - Adjust playback speed
• `/seek <seconds>` - Seek to position
• `/seekback <seconds>` - Seek backward

**🔄 Loop Commands:**
• `/loop` - Toggle loop mode
• `/loop <1-10>` - Loop specific times

**📊 Info Commands:**
• `/ping` - Check bot latency
• `/stats` - Bot statistics (sudoers only)

**📺 Channel Commands:**
• `/cplay` - Play in connected channel
• `/cvplay` - Video play in channel
• `/channelplay` - Connect channel to group
• `/cspeed` - Channel speed control

**👑 Admin Commands (Group Admins):**
• `/auth <user>` - Authorize user
• `/unauth <user>` - Remove authorization
• `/authusers` - List authorized users

For more help, contact @your_support_bot
    """
    
    await message.reply_text(help_text)

@bot.app.on_message(filters.command("ping"))
async def ping_command(client, message: Message):
    import time
    start_time = time.time()
    ping_msg = await message.reply_text("🏓 Pinging...")
    end_time = time.time()
    
    latency = round((end_time - start_time) * 1000, 2)
    
    await ping_msg.edit_text(
        f"🏓 **Pong!**\n\n"
        f"💫 **Latency:** `{latency}ms`\n"
        f"🤖 **Bot:** Online\n"
        f"🎵 **Music Engine:** Active"
    )

@bot.app.on_message(filters.command("stats") & filters.user(Config.SUDOERS))
async def stats_command(client, message: Message):
    import psutil
    import platform
    from datetime import datetime
    
    # System stats
    cpu_percent = psutil.cpu_percent()
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Bot stats
    total_users = await bot.db.get_users_count()
    total_chats = await bot.db.get_chats_count()
    
    stats_text = f"""
📊 **Bot Statistics**

**🤖 Bot Info:**
• **Users:** {total_users}
• **Chats:** {total_chats}
• **Uptime:** {datetime.now().strftime('%H:%M:%S')}

**💻 System Info:**
• **Platform:** {platform.system()} {platform.release()}
• **CPU Usage:** {cpu_percent}%
• **RAM Usage:** {memory.percent}%
• **Disk Usage:** {disk.percent}%
• **Available RAM:** {round(memory.available/1024/1024/1024, 2)} GB

**🎵 Music Stats:**
• **Active VCs:** {len(bot.music_player.active_chats)}
• **Queue Songs:** {bot.music_player.get_total_queue_count()}
• **Downloads Today:** {await bot.db.get_downloads_today()}
    """
    
    await message.reply_text(stats_text)

# Callback query handlers
@bot.app.on_callback_query()
async def callback_handler(client, callback_query):
    data = callback_query.data
    user_id = callback_query.from_user.id
    
    if data == "music_commands":
        text = """
🎵 **Music Commands**

**🎧 Basic Commands:**
• `/song <name>` - Download song
• `/play <name>` - Play in voice chat
• `/vplay <name>` - Play video
• `/queue` - Show queue
• `/shuffle` - Shuffle queue

**⚡ Control:**
• `/pause` - Pause music
• `/resume` - Resume music
• `/skip` - Skip current
• `/stop` - Stop playing
• `/speed <1-3>` - Change speed
• `/loop` - Toggle loop

**📺 Channel:**
• `/cplay` - Channel play
• `/cvplay` - Channel video
• `/cspeed` - Channel speed
        """
        
    elif data == "admin_commands":
        if not bot.is_sudoer(user_id):
            await callback_query.answer("❌ You're not authorized!", show_alert=True)
            return
            
        text = """
👑 **Admin Commands**

**🔐 User Management:**
• `/gban <user>` - Global ban
• `/ungban <user>` - Remove global ban
• `/gbannedusers` - List banned users
• `/block <user>` - Block user
• `/unblock <user>` - Unblock user

**💬 Chat Management:**
• `/blacklistchat` - Blacklist chat
• `/whitelistchat` - Whitelist chat
• `/blacklistedchats` - List blacklisted

**🔧 System:**
• `/maintenance` - Toggle maintenance
• `/logs` - Get bot logs
• `/logger on/off` - Toggle logging
        """
        
    elif data == "auth_commands":
        text = """
🔐 **Authorization Commands**

**👥 For Group Admins:**
• `/auth <user>` - Authorize user
• `/unauth <user>` - Remove auth
• `/authusers` - List authorized users

**📝 How it works:**
• Only authorized users can use music commands
• Group admins can authorize users
• Sudoers have full access everywhere
        """
        
    elif data == "broadcast_commands":
        if not bot.is_sudoer(user_id):
            await callback_query.answer("❌ You're not authorized!", show_alert=True)
            return
            
        text = """
📢 **Broadcast Commands**

**📤 Broadcasting:**
• `/broadcast <message>` - Send to all chats
• `/broadcast -pin <message>` - Pin broadcast
• `/broadcast -user <message>` - To users only
• `/broadcast -assistant <message>` - From assistant

**🔧 Options:**
• `-pin` - Pin message
• `-pinloud` - Pin with notification
• `-user` - Broadcast to users
• `-assistant` - Use assistant account
• `-nobot` - Don't send to bot chats
        """
        
    elif data == "bot_stats":
        total_users = await bot.db.get_users_count()
        total_chats = await bot.db.get_chats_count()
        
        text = f"""
📊 **Bot Statistics**

**📈 Usage:**
• **Total Users:** {total_users}
• **Total Chats:** {total_chats}
• **Active VCs:** {len(bot.music_player.active_chats)}

**🎵 Music:**
• **Songs in Queue:** {bot.music_player.get_total_queue_count()}
• **Downloads Today:** {await bot.db.get_downloads_today()}

**⚡ Status:**
• **Bot Status:** {'🔧 Maintenance' if bot.maintenance_mode else '✅ Online'}
• **Logging:** {'✅ Enabled' if bot.logging_enabled else '❌ Disabled'}
        """
        
    elif data == "help_menu":
        text = """
❓ **Help Menu**

**🎵 Music Bot Features:**
• High-quality music streaming
• YouTube downloads (MP3/MP4)
• Video playback in voice chats
• Advanced queue management
• Speed and loop controls
• Channel streaming support

**🚀 Quick Start:**
1. Add bot to your group
2. Start a voice chat
3. Use `/play <song name>` to play music
4. Use `/queue` to manage your playlist

**💬 Support:**
• Join @your_support_chat for help
• Report bugs to @your_channel
• Feature requests welcome!
        """
        
    else:
        await callback_query.answer("❌ Invalid option!")
        return
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
    ]])
    
    try:
        await callback_query.edit_message_text(text, reply_markup=keyboard)
    except:
        await callback_query.answer(text[:200] + "...", show_alert=True)

# Store bot instance for access in decorators
bot.app.bot_instance = bot

if __name__ == "__main__":
    bot.app.run(bot.start_bot())
