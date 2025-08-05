from pyrogram import Client, filters
from pyrogram.types import Message
from config import Config
import logging

logger = logging.getLogger(__name__)

def get_bot_instance(client):
    return getattr(client, 'bot_instance', None)

# Sudoer-only commands
@Client.on_message(filters.command("gban") & filters.user(Config.SUDOERS))
async def global_ban_user(client: Client, message: Message):
    bot = get_bot_instance(client)
    if not bot:
        return
    
    user_id = None
    reason = "No reason provided"
    
    # Get user from reply or command arguments
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        if len(message.command) > 1:
            reason = " ".join(message.command[1:])
    elif len(message.command) > 1:
        try:
            user_id = int(message.command[1])
            if len(message.command) > 2:
                reason = " ".join(message.command[2:])
        except ValueError:
            await message.reply_text("❌ Invalid user ID!")
            return
    else:
        await message.reply_text("❌ Please reply to a user or provide user ID!\n\n**Usage:** `/gban <user_id> [reason]`")
        return
    
    if user_id in Config.SUDOERS:
        await message.reply_text("❌ Cannot ban a sudoer!")
        return
    
    try:
        await bot.db.ban_user(user_id, message.from_user.id, reason)
        
        # Try to get user info
        try:
            user = await client.get_users(user_id)
            username = f"@{user.username}" if user.username else user.first_name
        except:
            username = f"User {user_id}"
        
        await message.reply_text(
            f"🔨 **User Globally Banned**\n\n"
            f"**User:** {username} (`{user_id}`)\n"
            f"**Reason:** {reason}\n"
            f"**Banned by:** {message.from_user.mention}"
        )
        
        # Log the ban
        logger.info(f"User {user_id} globally banned by {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"Global ban error: {e}")
        await message.reply_text("❌ Failed to ban user!")

@Client.on_message(filters.command("ungban") & filters.user(Config.SUDOERS))
async def global_unban_user(client: Client, message: Message):
    bot = get_bot_instance(client)
    if not bot:
        return
    
    user_id = None
    
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    elif len(message.command) > 1:
        try:
            user_id = int(message.command[1])
        except ValueError:
            await message.reply_text("❌ Invalid user ID!")
            return
    else:
        await message.reply_text("❌ Please reply to a user or provide user ID!\n\n**Usage:** `/ungban <user_id>`")
        return
    
    try:
        # Check if user is banned
        is_banned = await bot.db.is_user_banned(user_id)
        if not is_banned:
            await message.reply_text("❌ User is not banned!")
            return
        
        await bot.db.unban_user(user_id)
        
        try:
            user = await client.get_users(user_id)
            username = f"@{user.username}" if user.username else user.first_name
        except:
            username = f"User {user_id}"
        
        await message.reply_text(
            f"✅ **User Globally Unbanned**\n\n"
            f"**User:** {username} (`{user_id}`)\n"
            f"**Unbanned by:** {message.from_user.mention}"
        )
        
        logger.info(f"User {user_id} globally unbanned by {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"Global unban error: {e}")
        await message.reply_text("❌ Failed to unban user!")

@Client.on_message(filters.command("gbannedusers") & filters.user(Config.SUDOERS))
async def list_banned_users(client: Client, message: Message):
    bot = get_bot_instance(client)
    if not bot:
        return
    
    try:
        banned_users = await bot.db.get_banned_users()
        
        if not banned_users:
            await message.reply_text("✅ No globally banned users!")
            return
        
        text = "🔨 **Globally Banned Users:**\n\n"
        
        for i, user in enumerate(banned_users[:20], 1):
            username = user.get('username', 'No username')
            first_name = user.get('first_name', 'Unknown')
            text += f"`{i}.` **{first_name}** (@{username})\n"
            text += f"    **ID:** `{user['user_id']}`\n"
            text += f"    **Reason:** {user.get('reason', 'No reason')}\n\n"
        
        if len(banned_users) > 20:
            text += f"**... and {len(banned_users) - 20} more users**"
        
        await message.reply_text(text)
        
    except Exception as e:
        logger.error(f"List banned users error: {e}")
        await message.reply_text("❌ Failed to get banned users list!")

@Client.on_message(filters.command("blacklistchat") & filters.user(Config.SUDOERS))
async def blacklist_chat(client: Client, message: Message):
    bot = get_bot_instance(client)
    if not bot:
        return
    
    chat_id = message.chat.id
    reason = " ".join(message.command[1:]) if len(message.command) > 1 else "No reason provided"
    
    try:
        await bot.db.blacklist_chat(chat_id, message.from_user.id, reason)
        
        await message.reply_text(
            f"🚫 **Chat Blacklisted**\n\n"
            f"**Chat:** {message.chat.title or 'This Chat'}\n"
            f"**ID:** `{chat_id}`\n"
            f"**Reason:** {reason}\n"
            f"**Blacklisted by:** {message.from_user.mention}\n\n"
            f"**Bot will leave this chat now.**"
        )
        
        # Leave the chat
        await client.leave_chat(chat_id)
        logger.info(f"Chat {chat_id} blacklisted and left")
        
    except Exception as e:
        logger.error(f"Blacklist chat error: {e}")
        await message.reply_text("❌ Failed to blacklist chat!")

@Client.on_message(filters.command("whitelistchat") & filters.user(Config.SUDOERS))
async def whitelist_chat(client: Client, message: Message):
    bot = get_bot_instance(client)
    if not bot:
        return
    
    if len(message.command) < 2:
        await message.reply_text("❌ Please provide chat ID!\n\n**Usage:** `/whitelistchat <chat_id>`")
        return
    
    try:
        chat_id = int(message.command[1])
        
        is_blacklisted = await bot.db.is_chat_blacklisted(chat_id)
        if not is_blacklisted:
            await message.reply_text("❌ Chat is not blacklisted!")
            return
        
        await bot.db.whitelist_chat(chat_id)
        
        await message.reply_text(
            f"✅ **Chat Whitelisted**\n\n"
            f"**Chat ID:** `{chat_id}`\n"
            f"**Whitelisted by:** {message.from_user.mention}"
        )
        
        logger.info(f"Chat {chat_id} whitelisted by {message.from_user.id}")
        
    except ValueError:
        await message.reply_text("❌ Invalid chat ID!")
    except Exception as e:
        logger.error(f"Whitelist chat error: {e}")
        await message.reply_text("❌ Failed to whitelist chat!")

@Client.on_message(filters.command("maintenance") & filters.user(Config.SUDOERS))
async def toggle_maintenance(client: Client, message: Message):
    bot = get_bot_instance(client)
    if not bot:
        return
    
    bot.maintenance_mode = not bot.maintenance_mode
    status = "**ENABLED**" if bot.maintenance_mode else "**DISABLED**"
    
    await message.reply_text(
        f"🔧 **Maintenance Mode {status}**\n\n"
        f"{'⚠️ Bot is now in maintenance mode. Only sudoers can use the bot.' if bot.maintenance_mode else '✅ Bot is now available for all users.'}"
    )

@Client.on_message(filters.command("logs") & filters.user(Config.SUDOERS))
async def get_logs(client: Client, message: Message):
    try:
        if os.path.exists("bot.log"):
            await message.reply_document("bot.log", caption="📋 **Bot Logs**")
        else:
            await message.reply_text("❌ No log file found!")
    except Exception as e:
        logger.error(f"Get logs error: {e}")
        await message.reply_text("❌ Failed to send logs!")

@Client.on_message(filters.command("logger") & filters.user(Config.SUDOERS))
async def toggle_logger(client: Client, message: Message):
    bot = get_bot_instance(client)
    if not bot:
        return
    
    if len(message.command) < 2:
        await message.reply_text("❌ Please specify enable/disable!\n\n**Usage:** `/logger <on|off>`")
        return
    
    action = message.command[1].lower()
    
    if action in ["on", "enable", "true", "1"]:
        bot.logging_enabled = True
        await message.reply_text("✅ **Logging Enabled**")
    elif action in ["off", "disable", "false", "0"]:
        bot.logging_enabled = False
        await message.reply_text("❌ **Logging Disabled**")
    else:
        await message.reply_text("❌ Invalid option! Use: on/off")

# Chat admin commands
@Client.on_message(filters.command("auth"))
async def authorize_user(client: Client, message: Message):
    bot = get_bot_instance(client)
    if not bot or not await bot.auth_manager.is_admin(message):
        await message.reply_text("❌ This command requires admin privileges!")
        return
    
    if message.chat.type.name == "PRIVATE":
        await message.reply_text("❌ This command only works in groups!")
        return
    
    user_id = None
    username = None
    
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        username = message.reply_to_message.from_user.mention
    elif len(message.command) > 1:
        try:
            user_id = int(message.command[1])
            try:
                user = await client.get_users(user_id)
                username = user.mention
            except:
                username = f"User {user_id}"
        except ValueError:
            # Try to find by username
            try:
                user = await client.get_users(message.command[1])
                user_id = user.id
                username = user.mention
            except:
                await message.reply_text("❌ User not found!")
                return
    else:
        await message.reply_text("❌ Please reply to a user or provide user ID/username!\n\n**Usage:** `/auth <user_id|username>`")
        return
    
    chat_id = message.chat.id
    
    try:
        # Check if already authorized
        is_authorized = await bot.db.is_user_authorized(chat_id, user_id)
        if is_authorized:
            await message.reply_text("❌ User is already authorized!")
            return
        
        await bot.db.authorize_user(chat_id, user_id, message.from_user.id)
        
        await message.reply_text(
            f"✅ **User Authorized**\n\n"
            f"**User:** {username}\n"
            f"**Authorized by:** {message.from_user.mention}\n"
            f"**Chat:** {message.chat.title}"
        )
        
        logger.info(f"User {user_id} authorized in chat {chat_id} by {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"Authorization error: {e}")
        await message.reply_text("❌ Failed to authorize user!")

@Client.on_message(filters.command("unauth"))
async def unauthorize_user(client: Client, message: Message):
    bot = get_bot_instance(client)
    if not bot or not await bot.auth_manager.is_admin(message):
        await message.reply_text("❌ This command requires admin privileges!")
        return
    
    if message.chat.type.name == "PRIVATE":
        await message.reply_text("❌ This command only works in groups!")
        return
    
    user_id = None
    username = None
    
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        username = message.reply_to_message.from_user.mention
    elif len(message.command) > 1:
        try:
            user_id = int(message.command[1])
            try:
                user = await client.get_users(user_id)
                username = user.mention
            except:
                username = f"User {user_id}"
        except ValueError:
            try:
                user = await client.get_users(message.command[1])
                user_id = user.id
                username = user.mention
            except:
                await message.reply_text("❌ User not found!")
                return
    else:
        await message.reply_text("❌ Please reply to a user or provide user ID/username!\n\n**Usage:** `/unauth <user_id|username>`")
        return
    
    chat_id = message.chat.id
    
    try:
        is_authorized = await bot.db.is_user_authorized(chat_id, user_id)
        if not is_authorized:
            await message.reply_text("❌ User is not authorized!")
            return
        
        await bot.db.unauthorize_user(chat_id, user_id)
        
        await message.reply_text(
            f"❌ **User Authorization Removed**\n\n"
            f"**User:** {username}\n"
            f"**Removed by:** {message.from_user.mention}\n"
            f"**Chat:** {message.chat.title}"
        )
        
        logger.info(f"User {user_id} unauthorized in chat {chat_id} by {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"Unauthorization error: {e}")
        await message.reply_text("❌ Failed to remove authorization!")

@Client.on_message(filters.command("authusers"))
async def list_authorized_users(client: Client, message: Message):
    bot = get_bot_instance(client)
    if not bot:
        return
    
    if message.chat.type.name == "PRIVATE":
        await message.reply_text("❌ This command only works in groups!")
        return
    
    chat_id = message.chat.id
    
    try:
        authorized_users = await bot.db.get_authorized_users(chat_id)
        
        if not authorized_users:
            await message.reply_text("📝 **No authorized users in this chat!**")
            return
        
        text = f"👥 **Authorized Users in {message.chat.title}:**\n\n"
        
        for i, user in enumerate(authorized_users[:20], 1):
            username = f"@{user.get('username', 'No username')}"
            first_name = user.get('first_name', 'Unknown')
            text += f"`{i}.` **{first_name}** ({username})\n"
            text += f"    **ID:** `{user['user_id']}`\n\n"
        
        if len(authorized_users) > 20:
            text += f"**... and {len(authorized_users) - 20} more users**"
        
        await message.reply_text(text)
        
    except Exception as e:
        logger.error(f"List authorized users error: {e}")
        await message.reply_text("❌ Failed to get authorized users list!")

@Client.on_message(filters.command("broadcast") & filters.user(Config.SUDOERS))
async def broadcast_message(client: Client, message: Message):
    bot = get_bot_instance(client)
    if not bot:
        return
    
    if len(message.command) < 2:
        await message.reply_text(
            "❌ Please provide a message to broadcast!\n\n"
            "**Usage:** `/broadcast [options] <message>`\n\n"
            "**Options:**\n"
            "• `-pin` - Pin the message\n"
            "• `-pinloud` - Pin with notification\n"
            "• `-user` - Broadcast to users only\n"
            "• `-assistant` - Use assistant account\n"
            "• `-nobot` - Don't send to bot chats\n\n"
            "**Example:** `/broadcast -pin -user Hello everyone!`"
        )
        return
    
    # Parse message and options
    full_text = " ".join(message.command[1:])
    broadcast_text, options = bot.broadcast_manager.parse_broadcast_options(full_text)
    
    if not broadcast_text:
        await message.reply_text("❌ No message content provided!")
        return
    
    # Show broadcast info
    stats = await bot.broadcast_manager.get_broadcast_stats()
    target_count = stats['total_users'] if options.get('user') else stats['total_chats']
    
    status_msg = await message.reply_text(
        f"📢 **Starting Broadcast...**\n\n"
        f"**Target:** {'Users' if options.get('user') else 'Chats'}\n"
        f"**Count:** {target_count}\n"
        f"**Options:** {', '.join([k for k, v in options.items() if v]) or 'None'}\n\n"
        f"**Message Preview:**\n{broadcast_text[:100]}{'...' if len(broadcast_text) > 100 else ''}"
    )
    
    # Start broadcast
    try:
        results = await bot.broadcast_manager.broadcast_message(broadcast_text, options)
        
        result_text = bot.broadcast_manager.get_broadcast_result_text(results)
        await status_msg.edit_text(result_text)
        
        logger.info(f"Broadcast completed by {message.from_user.id}: {results}")
        
    except Exception as e:
        logger.error(f"Broadcast error: {e}")
        await status_msg.edit_text("❌ **Broadcast failed!**")

import os
