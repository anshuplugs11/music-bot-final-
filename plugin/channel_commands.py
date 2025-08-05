from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatMemberStatus
import logging

logger = logging.getLogger(__name__)

def get_bot_instance(client):
    return getattr(client, 'bot_instance', None)

# Channel connection storage (in production, use database)
channel_connections = {}  # {group_chat_id: channel_chat_id}

@Client.on_message(filters.command("channelplay"))
async def connect_channel(client: Client, message: Message):
    bot = get_bot_instance(client)
    if not bot or not await bot.auth_manager.is_admin(message):
        await message.reply_text("❌ This command requires admin privileges!")
        return
    
    if message.chat.type.name == "PRIVATE":
        await message.reply_text("❌ This command only works in groups!")
        return
    
    if len(message.command) < 2:
        await message.reply_text(
            "❌ Please provide channel username or ID!\n\n"
            "**Usage:** `/channelplay <@channel_username or channel_id>`\n"
            "**Example:** `/channelplay @my_music_channel`"
        )
        return
    
    try:
        channel_input = message.command[1]
        
        # Get channel info
        if channel_input.startswith('@'):
            channel = await client.get_chat(channel_input)
        else:
            channel_id = int(channel_input)
            channel = await client.get_chat(channel_id)
        
        # Check if it's a channel
        if channel.type.name != "CHANNEL":
            await message.reply_text("❌ Please provide a valid channel!")
            return
        
        # Check if bot is admin in channel
        try:
            bot_member = await client.get_chat_member(channel.id, client.me.id)
            if bot_member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                await message.reply_text(
                    f"❌ Bot must be admin in **{channel.title}** to stream music!\n\n"
                    f"Please make the bot admin and try again."
                )
                return
        except Exception as e:
            await message.reply_text("❌ Failed to check bot permissions in channel!")
            return
        
        # Check if user is admin in channel
        try:
            user_member = await client.get_chat_member(channel.id, message.from_user.id)
            if user_member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                await message.reply_text(f"❌ You must be admin in **{channel.title}** to connect it!")
                return
        except Exception as e:
            await message.reply_text("❌ You don't have permission to connect this channel!")
            return
        
        # Connect channel to group
        group_id = message.chat.id
        channel_connections[group_id] = channel.id
        
        await message.reply_text(
            f"✅ **Channel Connected Successfully!**\n\n"
            f"**Group:** {message.chat.title}\n"
            f"**Connected Channel:** {channel.title}\n"
            f"**Channel ID:** `{channel.id}`\n\n"
            f"Now you can use `/cplay` and `/cvplay` commands to stream music in the connected channel!"
        )
        
        logger.info(f"Channel {channel.id} connected to group {group_id}")
        
    except ValueError:
        await message.reply_text("❌ Invalid channel ID!")
    except Exception as e:
        logger.error(f"Channel connect error: {e}")
        await message.reply_text("❌ Failed to connect channel!")

@Client.on_message(filters.command("cplay"))
async def channel_play_audio(client: Client, message: Message):
    bot = get_bot_instance(client)
    if not bot or not await bot.auth_manager.is_admin(message):
        await message.reply_text("❌ This command requires admin privileges!")
        return
    
    group_id = message.chat.id
    
    # Check if channel is connected
    if group_id not in channel_connections:
        await message.reply_text(
            "❌ No channel connected to this group!\n\n"
            "Use `/channelplay <@channel>` to connect a channel first."
        )
        return
    
    channel_id = channel_connections[group_id]
    
    if len(message.command) < 2:
        await message.reply_text("❌ Please provide a song name!\n\n**Usage:** `/cplay <song name>`")
        return
    
    query = " ".join(message.command[1:])
    
    # Search and play in channel
    search_msg = await message.reply_text("🔍 **Searching for channel playback...**")
    
    try:
        results = await bot.youtube_dl.search_youtube(query, limit=1)
        
        if not results:
            await search_msg.edit_text("❌ No songs found!")
            return
        
        result = results[0]
        
        await search_msg.edit_text("📥 **Getting stream URL for channel...**")
        
        # Get stream URL
        stream_url = await bot.youtube_dl.get_stream_url(result['url'], "audio")
        
        if not stream_url:
            await search_msg.edit_text("❌ Failed to get stream URL!")
            return
        
        # Create queue item
        from music_player import QueueItem
        queue_item = QueueItem(
            title=result['title'],
            duration=result['duration'],
            requester=message.from_user.mention,
            stream_url=stream_url,
            is_video=False
        )
        
        # Play in channel
        success = await bot.music_player.play(channel_id, queue_item)
        
        if success:
            try:
                channel = await client.get_chat(channel_id)
                channel_name = channel.title
            except:
                channel_name = "Connected Channel"
            
            await search_msg.edit_text(
                f"🎵 **Now Playing in Channel:**\n\n"
                f"**Channel:** {channel_name}\n"
                f"**Title:** {result['title']}\n"
                f"**Duration:** {result['duration']}\n"
                f"**Requested by:** {message.from_user.mention}"
            )
        else:
            await search_msg.edit_text("❌ Failed to start channel playback!")
            
    except Exception as e:
        logger.error(f"Channel play error: {e}")
        await search_msg.edit_text("❌ An error occurred while playing in channel!")

@Client.on_message(filters.command("cvplay"))
async def channel_play_video(client: Client, message: Message):
    bot = get_bot_instance(client)
    if not bot or not await bot.auth_manager.is_admin(message):
        await message.reply_text("❌ This command requires admin privileges!")
        return
    
    group_id = message.chat.id
    
    # Check if channel is connected
    if group_id not in channel_connections:
        await message.reply_text(
            "❌ No channel connected to this group!\n\n"
            "Use `/channelplay <@channel>` to connect a channel first."
        )
        return
    
    channel_id = channel_connections[group_id]
    
    if len(message.command) < 2:
        await message.reply_text("❌ Please provide a song name!\n\n**Usage:** `/cvplay <song name>`")
        return
    
    query = " ".join(message.command[1:])
    
    # Similar to cplay but with video
    search_msg = await message.reply_text("🔍 **Searching for video playback in channel...**")
    
    try:
        results = await bot.youtube_dl.search_youtube(query, limit=1)
        
        if not results:
            await search_msg.edit_text("❌ No videos found!")
            return
        
        result = results[0]
        stream_url = await bot.youtube_dl.get_stream_url(result['url'], "video")
        
        if not stream_url:
            await search_msg.edit_text("❌ Failed to get video stream URL!")
            return
        
        from music_player import QueueItem
        queue_item = QueueItem(
            title=result['title'],
            duration=result['duration'],
            requester=message.from_user.mention,
            stream_url=stream_url,
            is_video=True
        )
        
        success = await bot.music_player.play(channel_id, queue_item)
        
        if success:
            try:
                channel = await client.get_chat(channel_id)
                channel_name = channel.title
            except:
                channel_name = "Connected Channel"
            
            await search_msg.edit_text(
                f"📹 **Now Playing Video in Channel:**\n\n"
                f"**Channel:** {channel_name}\n"
                f"**Title:** {result['title']}\n"
                f"**Duration:** {result['duration']}\n"
                f"**Requested by:** {message.from_user.mention}"
            )
        else:
            await search_msg.edit_text("❌ Failed to start video playback!")
            
    except Exception as e:
        logger.error(f"Channel video play error: {e}")
        await search_msg.edit_text("❌ An error occurred!")

@Client.on_message(filters.command(["cplayforce", "cvplayforce"]))
async def channel_force_play(client: Client, message: Message):
    bot = get_bot_instance(client)
    if not bot or not await bot.auth_manager.is_admin(message):
        await message.reply_text("❌ This command requires admin privileges!")
        return
    
    group_id = message.chat.id
    
    if group_id not in channel_connections:
        await message.reply_text("❌ No channel connected!")
        return
    
    channel_id = channel_connections[group_id]
    is_video = message.command[0] == "cvplayforce"
    
    if len(message.command) < 2:
        await message.reply_text(f"❌ Please provide a song name!\n\n**Usage:** `/{message.command[0]} <song name>`")
        return
    
    query = " ".join(message.command[1:])
    
    search_msg = await message.reply_text("⚡ **Force playing in channel...**")
    
    try:
        results = await bot.youtube_dl.search_youtube(query, limit=1)
        
        if not results:
            await search_msg.edit_text("❌ No results found!")
            return
        
        result = results[0]
        stream_url = await bot.youtube_dl.get_stream_url(result['url'], "video" if is_video else "audio")
        
        if not stream_url:
            await search_msg.edit_text("❌ Failed to get stream URL!")
            return
        
        from music_player import QueueItem
        queue_item = QueueItem(
            title=result['title'],
            duration=result['duration'],
            requester=message.from_user.mention,
            stream_url=stream_url,
            is_video=is_video
        )
        
        success = await bot.music_player.play(channel_id, queue_item, force=True)
        
        if success:
            try:
                channel = await client.get_chat(channel_id)
                channel_name = channel.title
            except:
                channel_name = "Connected Channel"
            
            media_type = "📹 Video" if is_video else "🎵 Audio"
            
            await search_msg.edit_text(
                f"⚡ **Force Playing in Channel:**\n\n"
                f"**Channel:** {channel_name}\n"
                f"**Title:** {result['title']}\n"
                f"**Duration:** {result['duration']}\n"
                f"**Type:** {media_type}\n"
                f"**Requested by:** {message.from_user.mention}"
            )
        else:
            await search_msg.edit_text("❌ Failed to force play!")
            
    except Exception as e:
        logger.error(f"Channel force play error: {e}")
        await search_msg.edit_text("❌ An error occurred!")

@Client.on_message(filters.command("cqueue"))
async def channel_queue(client: Client, message: Message):
    bot = get_bot_instance(client)
    if not bot:
        return
    
    group_id = message.chat.id
    
    if group_id not in channel_connections:
        await message.reply_text("❌ No channel connected!")
        return
    
    channel_id = channel_connections[group_id]
    
    current = bot.music_player.get_current_playing(channel_id)
    queue = await bot.music_player.get_queue(channel_id)
    
    if not current and not queue:
        await message.reply_text("📝 **Channel queue is empty!**")
        return
    
    try:
        channel = await client.get_chat(channel_id)
        channel_name = channel.title
    except:
        channel_name = "Connected Channel"
    
    text = f"📝 **{channel_name} Queue:**\n\n"
    
    if current:
        text += f"🎵 **Now Playing:**\n**{current.title}** | `{current.duration}`\n**Requested by:** {current.requester}\n\n"
    
    if queue:
        text += "**📋 Up Next:**\n"
        for i, item in enumerate(queue[:10], 1):
            text += f"`{i}.` **{item.title}** | `{item.duration}`\n"
        
        if len(queue) > 10:
            text += f"\n**... and {len(queue) - 10} more songs**"
    
    await message.reply_text(text)

@Client.on_message(filters.command("cstop"))
async def channel_stop(client: Client, message: Message):
    bot = get_bot_instance(client)
    if not bot or not await bot.auth_manager.is_admin(message):
        await message.reply_text("❌ This command requires admin privileges!")
        return
    
    group_id = message.chat.id
    
    if group_id not in channel_connections:
        await message.reply_text("❌ No channel connected!")
        return
    
    channel_id = channel_connections[group_id]
    
    success = await bot.music_player.stop(channel_id)
    
    if success:
        try:
            channel = await client.get_chat(channel_id)
            channel_name = channel.title
        except:
            channel_name = "Connected Channel"
        
        await message.reply_text(f"⏹ **Stopped playback in {channel_name}**")
    else:
        await message.reply_text("❌ Failed to stop channel playback!")

@Client.on_message(filters.command("disconnect"))
async def disconnect_channel(client: Client, message: Message):
    bot = get_bot_instance(client)
    if not bot or not await bot.auth_manager.is_admin(message):
        await message.reply_text("❌ This command requires admin privileges!")
        return
    
    group_id = message.chat.id
    
    if group_id not in channel_connections:
        await message.reply_text("❌ No channel connected to this group!")
        return
    
    channel_id = channel_connections[group_id]
    
    try:
        # Stop playback if active
        await bot.music_player.stop(channel_id)
        
        # Get channel name
        try:
            channel = await client.get_chat(channel_id)
            channel_name = channel.title
        except:
            channel_name = "Channel"
        
        # Disconnect
        del channel_connections[group_id]
        
        await message.reply_text(
            f"🔌 **Channel Disconnected**\n\n"
            f"**{channel_name}** has been disconnected from this group.\n"
            f"Use `/channelplay` to connect a channel again."
        )
        
        logger.info(f"Channel {channel_id} disconnected from group {group_id}")
        
    except Exception as e:
        logger.error(f"Channel disconnect error: {e}")
        await message.reply_text("❌ Failed to disconnect channel!")

@Client.on_message(filters.command("connected"))
async def show_connected_channel(client: Client, message: Message):
    group_id = message.chat.id
    
    if group_id not in channel_connections:
        await message.reply_text("❌ No channel connected to this group!")
        return
    
    channel_id = channel_connections[group_id]
    
    try:
        channel = await client.get_chat(channel_id)
        bot = get_bot_instance(client)
        
        # Get channel status
        current = bot.music_player.get_current_playing(channel_id) if bot else None
        queue_count = len(await bot.music_player.get_queue(channel_id)) if bot else 0
        
        status = "🎵 Playing" if current else "⏸ Idle"
        
        await message.reply_text(
            f"🔗 **Connected Channel Info:**\n\n"
            f"**Channel:** {channel.title}\n"
            f"**Username:** @{channel.username if channel.username else 'None'}\n"
            f"**ID:** `{channel.id}`\n"
            f"**Status:** {status}\n"
            f"**Queue:** {queue_count} songs\n\n"
            f"**Current Song:** {current.title if current else 'None'}"
        )
        
    except Exception as e:
        logger.error(f"Show connected error: {e}")
        await message.reply_text("❌ Failed to get channel info!")title
    except:
        channel_name = "Connected Channel"
    
    text = f"📝 **{channel_name} Queue:**\n\n"
    
    if current:
        text += f"🎵 **Now Playing:**\n**{current.title}** | `{current.duration}`\n**Requested by:** {current.requester}\n\n"
    
    if queue:
        text += "**📋 Up Next:**\n"
        for i, item in enumerate(queue[:10], 1):
            text += f"`{i}.` **{item.title}** | `{item.duration}`\n"
        
        if len(queue) > 10:
            text += f"\n**... and {len(queue) - 10} more songs**"
    
    await message.reply_text(text)

@Client.on_message(filters.command("cstop"))
async def channel_stop(client: Client, message: Message):
    bot = get_bot_instance(client)
    if not bot or not await bot.auth_manager.is_admin(message):
        await message.reply_text("❌ This command requires admin privileges!")
        return
    
    group_id = message.chat.id
    
    if group_id not in channel_connections:
        await message.reply_text("❌ No channel connected!")
        return
    
    channel_id = channel_connections[group_id]
    
    success = await bot.music_player.stop(channel_id)
    
    if success:
        try:
            channel = await client.get_chat(channel_id)
            channel_name = channel.title
        except:
            channel_name = "Connected Channel"
        
        await message.reply_text(f"⏹ **Stopped playback in {channel_name}**")
    else:
        await message.reply_text("❌ Failed to stop channel playback!")

@Client.on_message(filters.command("disconnect"))
async def disconnect_channel(client: Client, message: Message):
    bot = get_bot_instance(client)
    if not bot or not await bot.auth_manager.is_admin(message):
        await message.reply_text("❌ This command requires admin privileges!")
        return
    
    group_id = message.chat.id
    
    if group_id not in channel_connections:
        await message.reply_text("❌ No channel connected to this group!")
        return
    
    channel_id = channel_connections[group_id]
    
    try:
        # Stop playback if active
        await bot.music_player.stop(channel_id)
        
        # Get channel name
        try:
            channel = await client.get_chat(channel_id)
            channel_name = channel.title
        except:
            channel_name = "Channel"
        
        # Disconnect
        del channel_connections[group_id]
        
        await message.reply_text(
            f"🔌 **Channel Disconnected**\n\n"
            f"**{channel_name}** has been disconnected from this group.\n"
            f"Use `/channelplay` to connect a channel again."
        )
        
        logger.info(f"Channel {channel_id} disconnected from group {group_id}")
        
    except Exception as e:
        logger.error(f"Channel disconnect error: {e}")
        await message.reply_text("❌ Failed to disconnect channel!")

@Client.on_message(filters.command("connected"))
async def show_connected_channel(client: Client, message: Message):
    group_id = message.chat.id
    
    if group_id not in channel_connections:
        await message.reply_text("❌ No channel connected to this group!")
        return
    
    channel_id = channel_connections[group_id]
    
    try:
        channel = await
