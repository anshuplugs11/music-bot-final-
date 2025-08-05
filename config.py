import os
from typing import List

class Config:
    # Bot Configuration
    API_ID = int(os.environ.get("API_ID", "12345678"))
    API_HASH = os.environ.get("API_HASH", "your_api_hash")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_bot_token")
    
    # Owner Configuration
    OWNER_ID = int(os.environ.get("OWNER_ID", "your_owner_id"))
    SUDOERS = list(map(int, os.environ.get("SUDOERS", str(OWNER_ID)).split()))
    
    # Assistant Bot (Optional for broadcasting)
    ASSISTANT_API_ID = int(os.environ.get("ASSISTANT_API_ID", API_ID))
    ASSISTANT_API_HASH = os.environ.get("ASSISTANT_API_HASH", API_HASH)
    ASSISTANT_SESSION = os.environ.get("ASSISTANT_SESSION", "assistant_session")
    
    # Database Configuration
    DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///music_bot.db")
    
    # Music Configuration
    DOWNLOAD_DIR = os.environ.get("DOWNLOAD_DIR", "downloads")
    MAX_DURATION = int(os.environ.get("MAX_DURATION", "3600"))  # 1 hour
    QUEUE_LIMIT = int(os.environ.get("QUEUE_LIMIT", "50"))
    
    # Spotify Configuration (Optional)
    SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
    SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")
    
    # YouTube Configuration
    YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
    
    # Chat Configuration
    LOG_CHAT_ID = int(os.environ.get("LOG_CHAT_ID", OWNER_ID))
    SUPPORT_CHAT = os.environ.get("SUPPORT_CHAT", "@your_support_chat")
    UPDATES_CHANNEL = os.environ.get("UPDATES_CHANNEL", "@your_channel")
    
    # Feature Toggles
    PRIVATE_BOT_MODE = bool(os.environ.get("PRIVATE_BOT_MODE", False))
    AUTO_LEAVE_TIME = int(os.environ.get("AUTO_LEAVE_TIME", "600"))  # 10 minutes
    
    # Render.com specific
    PORT = int(os.environ.get("PORT", "8000"))
    
    # Limits
    MAX_CONCURRENT_DOWNLOADS = int(os.environ.get("MAX_CONCURRENT_DOWNLOADS", "5"))
    MAX_PLAYLIST_SIZE = int(os.environ.get("MAX_PLAYLIST_SIZE", "100"))
    
    # Quality Settings
    AUDIO_QUALITY = os.environ.get("AUDIO_QUALITY", "320")  # kbps
    VIDEO_QUALITY = os.environ.get("VIDEO_QUALITY", "720")  # p
    
    @staticmethod
    def create_dirs():
        """Create necessary directories"""
        os.makedirs(Config.DOWNLOAD_DIR, exist_ok=True)
        os.makedirs("logs", exist_ok=True)
        os.makedirs("temp", exist_ok=True)
