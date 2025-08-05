import asyncio
import os
import random
from typing import Dict, List, Optional
from pyrogram import Client
from pyrogram.types import Message
from pytgcalls import PyTgCalls, StreamType
from pytgcalls.types.input_stream import AudioPiped, VideoPiped, AudioVideoPiped
from pytgcalls.exceptions import NoActiveGroupCall, GroupCallNotFound
import logging

logger = logging.getLogger(__name__)

class QueueItem:
    def __init__(self, title: str, duration: str, requester: str, file_path: str = None, 
                 stream_url: str = None, is_video: bool = False):
        self.title = title
        self.duration = duration
        self.requester = requester
        self.file_path = file_path
        self.stream_url = stream_url
        self.is_video = is_video
        self.position = 0

class MusicPlayer:
    def __init__(self):
        self.pytgcalls = None
        self.queues: Dict[int, List[QueueItem]] = {}
        self.current_playing: Dict[int, QueueItem] = {}
        self.loop_mode: Dict[int, int] = {}  # 0: off, 1: current, 2: queue
        self.loop_count: Dict[int, int] = {}
        self.is_paused: Dict[int, bool] = {}
        self.playback_speed: Dict[int, float] = {}
        self.active_chats: List[int] = []
        
    async def initialize(self, client: Client):
        """Initialize PyTgCalls"""
        self.pytgcalls = PyTgCalls(client)
        await self.pytgcalls.start()
        
        # Set up handlers
        @self.pytgcalls.on_stream_end()
        async def on_stream_end(client, update):
            chat_id = update.chat_id
            await self.handle_stream_end(chat_id)
            
        @self.pytgcalls.on_closed_voice_chat()
        async def on_closed_vc(client, chat_id):
            await self.cleanup_chat(chat_id)
    
    async def join_voice_chat(self, chat_id: int) -> bool:
        """Join voice chat"""
        try:
            await self.pytgcalls.join_group_call(
                chat_id,
                AudioPiped("silence.mp3"),  # Dummy audio
                stream_type=StreamType().local_stream
            )
            if chat_id not in self.active_chats:
                self.active_chats.append(chat_id)
            return True
        except Exception as e:
            logger.error(f"Failed to join VC in {chat_id}: {e}")
            return False
    
    async def leave_voice_chat(self, chat_id: int) -> bool:
        """Leave voice chat"""
        try:
            await self.pytgcalls.leave_group_call(chat_id)
            await self.cleanup_chat(chat_id)
            return True
        except Exception as e:
            logger.error(f"Failed to leave VC in {chat_id}: {e}")
            return False
    
    async def play(self, chat_id: int, item: QueueItem, force: bool = False) -> bool:
        """Play a song"""
        try:
            if force or not self.current_playing.get(chat_id):
                # Join VC if not already joined
                if chat_id not in self.active_chats:
                    success = await self.join_voice_chat(chat_id)
                    if not success:
                        return False
                
                # Prepare stream
                if item.is_video:
                    if item.file_path:
                        stream = AudioVideoPiped(item.file_path)
                    else:
                        stream = AudioVideoPiped(item.stream_url)
                else:
                    if item.file_path:
                        stream = AudioPiped(item.file_path)
                    else:
                        stream = AudioPiped(item.stream_url)
                
                # Change stream
                await self.pytgcalls.change_stream(
                    chat_id,
                    stream
                )
                
                self.current_playing[chat_id] = item
                self.is_paused[chat_id] = False
                return True
            else:
                # Add to queue
                await self.add_to_queue(chat_id, item)
                return True
                
        except Exception as e:
            logger.error(f"Failed to play in {chat_id}: {e}")
            return False
    
    async def pause(self, chat_id: int) -> bool:
        """Pause playback"""
        try:
            await self.pytgcalls.pause_stream(chat_id)
            self.is_paused[chat_id] = True
            return True
        except Exception as e:
            logger.error(f"Failed to pause in {chat_id}: {e}")
            return False
    
    async def resume(self, chat_id: int) -> bool:
        """Resume playback"""
        try:
            await self.pytgcalls.resume_stream(chat_id)
            self.is_paused[chat_id] = False
            return True
        except Exception as e:
            logger.error(f"Failed to resume in {chat_id}: {e}")
            return False
    
    async def skip(self, chat_id: int) -> bool:
        """Skip current song"""
        try:
            await self.handle_stream_end(chat_id)
            return True
        except Exception as e:
            logger.error(f"Failed to skip in {chat_id}: {e}")
            return False
    
    async def stop(self, chat_id: int) -> bool:
        """Stop playback"""
        try:
            await self.pytgcalls.leave_group_call(chat_id)
            await self.cleanup_chat(chat_id)
            return True
        except Exception as e:
            logger.error(f"Failed to stop in {chat_id}: {e}")
            return False
    
    async def set_speed(self, chat_id: int, speed: float) -> bool:
        """Set playback speed"""
        try:
            # Note: This would require custom implementation with FFmpeg
            self.playback_speed[chat_id] = speed
            # Restart current stream with new speed
            current = self.current_playing.get(chat_id)
            if current:
                await self.play(chat_id, current, force=True)
            return True
        except Exception as e:
            logger.error(f"Failed to set speed in {chat_id}: {e}")
            return False
    
    async def seek(self, chat_id: int, seconds: int) -> bool:
        """Seek to position"""
        try:
            current = self.current_playing.get(chat_id)
            if current:
                current.position = seconds
                # This would require custom implementation
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to seek in {chat_id}: {e}")
            return False
    
    async def add_to_queue(self, chat_id: int, item: QueueItem):
        """Add item to queue"""
        if chat_id not in self.queues:
            self.queues[chat_id] = []
        self.queues[chat_id].append(item)
    
    async def get_queue(self, chat_id: int) -> List[QueueItem]:
        """Get current queue"""
        return self.queues.get(chat_id, [])
    
    async def shuffle_queue(self, chat_id: int) -> bool:
        """Shuffle queue"""
        try:
            queue = self.queues.get(chat_id, [])
            if len(queue) > 1:
                random.shuffle(queue)
                self.queues[chat_id] = queue
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to shuffle queue in {chat_id}: {e}")
            return False
    
    async def clear_queue(self, chat_id: int):
        """Clear queue"""
        self.queues[chat_id] = []
    
    async def set_loop(self, chat_id: int, mode: int, count: int = 0):
        """Set loop mode"""
        self.loop_mode[chat_id] = mode
        if count > 0:
            self.loop_count[chat_id] = count
    
    async def handle_stream_end(self, chat_id: int):
        """Handle when stream ends"""
        try:
            current = self.current_playing.get(chat_id)
            loop_mode = self.loop_mode.get(chat_id, 0)
            
            # Handle loop
            if loop_mode == 1 and current:  # Loop current
                count = self.loop_count.get(chat_id, 0)
                if count > 0:
                    self.loop_count[chat_id] = count - 1
                    await self.play(chat_id, current, force=True)
                    return
                elif count == 0:  # Infinite loop
                    await self.play(chat_id, current, force=True)
                    return
            
            # Play next in queue
            queue = self.queues.get(chat_id, [])
            if queue:
                next_item = queue.pop(0)
                await self.play(chat_id, next_item, force=True)
                
                # Handle queue loop
                if loop_mode == 2 and current:
                    await self.add_to_queue(chat_id, current)
            else:
                # No more songs, leave after timeout
                self.current_playing.pop(chat_id, None)
                asyncio.create_task(self.auto_leave(chat_id))
                
        except Exception as e:
            logger.error(f"Error handling stream end in {chat_id}: {e}")
    
    async def auto_leave(self, chat_id: int):
        """Auto leave after inactivity"""
        await asyncio.sleep(300)  # 5 minutes
        if chat_id in self.active_chats and not self.current_playing.get(chat_id):
            await self.leave_voice_chat(chat_id)
    
    async def cleanup_chat(self, chat_id: int):
        """Cleanup chat data"""
        self.current_playing.pop(chat_id, None)
        self.queues.pop(chat_id, None)
        self.loop_mode.pop(chat_id, None)
        self.loop_count.pop(chat_id, None)
        self.is_paused.pop(chat_id, None)
        self.playback_speed.pop(chat_id, None)
        if chat_id in self.active_chats:
            self.active_chats.remove(chat_id)
    
    def get_current_playing(self, chat_id: int) -> Optional[QueueItem]:
        """Get currently playing item"""
        return self.current_playing.get(chat_id)
    
    def is_playing(self, chat_id: int) -> bool:
        """Check if something is playing"""
        return chat_id in self.current_playing and not self.is_paused.get(chat_id, False)
    
    def get_total_queue_count(self) -> int:
        """Get total songs in all queues"""
        return sum(len(queue) for queue in self.queues.values())
    
    async def get_chat_info(self, chat_id: int) -> dict:
        """Get chat playback info"""
        current = self.current_playing.get(chat_id)
        queue = self.queues.get(chat_id, [])
        
        return {
            "current": current,
            "queue_count": len(queue),
            "is_playing": self.is_playing(chat_id),
            "is_paused": self.is_paused.get(chat_id, False),
            "loop_mode": self.loop_mode.get(chat_id, 0),
            "speed": self.playback_speed.get(chat_id, 1.0)
        }
    
