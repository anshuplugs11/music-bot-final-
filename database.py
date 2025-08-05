import asyncio
import sqlite3
import aiosqlite
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = "music_bot.db"):
        self.db_path = db_path
        self.connection = None
    
    async def connect(self):
        """Connect to database and create tables"""
        self.connection = await aiosqlite.connect(self.db_path)
        await self.create_tables()
        logger.info("Database connected successfully")
    
    async def disconnect(self):
        """Disconnect from database"""
        if self.connection:
            await self.connection.close()
    
    async def create_tables(self):
        """Create necessary tables"""
        await self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_banned INTEGER DEFAULT 0,
                download_count INTEGER DEFAULT 0
            );
            
            CREATE TABLE IF NOT EXISTS chats (
                chat_id INTEGER PRIMARY KEY,
                chat_title TEXT,
                chat_type TEXT,
                join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_blacklisted INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1
            );
            
            CREATE TABLE IF NOT EXISTS authorized_users (
                chat_id INTEGER,
                user_id INTEGER,
                authorized_by INTEGER,
                auth_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (chat_id, user_id)
            );
            
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                chat_id INTEGER,
                title TEXT,
                url TEXT,
                file_path TEXT,
                download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                format_type TEXT,
                file_size INTEGER
            );
            
            CREATE TABLE IF NOT EXISTS banned_users (
                user_id INTEGER PRIMARY KEY,
                banned_by INTEGER,
                reason TEXT,
                ban_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS blacklisted_chats (
                chat_id INTEGER PRIMARY KEY,
                blacklisted_by INTEGER,
                reason TEXT,
                blacklist_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS bot_stats (
                stat_name TEXT PRIMARY KEY,
                stat_value INTEGER,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS playlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                playlist_name TEXT,
                songs TEXT,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await self.connection.commit()
    
    # User Management
    async def add_user(self, user_id: int, username: str = None, first_name: str = None):
        """Add or update user"""
        try:
            await self.connection.execute("""
                INSERT OR REPLACE INTO users (user_id, username, first_name)
                VALUES (?, ?, ?)
            """, (user_id, username, first_name))
            await self.connection.commit()
        except Exception as e:
            logger.error(f"Error adding user {user_id}: {e}")
    
    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user information"""
        try:
            async with self.connection.execute("""
                SELECT * FROM users WHERE user_id = ?
            """, (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    columns = [description[0] for description in cursor.description]
                    return dict(zip(columns, row))
                return None
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None
    
    async def get_users_count(self) -> int:
        """Get total users count"""
        try:
            async with self.connection.execute("SELECT COUNT(*) FROM users") as cursor:
                result = await cursor.fetchone()
                return result[0] if result else 0
        except Exception as e:
            logger.error(f"Error getting users count: {e}")
            return 0
    
    async def ban_user(self, user_id: int, banned_by: int, reason: str = None):
        """Ban a user globally"""
        try:
            await self.connection.execute("""
                INSERT OR REPLACE INTO banned_users (user_id, banned_by, reason)
                VALUES (?, ?, ?)
            """, (user_id, banned_by, reason))
            
            await self.connection.execute("""
                UPDATE users SET is_banned = 1 WHERE user_id = ?
            """, (user_id,))
            
            await self.connection.commit()
        except Exception as e:
            logger.error(f"Error banning user {user_id}: {e}")
    
    async def unban_user(self, user_id: int):
        """Unban a user"""
        try:
            await self.connection.execute("DELETE FROM banned_users WHERE user_id = ?", (user_id,))
            await self.connection.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,))
            await self.connection.commit()
        except Exception as e:
            logger.error(f"Error unbanning user {user_id}: {e}")
    
    async def is_user_banned(self, user_id: int) -> bool:
        """Check if user is banned"""
        try:
            async with self.connection.execute("""
                SELECT 1 FROM banned_users WHERE user_id = ?
            """, (user_id,)) as cursor:
                result = await cursor.fetchone()
                return result is not None
        except Exception as e:
            logger.error(f"Error checking ban status for {user_id}: {e}")
            return False
    
    async def get_banned_users(self) -> List[Dict]:
        """Get all banned users"""
        try:
            async with self.connection.execute("""
                SELECT bu.*, u.username, u.first_name
                FROM banned_users bu
                LEFT JOIN users u ON bu.user_id = u.user_id
                ORDER BY bu.ban_date DESC
            """) as cursor:
                rows = await cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Error getting banned users: {e}")
            return []
    
    # Chat Management
    async def add_chat(self, chat_id: int, chat_title: str = None, chat_type: str = None):
        """Add or update chat"""
        try:
            await self.connection.execute("""
                INSERT OR REPLACE INTO chats (chat_id, chat_title, chat_type)
                VALUES (?, ?, ?)
            """, (chat_id, chat_title, chat_type))
            await self.connection.commit()
        except Exception as e:
            logger.error(f"Error adding chat {chat_id}: {e}")
    
    async def get_chats_count(self) -> int:
        """Get total chats count"""
        try:
            async with self.connection.execute("SELECT COUNT(*) FROM chats WHERE is_active = 1") as cursor:
                result = await cursor.fetchone()
                return result[0] if result else 0
        except Exception as e:
            logger.error(f"Error getting chats count: {e}")
            return 0
    
    async def blacklist_chat(self, chat_id: int, blacklisted_by: int, reason: str = None):
        """Blacklist a chat"""
        try:
            await self.connection.execute("""
                INSERT OR REPLACE INTO blacklisted_chats (chat_id, blacklisted_by, reason)
                VALUES (?, ?, ?)
            """, (chat_id, blacklisted_by, reason))
            
            await self.connection.execute("""
                UPDATE chats SET is_blacklisted = 1 WHERE chat_id = ?
            """, (chat_id,))
            
            await self.connection.commit()
        except Exception as e:
            logger.error(f"Error blacklisting chat {chat_id}: {e}")
    
    async def whitelist_chat(self, chat_id: int):
        """Remove chat from blacklist"""
        try:
            await self.connection.execute("DELETE FROM blacklisted_chats WHERE chat_id = ?", (chat_id,))
            await self.connection.execute("UPDATE chats SET is_blacklisted = 0 WHERE chat_id = ?", (chat_id,))
            await self.connection.commit()
        except Exception as e:
            logger.error(f"Error whitelisting chat {chat_id}: {e}")
    
    async def is_chat_blacklisted(self, chat_id: int) -> bool:
        """Check if chat is blacklisted"""
        try:
            async with self.connection.execute("""
                SELECT 1 FROM blacklisted_chats WHERE chat_id = ?
            """, (chat_id,)) as cursor:
                result = await cursor.fetchone()
                return result is not None
        except Exception as e:
            logger.error(f"Error checking blacklist status for {chat_id}: {e}")
            return False
    
    # Authorization Management
    async def authorize_user(self, chat_id: int, user_id: int, authorized_by: int):
        """Authorize user in a chat"""
        try:
            await self.connection.execute("""
                INSERT OR REPLACE INTO authorized_users (chat_id, user_id, authorized_by)
                VALUES (?, ?, ?)
            """, (chat_id, user_id, authorized_by))
            await self.connection.commit()
        except Exception as e:
            logger.error(f"Error authorizing user {user_id} in chat {chat_id}: {e}")
    
    async def unauthorize_user(self, chat_id: int, user_id: int):
        """Remove user authorization"""
        try:
            await self.connection.execute("""
                DELETE FROM authorized_users WHERE chat_id = ? AND user_id = ?
            """, (chat_id, user_id))
            await self.connection.commit()
        except Exception as e:
            logger.error(f"Error removing authorization for user {user_id} in chat {chat_id}: {e}")
    
    async def is_user_authorized(self, chat_id: int, user_id: int) -> bool:
        """Check if user is authorized in chat"""
        try:
            async with self.connection.execute("""
                SELECT 1 FROM authorized_users WHERE chat_id = ? AND user_id = ?
            """, (chat_id, user_id)) as cursor:
                result = await cursor.fetchone()
                return result is not None
        except Exception as e:
            logger.error(f"Error checking authorization for user {user_id} in chat {chat_id}: {e}")
            return False
    
    async def get_authorized_users(self, chat_id: int) -> List[Dict]:
        """Get authorized users for a chat"""
        try:
            async with self.connection.execute("""
                SELECT au.*, u.username, u.first_name
                FROM authorized_users au
                LEFT JOIN users u ON au.user_id = u.user_id
                WHERE au.chat_id = ?
                ORDER BY au.auth_date DESC
            """, (chat_id,)) as cursor:
                rows = await cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Error getting authorized users for chat {chat_id}: {e}")
            return []
    
    # Download Management
    async def add_download(self, user_id: int, chat_id: int, title: str, url: str, 
                          file_path: str, format_type: str, file_size: int = 0):
        """Record a download"""
        try:
            await self.connection.execute("""
                INSERT INTO downloads (user_id, chat_id, title, url, file_path, format_type, file_size)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, chat_id, title, url, file_path, format_type, file_size))
            
            # Update user download count
            await self.connection.execute("""
                UPDATE users SET download_count = download_count + 1 WHERE user_id = ?
            """, (user_id,))
            
            await self.connection.commit()
        except Exception as e:
            logger.error(f"Error recording download: {e}")
    
    async def get_downloads_today(self) -> int:
        """Get downloads count for today"""
        try:
            today = datetime.now().date()
            async with self.connection.execute("""
                SELECT COUNT(*) FROM downloads 
                WHERE DATE(download_date) = ?
            """, (today,)) as cursor:
                result = await cursor.fetchone()
                return result[0] if result else 0
        except Exception as e:
            logger.error(f"Error getting today's downloads: {e}")
            return 0
    
    async def get_user_downloads(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get user's recent downloads"""
        try:
            async with self.connection.execute("""
                SELECT * FROM downloads WHERE user_id = ?
                ORDER BY download_date DESC LIMIT ?
            """, (user_id, limit)) as cursor:
                rows = await cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Error getting downloads for user {user_id}: {e}")
            return []
    
    # Statistics
    async def update_stat(self, stat_name: str, stat_value: int):
        """Update bot statistics"""
        try:
            await self.connection.execute("""
                INSERT OR REPLACE INTO bot_stats (stat_name, stat_value, last_updated)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (stat_name, stat_value))
            await self.connection.commit()
        except Exception as e:
            logger.error(f"Error updating stat {stat_name}: {e}")
    
    async def get_stat(self, stat_name: str) -> int:
        """Get bot statistic"""
        try:
            async with self.connection.execute("""
                SELECT stat_value FROM bot_stats WHERE stat_name = ?
            """, (stat_name,)) as cursor:
                result = await cursor.fetchone()
                return result[0] if result else 0
        except Exception as e:
            logger.error(f"Error getting stat {stat_name}: {e}")
            return 0
    
    # Playlist Management
    async def create_playlist(self, user_id: int, playlist_name: str, songs: List[str]):
        """Create user playlist"""
        try:
            songs_json = ",".join(songs)
            await self.connection.execute("""
                INSERT INTO playlists (user_id, playlist_name, songs)
                VALUES (?, ?, ?)
            """, (user_id, playlist_name, songs_json))
            await self.connection.commit()
        except Exception as e:
            logger.error(f"Error creating playlist: {e}")
    
    async def get_user_playlists(self, user_id: int) -> List[Dict]:
        """Get user playlists"""
        try:
            async with self.connection.execute("""
                SELECT * FROM playlists WHERE user_id = ?
                ORDER BY created_date DESC
            """, (user_id,)) as cursor:
                rows = await cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                playlists = []
                for row in rows:
                    playlist = dict(zip(columns, row))
                    playlist['songs'] = playlist['songs'].split(',') if playlist['songs'] else []
                    playlists.append(playlist)
                return playlists
        except Exception as e:
            logger.error(f"Error getting playlists for user {user_id}: {e}")
            return []
    
    # Cleanup
    async def cleanup_old_downloads(self, days: int = 7):
        """Clean up old download records"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            await self.connection.execute("""
                DELETE FROM downloads WHERE download_date < ?
            """, (cutoff_date,))
            await self.connection.commit()
        except Exception as e:
            logger.error(f"Error cleaning up old downloads: {e}")
    
    async def get_all_chat_ids(self) -> List[int]:
        """Get all active chat IDs for broadcasting"""
        try:
            async with self.connection.execute("""
                SELECT chat_id FROM chats 
                WHERE is_active = 1 AND is_blacklisted = 0
            """) as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]
        except Exception as e:
            logger.error(f"Error getting chat IDs: {e}")
            return []
    
    async def get_all_user_ids(self) -> List[int]:
        """Get all user IDs for broadcasting"""
        try:
            async with self.connection.execute("""
                SELECT user_id FROM users WHERE is_banned = 0
            """) as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]
        except Exception as e:
            logger.error(f"Error getting user IDs: {e}")
            return []
