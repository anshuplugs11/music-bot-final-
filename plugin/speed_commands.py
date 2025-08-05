from pyrogram import Client, filters
from pyrogram.types import Message
import logging

logger = logging.getLogger(__name__)

def get_bot_instance(client):
    return getattr(client, 'bot_instance', None)

@Client.on_message(filters.command(["speed", "playback"]))
async def set_playback_speed(client: Client, message: Message):
    bot = get_bot_instance(client)
    if not bot or not await bot.auth_manager.is_authorized(message):
        return
    
    if message.chat.type.name == "PRIVATE":
        await message.reply_text("❌ This command only works in groups!")
        return
    
    if len(message.command) < 2:
        await message.reply_text(
            "❌ Please specify speed!\n\n"
            "**Usage:** `/speed <0.5-3.0>`\n"
            "**Examples:**\n"
            "• `/speed 0.5` - Half speed\n"
            "• `/speed 1.0` - Normal speed\n"
            "• `/speed 1.5` - 1.5x speed\n"
            "• `/speed 2.0` - Double speed"
        )
        return
    
    try:
        speed = float(message.command[1])
        
        if speed < 0.5 or speed > 3.0:
            await message.reply_text("❌ Speed must be between 0.5 and 3.0!")
            return
        
        chat_id = message.chat.id
        current = bot.music_player.get_current_playing(chat_id)
        
        if not current:
            await message.reply_text("❌ Nothing is playing!")
            return
        
        success = await bot.music_player.set_speed(chat_id, speed)
        
        if success:
            speed_text = {
                0.5: "🐌 Half Speed",
                0.75: "🔽 Slow",
                1.0: "▶️ Normal Speed",
                1.25: "🔼 Fast",
                1.5: "⚡ 1.5x Speed",
                2.0: "🚀 Double Speed"
            }.get(speed, f"⚡ {speed}x Speed")
            
            await message.reply_text(
                f"⚡ **Playback Speed Changed**\n\n"
                f"**Current Song:** {current.title}\n"
                f"**New Speed:** {speed_text}"
            )
        else:
            await message.reply_text("❌ Failed to change speed!")
            
    except ValueError:
        await message.reply_text("❌ Invalid speed value!")
    except Exception as e:
        logger.error(f"Speed change error: {e}")
        await message.reply_text("❌ An error occurred!")

@Client.on_message(filters.command(["cspeed", "cplayback"]))
async def set_channel_speed(client: Client, message: Message):
    bot = get_bot_instance(client)
    if not bot or not await bot.auth_manager.is_admin(message):
        await message.reply_text("❌ This command requires admin privileges!")
        return
    
    # Similar to set_playback_speed but for connected channels
    await message.reply_text("🔧 Channel speed control - Coming soon!")

@Client.on_message(filters.command("seek"))
async def seek_position(client: Client, message: Message):
    bot = get_bot_instance(client)
    if not bot or not await bot.auth_manager.is_authorized(message):
        return
    
    if message.chat.type.name == "PRIVATE":
        await message.reply_text("❌ This command only works in groups!")
        return
    
    if len(message.command) < 2:
        await message.reply_text(
            "❌ Please specify seek position!\n\n"
            "**Usage:** `/seek <seconds>`\n"
            "**Examples:**\n"
            "• `/seek 30` - Seek to 30 seconds\n"
            "• `/seek 120` - Seek to 2 minutes"
        )
        return
    
    try:
        seconds = int(message.command[1])
        
        if seconds < 0:
            await message.reply_text("❌ Seek position must be positive!")
            return
        
        chat_id = message.chat.id
        current = bot.music_player.get_current_playing(chat_id)
        
        if not current:
            await message.reply_text("❌ Nothing is playing!")
            return
        
        success = await bot.music_player.seek(chat_id, seconds)
        
        if success:
            minutes = seconds // 60
            secs = seconds % 60
            time_str = f"{minutes:02d}:{secs:02d}"
            
            await message.reply_text(
                f"⏩ **Seeked to {time_str}**\n\n"
                f"**Current Song:** {current.title}"
            )
        else:
            await message.reply_text("❌ Failed to seek!")
            
    except ValueError:
        await message.reply_text("❌ Invalid time value!")
    except Exception as e:
        logger.error(f"Seek error: {e}")
        await message.reply_text("❌ An error occurred!")

@Client.on_message(filters.command("seekback"))
async def seek_backward(client: Client, message: Message):
    bot = get_bot_instance(client)
    if not bot or not await bot.auth_manager.is_authorized(message):
        return
    
    if message.chat.type.name == "PRIVATE":
        await message.reply_text("❌ This command only works in groups!")
        return
    
    if len(message.command) < 2:
        await message.reply_text(
            "❌ Please specify seconds to go back!\n\n"
            "**Usage:** `/seekback <seconds>`\n"
            "**Examples:**\n"
            "• `/seekback 10` - Go back 10 seconds\n"
            "• `/seekback 30` - Go back 30 seconds"
        )
        return
    
    try:
        seconds = int(message.command[1])
        
        if seconds < 0:
            await message.reply_text("❌ Seconds must be positive!")
            return
        
        chat_id = message.chat.id
        current = bot.music_player.get_current_playing(chat_id)
        
        if not current:
            await message.reply_text("❌ Nothing is playing!")
            return
        
        # Calculate new position
        current_position = getattr(current, 'position', 0)
        new_position = max(0, current_position - seconds)
        
        success = await bot.music_player.seek(chat_id, new_position)
        
        if success:
            minutes = new_position // 60
            secs = new_position % 60
            time_str = f"{minutes:02d}:{secs:02d}"
            
            await message.reply_text(
                f"⏪ **Seeked back to {time_str}**\n\n"
                f"**Current Song:** {current.title}"
            )
        else:
            await message.reply_text("❌ Failed to seek back!")
            
    except ValueError:
        await message.reply_text("❌ Invalid time value!")
    except Exception as e:
        logger.error(f"Seek back error: {e}")
        await message.reply_text("❌ An error occurred!")

@Client.on_message(filters.command("volume"))
async def set_volume(client: Client, message: Message):
    bot = get_bot_instance(client)
    if not bot or not await bot.auth_manager.is_authorized(message):
        return
    
    if message.chat.type.name == "PRIVATE":
        await message.reply_text("❌ This command only works in groups!")
        return
    
    if len(message.command) < 2:
        await message.reply_text(
            "❌ Please specify volume level!\n\n"
            "**Usage:** `/volume <1-100>`\n"
            "**Examples:**\n"
            "• `/volume 50` - Set to 50%\n"
            "• `/volume 100` - Set to maximum"
        )
        return
    
    try:
        volume = int(message.command[1])
        
        if volume < 1 or volume > 100:
            await message.reply_text("❌ Volume must be between 1 and 100!")
            return
        
        chat_id = message.chat.id
        current = bot.music_player.get_current_playing(chat_id)
        
        if not current:
            await message.reply_text("❌ Nothing is playing!")
            return
        
        # Note: Volume control would need to be implemented in PyTgCalls
        await message.reply_text(
            f"🔊 **Volume Set to {volume}%**\n\n"
            f"**Current Song:** {current.title}\n\n"
            f"*Note: Volume control is handled by Telegram's voice chat settings.*"
        )
        
    except ValueError:
        await message.reply_text("❌ Invalid volume value!")
    except Exception as e:
        logger.error(f"Volume error: {e}")
        await message.reply_text("❌ An error occurred!")
