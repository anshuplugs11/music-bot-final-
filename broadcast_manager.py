import asyncio
from pyrogram import Client
from pyrogram.types import Message
from pyrogram.errors import FloodWait, ChatWriteForbidden, UserIsBlocked, PeerIdInvalid
from database import Database
from config import Config
import logging

logger = logging.getLogger(__name__)

class BroadcastManager:
    def __init__(self, client: Client, db: Database):
        self.client = client
        self.db = db
        self.assistant_client = None
        
    async def initialize_assistant(self):
        """Initialize assistant client for broadcasting"""
        if Config.ASSISTANT_SESSION:
            try:
                self.assistant_client = Client(
                    Config.ASSISTANT_SESSION,
                    api_id=Config.ASSISTANT_API_ID,
                    api_hash=Config.ASSISTANT_API_HASH
                )
                await self.assistant_client.start()
                logger.info("Assistant client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize assistant client: {e}")
    
    async def broadcast_message(self, message: str, options: dict = None) -> dict:
        """Broadcast message to chats/users"""
        if not options:
            options = {}
        
        results = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "blocked": 0,
            "deleted": 0,
            "errors": []
        }
        
        # Determine broadcast targets
        targets = []
        
        if options.get("user"):
            # Broadcast to users
            user_ids = await self.db.get_all_user_ids()
            targets.extend([("user", uid) for uid in user_ids])
        else:
            # Broadcast to chats (default)
            chat_ids = await self.db.get_all_chat_ids()
            targets.extend([("chat", cid) for cid in chat_ids])
        
        results["total"] = len(targets)
        
        # Choose client
        client = self.assistant_client if options.get("assistant") and self.assistant_client else self.client
        
        # Broadcast with rate limiting
        semaphore = asyncio.Semaphore(20)  # Limit concurrent requests
        
        async def send_to_target(target_type, target_id):
            async with semaphore:
                try:
                    if options.get("nobot") and target_id == self.client.me.id:
                        return "skipped"
                    
                    # Prepare message options
                    kwargs = {}
                    if options.get("pin") or options.get("pinloud"):
                        kwargs["disable_notification"] = not options.get("pinloud")
                    
                    # Send message
                    sent_message = await client.send_message(
                        target_id,
                        message,
                        **kwargs
                    )
                    
                    # Pin message if requested
                    if options.get("pin") or options.get("pinloud"):
                        try:
                            await client.pin_chat_message(
                                target_id,
                                sent_message.id,
                                disable_notification=not options.get("pinloud")
                            )
                        except Exception as pin_error:
                            logger.warning(f"Failed to pin message in {target_id}: {pin_error}")
                    
                    await asyncio.sleep(0.1)  # Rate limiting
                    return "success"
                    
                except FloodWait as e:
                    logger.warning(f"FloodWait {e.value} seconds for {target_id}")
                    await asyncio.sleep(e.value)
                    return "flood_wait"
                    
                except (UserIsBlocked, ChatWriteForbidden):
                    return "blocked"
                    
                except PeerIdInvalid:
                    return "deleted"
                    
                except Exception as e:
                    logger.error(f"Broadcast error for {target_id}: {e}")
                    return f"error: {str(e)}"
        
        # Execute broadcasts
        tasks = [send_to_target(t_type, t_id) for t_type, t_id in targets]
        
        # Process in batches to avoid overwhelming
        batch_size = 50
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    results["failed"] += 1
                    results["errors"].append(str(result))
                elif result == "success":
                    results["success"] += 1
                elif result == "blocked":
                    results["blocked"] += 1
                elif result == "deleted":
                    results["deleted"] += 1
                elif result.startswith("error"):
                    results["failed"] += 1
                    results["errors"].append(result)
            
            # Small delay between batches
            await asyncio.sleep(1)
        
        return results
    
    def parse_broadcast_options(self, text: str) -> tuple:
        """Parse broadcast command options"""
        options = {
            "pin": False,
            "pinloud": False,
            "user": False,
            "assistant": False,
            "nobot": False
        }
        
        parts = text.split()
        message_parts = []
        
        for part in parts:
            if part.startswith("-"):
                option = part[1:].lower()
                if option in options:
                    options[option] = True
            else:
                message_parts.append(part)
        
        message = " ".join(message_parts)
        return message, options
    
    async def get_broadcast_stats(self) -> dict:
        """Get broadcast statistics"""
        total_chats = await self.db.get_chats_count()
        total_users = await self.db.get_users_count()
        
        return {
            "total_chats": total_chats,
            "total_users": total_users,
            "assistant_available": self.assistant_client is not None
        }
    
    def get_broadcast_result_text(self, results: dict) -> str:
        """Format broadcast results"""
        text = f"""
📢 **Broadcast Completed**

📊 **Results:**
• **Total Targets:** {results['total']}
• **✅ Successful:** {results['success']}
• **❌ Failed:** {results['failed']}
• **🚫 Blocked/Forbidden:** {results['blocked']}
• **🗑 Deleted Chats:** {results['deleted']}

**Success Rate:** {(results['success'] / results['total'] * 100):.1f}%
        """
        
        if results['errors']:
            text += f"\n**Recent Errors:**\n"
            for error in results['errors'][:5]:  # Show first 5 errors
                text += f"• `{error}`\n"
        
        return text
    
    async def test_broadcast(self, target_id: int, message: str) -> bool:
        """Test broadcast to a specific target"""
        try:
            await self.client.send_message(target_id, f"🧪 **Test Broadcast**\n\n{message}")
            return True
        except Exception as e:
            logger.error(f"Test broadcast failed: {e}")
            return False
