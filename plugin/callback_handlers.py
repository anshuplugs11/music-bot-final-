from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import logging

logger = logging.getLogger(__name__)

def get_bot_instance(client):
    return getattr(client, 'bot_instance', None)

@Client.on_callback_query(filters.regex("^download_song:"))
async def handle_song_download(client: Client, callback_query: CallbackQuery):
    bot = get_bot_instance(client)
    if not bot:
        await callback_query.answer("❌ Bot not initialized!", show_alert=True)
        return
    
    try:
        _, video_id, requester_id = callback_query.data.split(":")
        
        # Check if the user who clicked is the one who requested
        if int(requester_id) != callback_query.from_user.id:
            await callback_query.answer("❌ This is not your request!", show_alert=True)
            return
        
        await callback_query.answer("📥 Starting download...")
        
        # Get video info
        video_url = f"https://youtube.com/watch?v={video_id}"
        video_info = await bot.youtube_dl.get_video_info(video_url)
        
        if not video_info:
            await callback_query.edit_message_text("❌ Failed to get video information!")
            return
        
        # Show download options
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎵 Audio (MP3)", callback_data=f"dl_audio:{video_id}"),
                InlineKeyboardButton("📹 Video (MP4)", callback_data=f"dl_video:{video_id}")
            ],
            [
                InlineKeyboardButton("❌ Cancel", callback_data="cancel_download")
            ]
        ])
        
        await callback_query.edit_message_text(
            f"📥 **Choose Download Format:**\n\n"
            f"**Title:** {video_info['title']}\n"
            f"**Duration:** {video_info['duration']}\n"
            f"**Uploader:** {video_info['uploader']}\n"
            f"**Views:** {video_info.get('view_count', 'N/A')}",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Download callback error: {e}")
        await callback_query.edit_message_text("❌ An error occurred!")

@Client.on_callback_query(filters.regex("^dl_"))
async def handle_download_format(client: Client, callback_query: CallbackQuery):
    bot = get_bot_instance(client)
    if not bot:
        return
    
    try:
        format_type, video_id = callback_query.data.split(":", 1)
        format_type = format_type.replace("dl_", "")
        
        video_url = f"https://youtube.com/watch?v={video_id}"
        
        # Update message to show download progress
        await callback_query.edit_message_text("📥 **Downloading... Please wait**")
        
        # Download progress callback
        progress_msg = None
        async def progress_callback(d):
            nonlocal progress_msg
            if d['status'] == 'downloading':
                progress_text = bot.youtube_dl.get_download_progress_text(d)
                if progress_msg != progress_text:
                    progress_msg = progress_text
                    try:
                        await callback_query.edit_message_text(progress_text)
                    except:
                        pass
        
        # Start download
        result = await bot.youtube_dl.download(
            video_url, 
            format_type, 
            "best",
            progress_callback
        )
        
        if result:
            file_path, info = result
            
            # Record download in database
            await bot.db.add_download(
                callback_query.from_user.id,
                callback_query.message.chat.id,
                info['title'],
                video_url,
                file_path,
                format_type,
                info.get('file_size', 0)
            )
            
            # Send the file
            caption = (
                f"🎵 **Downloaded Successfully!**\n\n"
                f"**Title:** {info['title']}\n"
                f"**Duration:** {info['duration']}\n"
                f"**Uploader:** {info['uploader']}\n"
                f"**Format:** {format_type.upper()}\n"
                f"**Requested by:** {callback_query.from_user.mention}"
            )
            
            if format_type == "audio":
                await callback_query.message.reply_audio(
                    file_path,
                    caption=caption,
                    performer=info['uploader'],
                    title=info['title']
                )
            else:
                await callback_query.message.reply_video(
                    file_path,
                    caption=caption
                )
            
            await callback_query.edit_message_text("✅ **Download completed and sent!**")
            
            # Clean up file after sending
            try:
                import os
                os.remove(file_path)
            except:
                pass
                
        else:
            await callback_query.edit_message_text("❌ **Download failed!**")
            
    except Exception as e:
        logger.error(f"Download format error: {e}")
        await callback_query.edit_message_text("❌ **Download failed!**")

@Client.on_callback_query(filters.regex("^(pause|resume|skip|stop|shuffle):"))
async def handle_player_controls(client: Client, callback_query: CallbackQuery):
    bot = get_bot_instance(client)
    if not bot:
        return
    
    # Check authorization
    from pyrogram.types import Message
    fake_message = Message(
        id=0,
        from_user=callback_query.from_user,
        date=callback_query.message.date,
        chat=callback_query.message.chat,
        content_type=None,
        service=None
    )
    
    if not await bot.auth_manager.is_authorized(fake_message):
        await callback_query.answer("❌ You're not authorized!", show_alert=True)
        return
    
    try:
        action, chat_id = callback_query.data.split(":")
        chat_id = int(chat_id)
        
        current = bot.music_player.get_current_playing(chat_id)
        
        if action == "pause":
            if not current:
                await callback_query.answer("❌ Nothing is playing!", show_alert=True)
                return
            
            success = await bot.music_player.pause(chat_id)
            if success:
                await callback_query.answer("⏸ Paused")
            else:
                await callback_query.answer("❌ Failed to pause!", show_alert=True)
                
        elif action == "resume":
            success = await bot.music_player.resume(chat_id)
            if success:
                await callback_query.answer("▶️ Resumed")
            else:
                await callback_query.answer("❌ Failed to resume!", show_alert=True)
                
        elif action == "skip":
            if not current:
                await callback_query.answer("❌ Nothing is playing!", show_alert=True)
                return
            
            success = await bot.music_player.skip(chat_id)
            if success:
                await callback_query.answer(f"⏭ Skipped: {current.title}")
                # Update the message
                try:
                    new_current = bot.music_player.get_current_playing(chat_id)
                    if new_current:
                        await callback_query.edit_message_text(
                            f"🎵 **Now Playing:**\n\n"
                            f"**Title:** {new_current.title}\n"
                            f"**Duration:** {new_current.duration}\n"
                            f"**Requested by:** {new_current.requester}",
                            reply_markup=callback_query.message.reply_markup
                        )
                    else:
                        await callback_query.edit_message_text("⏹ **Playback ended**")
                except:
                    pass
            else:
                await callback_query.answer("❌ Failed to skip!", show_alert=True)
                
        elif action == "stop":
            success = await bot.music_player.stop(chat_id)
            if success:
                await callback_query.answer("⏹ Stopped and left VC")
                await callback_query.edit_message_text("⏹ **Playback stopped and left voice chat**")
            else:
                await callback_query.answer("❌ Failed to stop!", show_alert=True)
                
        elif action == "shuffle":
            success = await bot.music_player.shuffle_queue(chat_id)
            if success:
                await callback_query.answer("🔀 Queue shuffled")
            else:
                await callback_query.answer("❌ Queue is empty!", show_alert=True)
                
    except Exception as e:
        logger.error(f"Player control error: {e}")
        await callback_query.answer("❌ An error occurred!", show_alert=True)

@Client.on_callback_query(filters.regex("^queue:"))
async def handle_queue_display(client: Client, callback_query: CallbackQuery):
    bot = get_bot_instance(client)
    if not bot:
        return
    
    try:
        chat_id = int(callback_query.data.split(":")[1])
        
        current = bot.music_player.get_current_playing(chat_id)
        queue = await bot.music_player.get_queue(chat_id)
        
        if not current and not queue:
            await callback_query.answer("📝 Queue is empty!", show_alert=True)
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
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔀 Shuffle", callback_data=f"shuffle:{chat_id}"),
                InlineKeyboardButton("🗑 Clear", callback_data=f"clear_queue:{chat_id}")
            ],
            [
                InlineKeyboardButton("🔄 Refresh", callback_data=f"queue:{chat_id}")
            ]
        ])
        
        await callback_query.edit_message_text(text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Queue display error: {e}")
        await callback_query.answer("❌ An error occurred!", show_alert=True)

@Client.on_callback_query(filters.regex("^clear_queue:"))
async def handle_clear_queue(client: Client, callback_query: CallbackQuery):
    bot = get_bot_instance(client)
    if not bot:
        return
    
    # Check authorization
    from pyrogram.types import Message
    fake_message = Message(
        id=0,
        from_user=callback_query.from_user,
        date=callback_query.message.date,
        chat=callback_query.message.chat,
        content_type=None,
        service=None
    )
    
    if not await bot.auth_manager.is_authorized(fake_message):
        await callback_query.answer("❌ You're not authorized!", show_alert=True)
        return
    
    try:
        chat_id = int(callback_query.data.split(":")[1])
        
        await bot.music_player.clear_queue(chat_id)
        await callback_query.answer("🗑 Queue cleared!")
        
        # Update display
        current = bot.music_player.get_current_playing(chat_id)
        if current:
            text = f"📝 **Queue cleared!**\n\n🎵 **Now Playing:**\n**{current.title}** | `{current.duration}`\n**Requested by:** {current.requester}"
        else:
            text = "📝 **Queue is now empty!**"
        
        await callback_query.edit_message_text(text)
        
    except Exception as e:
        logger.error(f"Clear queue error: {e}")
        await callback_query.answer("❌ An error occurred!", show_alert=True)

@Client.on_callback_query(filters.regex("^cancel"))
async def handle_cancel(client: Client, callback_query: CallbackQuery):
    await callback_query.edit_message_text("❌ **Operation cancelled**")

@Client.on_callback_query(filters.regex("^main_menu$"))
async def handle_main_menu(client: Client, callback_query: CallbackQuery):
    bot = get_bot_instance(client)
    if not bot:
        return
    
    welcome_text = f"""
🎵 **Welcome to Advanced Music Bot!**

Hello {callback_query.from_user.mention}!

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
    
    await callback_query.edit_message_text(
        welcome_text,
        reply_markup=bot.get_main_keyboard()
    )
