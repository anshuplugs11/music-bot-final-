from pyrogram.types import Message
from pyrogram.enums import ChatMemberStatus
from config import Config
from database import Database
import logging

logger = logging.getLogger(__name__)

class AuthManager:
    def __init__(self, db: Database):
        self.db = db
    
    async def is_authorized(self, message: Message) -> bool:
        """Check if user is authorized to use music commands"""
        user_id = message.from_user.id
        chat_id = message.chat.id
        
        # Sudoers have full access everywhere
        if user_id in Config.SUDOERS:
            return True
        
        # Check if user is globally banned
        if await self.db.is_user_banned(user_id):
            return False
        
        # Check if chat is blacklisted
        if await self.db.is_chat_blacklisted(chat_id):
            return False
        
        # Private chats - allow if not banned
        if message.chat.type.name == "PRIVATE":
            return True
        
        # Group chats - check authorization
        if message.chat.type.name in ["GROUP", "SUPERGROUP"]:
            # Check if user is authorized in this chat
            if await self.db.is_user_authorized(chat_id, user_id):
                return True
            
            # Check if user is admin
            try:
                member = await message._client.get_chat_member(chat_id, user_id)
                if member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
                    return True
            except Exception as e:
                logger.error(f"Error checking admin status: {e}")
        
        return False
    
    async def is_admin(self, message: Message) -> bool:
        """Check if user is admin in the chat"""
        user_id = message.from_user.id
        chat_id = message.chat.id
        
        # Sudoers are always admin
        if user_id in Config.SUDOERS:
            return True
        
        # Private chats - user is always admin of their own chat
        if message.chat.type.name == "PRIVATE":
            return True
        
        # Group chats
        try:
            member = await message._client.get_chat_member(chat_id, user_id)
            return member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]
        except Exception as e:
            logger.error(f"Error checking admin status: {e}")
            return False
    
    async def is_owner(self, message: Message) -> bool:
        """Check if user is owner of the chat"""
        user_id = message.from_user.id
        chat_id = message.chat.id
        
        # Sudoers are always owner
        if user_id in Config.SUDOERS:
            return True
        
        # Private chats
        if message.chat.type.name == "PRIVATE":
            return True
        
        # Group chats
        try:
            member = await message._client.get_chat_member(chat_id, user_id)
            return member.status == ChatMemberStatus.OWNER
        except Exception as e:
            logger.error(f"Error checking owner status: {e}")
            return False
    
    async def can_manage_voice_chats(self, message: Message) -> bool:
        """Check if user can manage voice chats"""
        user_id = message.from_user.id
        chat_id = message.chat.id
        
        # Sudoers can manage everywhere
        if user_id in Config.SUDOERS:
            return True
        
        # Private chats
        if message.chat.type.name == "PRIVATE":
            return True
        
        # Group chats - check admin permissions
        try:
            member = await message._client.get_chat_member(chat_id, user_id)
            if member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
                # Check specific permissions
                if hasattr(member, 'privileges') and member.privileges:
                    return member.privileges.can_manage_video_chats
                return True  # Assume admin can manage if privileges not available
        except Exception as e:
            logger.error(f"Error checking voice chat permissions: {e}")
        
        return False
    
    def get_auth_failed_text(self, reason: str = "general") -> str:
        """Get authorization failed message"""
        messages = {
            "general": "❌ You're not authorized to use this command!",
            "admin": "❌ This command requires admin privileges!",
            "owner": "❌ This command requires owner privileges!",
            "banned": "❌ You're banned from using this bot!",
            "blacklisted": "❌ This chat is blacklisted!",
            "voice_chat": "❌ You need voice chat management permissions!"
        }
        return messages.get(reason, messages["general"])
    
    async def authorize_user_in_chat(self, chat_id: int, user_id: int, authorized_by: int) -> bool:
        """Authorize user in a specific chat"""
        try:
            await self.db.authorize_user(chat_id, user_id, authorized_by)
            return True
        except Exception as e:
            logger.error(f"Error authorizing user {user_id} in chat {chat_id}: {e}")
            return False
    
    async def unauthorize_user_in_chat(self, chat_id: int, user_id: int) -> bool:
        """Remove user authorization in a specific chat"""
        try:
            await self.db.unauthorize_user(chat_id, user_id)
            return True
        except Exception as e:
            logger.error(f"Error unauthorizing user {user_id} in chat {chat_id}: {e}")
            return False
    
    async def get_authorized_users_list(self, chat_id: int) -> list:
        """Get list of authorized users in a chat"""
        try:
            return await self.db.get_authorized_users(chat_id)
        except Exception as e:
            logger.error(f"Error getting authorized users for chat {chat_id}: {e}")
            return []
