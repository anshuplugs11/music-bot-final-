import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from music_player import QueueItem
import logging

logger = logging.getLogger(__name__)

# Helper function to get bot instance
def get_bot_instance(client):
    return getattr(client, 'bot_instance', None)

@Client.on_message(filters.command("song"))
async def download_song(client: Client, message: Message):
    bot = get_bot_instance(client)
    if not bot or not await bot.auth_manager.is_authorized(message):
        await message.reply_text(bot.auth_manager.get_auth_failed_text() if bot else "❌ Bot not initialized!")
        return
    
    if len(message.command) < 2:
        await message.reply_text("❌ Please provide a song name!\n\n**Usage:** `/song <song name>`")
        return
    
    query = " ".join(message.command[1:])
    
    # Search for songs
    search_msg = await message.reply_text("🔍 **Searching for songs...**")
    
    try:
        results = await bot.youtube_dl.search_youtube(query, limit=5)
        
        if not results:
            await search_msg.edit_text("❌ No songs found for your query!")
            return
        
        # Create selection keyboard
        keyboard = []
        for i, result in enumerate(results):
            keyboard.append([
                InlineKeyboardButton(
                    f"🎵 {result['title'][:50]}... | {result['duration']}",
                    callback_data=f"download_song:{result['id']}:{message.from_user.id}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_download")
        ])
        
        await search_msg.edit_text(
            f"🎵 **Search Results for:** `{query}`\n\n"
            "Select a song to download:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Song search error: {e}")
        await search_msg.edit_text("❌ An error occurred while searching!")

@Client.on_message(filters.command(["play", "vplay"]))
async def play_song(client: Client, message: Message):
    bot = get_bot_instance(client)
    if not bot or not await bot.auth_manager.is_authorized(message):
        await message.reply_text(bot.auth_manager.get_auth_failed_text() if bot else "❌ Bot not initialized!")
        return
    
    if message.chat.type.name == "PRIVATE":
        await message.reply_text("❌ This command only works in groups!")
        return
    
    if not await bot.auth_manager.can_manage_voice_chats(message):
        await message.reply_text(bot.auth_manager.get_auth_failed_text("voice_chat"))
        return
    
    is_video = message.command[0] == "vplay"
    
    if len(message.command) < 2:
        await message.reply_text(f"❌ Please provide a song name!\n\n**Usage:** `/{message.command[0]} <song name>`")
        return
    
    query = " ".join(message.command[1:])
    chat_id = message.chat.id
    
    # Search and play
    search_msg = await message.reply_text("🔍 **Searching...**")
    
    try:
        results = await bot.youtube_dl.search_youtube(query, limit=1)
        
        if not results:
            await search_msg.edit_text("❌ No songs found!")
            return
        
        result = results[0]
        
        await search_msg.edit_text("📥 **Getting stream URL...**")
        
        # Get stream URL
        stream_url = await bot.youtube_dl.get_stream_url(result['url'], "video" if is_video else "audio")
        
        if not stream_url:
            await search_msg.edit_text("❌ Failed to get stream URL!")
            return
        
        # Create queue item
        queue_item = QueueItem(
            title=result['title'],
            duration=result['duration'],
            requester=message.from_user.mention,
            stream_url=stream_url,
            is_video=is_video
        )
        
        # Play the song
        await search_msg.edit_text("🎵 **Starting playback...**")
        
        success = await bot.music_player.play(chat_id, queue_item)
        
        if success:
            current_info = bot.music_player.get_current_playing(chat_id)
            if current_info and current_info.title == queue_item.title:
                # Currently playing
                await search_msg.edit_text(
                    f"🎵 **Now Playing:**\n\n"
                    f"**Title:** {result['title']}\n"
                    f"**Duration:** {result['duration']}\n"
                    f"**Requested by:** {message.from_user.mention}\n"
                    f"**Type:** {'📹 Video' if is_video else '🎵 Audio'}",
                    reply_markup=get_player_keyboard(chat_id)
                )
            else:
                # Added to queue
                queue_pos = len(await bot.music_player.get_queue(chat_id))
                await search_msg.edit_text(
                    f"📝 **Added to Queue (#**{queue_pos}**)**\n\n"
                    f"**Title:** {result['title']}\n"
                    f"**Duration:** {result['duration']}\n"
                    f"**Requested by:** {message.from_user.mention}"
                )
        else:
            await search_msg.edit_text("❌ Failed to start playback!")
            
    except Exception as e:
        logger.error(f"Play error: {e}")
        await search_msg.edit_text("❌ An error occurred while playing!")

@Client.on_message(filters.command(["playforce", "vplayforce"]))
async def force_play(client: Client, message: Message):
    bot = get_bot_instance(client)
    if not bot or not await bot.auth_manager.is_admin(message):
        await message.reply_text("❌ This command requires admin privileges!")
        return
    
    if message.chat.type.name == "PRIVATE":
        await message.reply_text("❌ This command only works in groups!")
        return
    
    is_video = message.command[0] == "vplayforce"
    
    if len(message.command) < 2:
        await message.reply_text(f"❌ Please provide a song name!\n\n**Usage:** `/{message.command[0]} <song name>`")
        return
    
    query = " ".join(message.command[1:])
    chat_id = message.chat.id
    
    # Similar to play_song but with force=True
    search_msg = await message.reply_text("🔍 **Force playing...**")
    
    try:
        results = await bot.youtube_dl.search_youtube(query, limit=1)
        
        if not results:
            await search_msg.edit_text("❌ No songs found!")
            return
        
        result = results[0]
        stream_url = await bot.youtube_dl.get_stream_url(result['url'], "video" if is_video else "audio")
        
        if not stream_url:
            await search_msg.edit_text("❌ Failed to get stream URL!")
            return
        
        queue_item = QueueItem(
            title=result['title'],
            duration=result['duration'],
            requester=message.from_user.mention,
            stream_url=stream_url,
            is_video=is_video
        )
        
        success = await bot.music_player.play(chat_id, queue_item, force=True)
        
        if success:
            await search_msg.edit_text(
                f"⚡ **Force Playing:**\n\n"
                f"**Title:** {result['title']}\n"
                f"**Duration:** {result['duration']}\n"
                f"**Requested by:** {message.from_user.mention}\n"
                f"**Type:** {'📹 Video' if is_video else '🎵 Audio'}",
                reply_markup=get_player_keyboard(chat_id)
            )
        else:
            await search_msg.edit_text("❌ Failed to force play!")
            
    except Exception as e:
        logger.error(f"Force play error: {e}")
        await search_msg.edit_text("❌ An error occurred!")

@Client.on_message(filters.command("pause"))
async def pause_playback(client: Client, message: Message):
    bot = get_bot_instance(client)
    if not bot or not await bot.auth_manager.is_authorized(message):
        return
    
    chat_id = message.chat.id
    
    if bot.music_player.is_playing(chat_id):
        success = await bot.music_player.pause(chat_id)
        if success:
            await message.reply_text("⏸ **Playback Paused**")
        else:
            await message.reply_text("❌ Failed to pause!")
    else:
        await message.reply_text("❌ Nothing is playing!")

@Client.on_message(filters.command("resume"))
async def resume_playback(client: Client, message: Message):
    bot = get_bot_instance(client)
    if not bot or not await bot.auth_manager.is_authorized(message):
        return
    
    chat_id = message.chat.id
    
    success = await bot.music_player.resume(chat_id)
    if success:
        await message.reply_text("▶️ **Playback Resumed**")
    else:
        await message.reply_text("❌ Failed to resume!")

@Client.on_message(filters.command("skip"))
async def skip_song(client: Client, message: Message):
    bot = get_bot_instance(client)
    if not bot or not await bot.auth_manager.is_authorized(message):
        return
    
    chat_id = message.chat.id
    current = bot.music_player.get_current_playing(chat_id)
    
    if current:
        success = await bot.music_player.skip(chat_id)
        if success:
            await message.reply_text(f"⏭ **Skipped:** {current.title}")
        else:
            await message.reply_text("❌ Failed to skip!")
    else:
        await message.reply_text("❌ Nothing is playing!")

@Client.on_message(filters.command("stop"))
async def stop_playback(client: Client, message: Message):
    bot = get_bot_instance(client)
    if not bot or not await bot.auth_manager.is_authorized(message):
        return
    
    chat_id = message.chat.id
    
    success = await bot.music_player.stop(chat_id)
    if success:
        await message.reply_text("⏹ **Playback Stopped and Left Voice Chat**")
    else:
        await message.reply_text("❌ Failed to stop!")

@Client.on_message(filters.command("queue"))
async def show_queue(client: Client, message: Message):
    bot = get_bot_instance(client)
    if not bot:
        return
    
    chat_id = message.chat.id
    current = bot.music_player.get_current_playing(chat_id)
    queue = await bot.music_player.get_queue(chat_id)
    
    if not current and not queue:
        await message.reply_text("📝 **Queue is empty!**")
        return
    
    text = "📝 **Current Queue:**\n\n"
    
    if current:
        text += f"🎵 **Now Playing:**\n**{current.title}** | `{current.duration}`\n**Requested by:** {current.requester}\n\n"
    
    if queue:
        text += "**📋 Up Next:**\n"
        for i, item in enumerate(queue[:10], 1):
            text += f"`{i}.` **{item.title}** | `{item.duration}`\n"
        
        if len(queue) > 10:
            text += f"\n**... and {len(queue) - 10} more songs**"
    
    await message.reply_text(text, reply_markup=get_queue_keyboard(chat_id))

@Client.on_message(filters.command("shuffle"))
async def shuffle_queue(client: Client, message: Message):
    bot = get_bot_instance(client)
    if not bot or not await bot.auth_manager.is_authorized(message):
        return
    
    chat_id = message.chat.id
    
    success = await bot.music_player.shuffle_queue(chat_id)
    if success:
        await message.reply_text("🔀 **Queue Shuffled!**")
    else:
        await message.reply_text("❌ Queue is empty or failed to shuffle!")

@Client.on_message(filters.command("loop"))
async def toggle_loop(client: Client, message: Message):
    bot = get_bot_instance(client)
    if not bot or not await bot.auth_manager.is_authorized(message):
        return
    
    chat_id = message.chat.id
    
    if len(message.command) > 1:
        try:
            count = int(message.command[1])
            await bot.music_player.set_loop(chat_id, 1, count)
            await message.reply_text(f"🔁 **Loop enabled for {count} times**")
        except ValueError:
            await message.reply_text("❌ Invalid loop count!")
    else:
        # Toggle loop mode
        current_mode = bot.music_player.loop_mode.get(chat_id, 0)
        new_mode = 0 if current_mode > 0 else 2
        await bot.music_player.set_loop(chat_id, new_mode)
        
        if new_mode == 0:
            await message.reply_text("🔁 **Loop Disabled**")
        else:
            await message.reply_text("🔁 **Queue Loop Enabled**")

def get_player_keyboard(chat_id: int):
    """Get player control keyboard"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⏸ Pause", callback_data=f"pause:{chat_id}"),
            InlineKeyboardButton("▶️ Resume", callback_data=f"resume:{chat_id}"),
            InlineKeyboardButton("⏭ Skip", callback_data=f"skip:{chat_id}")
        ],
        [
            InlineKeyboardButton("📝 Queue", callback_data=f"queue:{chat_id}"),
            InlineKeyboardButton("🔀 Shuffle", callback_data=f"shuffle:{chat_id}"),
            InlineKeyboardButton("⏹ Stop", callback_data=f"stop:{chat_id}")
        ]
    ])

def get_queue_keyboard(chat_id: int):
    """Get queue management keyboard"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔀 Shuffle", callback_data=f"shuffle:{chat_id}"),
            InlineKeyboardButton("🗑 Clear", callback_data=f"clear_queue:{chat_id}")
        ],
        [
            InlineKeyboardButton("🔄 Refresh", callback_data=f"queue:{chat_id}")
        ]
    ])
