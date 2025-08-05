import os
import asyncio
import yt_dlp
from typing import Dict, List, Optional, Tuple
import re
import logging
from config import Config

logger = logging.getLogger(__name__)

class YouTubeDownloader:
    def __init__(self):
        self.downloading = {}
        self.download_semaphore = asyncio.Semaphore(Config.MAX_CONCURRENT_DOWNLOADS)
        
    def get_ydl_opts(self, format_type: str = "audio", quality: str = "best"):
        """Get yt-dlp options"""
        base_opts = {
            'outtmpl': f'{Config.DOWNLOAD_DIR}/%(title)s.%(ext)s',
            'writeinfojson': False,
            'writedescription': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'ignoreerrors': True,
            'no_warnings': True,
            'extractaudio': format_type == "audio",
            'audioformat': 'mp3' if format_type == "audio" else None,
            'audioquality': Config.AUDIO_QUALITY if format_type == "audio" else None,
            'format': self.get_format_selector(format_type, quality),
            'noplaylist': True,
        }
        
        if format_type == "audio":
            base_opts.update({
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': Config.AUDIO_QUALITY,
                }]
            })
        
        return base_opts
    
    def get_format_selector(self, format_type: str, quality: str) -> str:
        """Get format selector for yt-dlp"""
        if format_type == "audio":
            return "bestaudio/best"
        elif format_type == "video":
            if quality == "720":
                return "best[height<=720]/best"
            elif quality == "480":
                return "best[height<=480]/best"
            elif quality == "360":
                return "best[height<=360]/best"
            else:
                return "best"
        return "best"
    
    async def search_youtube(self, query: str, limit: int = 10) -> List[Dict]:
        """Search YouTube for videos"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'default_search': 'ytsearch10:',
            }
            
            loop = asyncio.get_event_loop()
            
            def search():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(query, download=False)
            
            info = await loop.run_in_executor(None, search)
            
            results = []
            if 'entries' in info:
                for entry in info['entries'][:limit]:
                    if entry:
                        results.append({
                            'id': entry.get('id'),
                            'title': entry.get('title', 'Unknown'),
                            'url': f"https://youtube.com/watch?v={entry.get('id')}",
                            'duration': self.format_duration(entry.get('duration', 0)),
                            'thumbnail': entry.get('thumbnail'),
                            'uploader': entry.get('uploader', 'Unknown')
                        })
            
            return results
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []
    
    async def get_video_info(self, url: str) -> Optional[Dict]:
        """Get video information"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
            }
            
            loop = asyncio.get_event_loop()
            
            def get_info():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(url, download=False)
            
            info = await loop.run_in_executor(None, get_info)
            
            if not info:
                return None
            
            return {
                'id': info.get('id'),
                'title': info.get('title', 'Unknown'),
                'url': info.get('webpage_url', url),
                'duration': self.format_duration(info.get('duration', 0)),
                'thumbnail': info.get('thumbnail'),
                'uploader': info.get('uploader', 'Unknown'),
                'view_count': info.get('view_count', 0),
                'like_count': info.get('like_count', 0),
                'upload_date': info.get('upload_date'),
                'description': info.get('description', '')[:500] + '...' if info.get('description') else ''
            }
            
        except Exception as e:
            logger.error(f"Info extraction error: {e}")
            return None
    
    async def download(self, url: str, format_type: str = "audio", quality: str = "best", 
                      progress_callback=None) -> Optional[Tuple[str, Dict]]:
        """Download video/audio"""
        async with self.download_semaphore:
            try:
                video_id = self.extract_video_id(url)
                if not video_id:
                    return None
                
                # Check if already downloading
                if video_id in self.downloading:
                    return None
                
                self.downloading[video_id] = True
                
                ydl_opts = self.get_ydl_opts(format_type, quality)
                
                # Add progress hook
                if progress_callback:
                    ydl_opts['progress_hooks'] = [progress_callback]
                
                loop = asyncio.get_event_loop()
                
                def download_func():
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                        return info
                
                info = await loop.run_in_executor(None, download_func)
                
                if not info:
                    return None
                
                # Find downloaded file
                title = info.get('title', 'Unknown')
                ext = 'mp3' if format_type == "audio" else info.get('ext', 'mp4')
                file_path = os.path.join(Config.DOWNLOAD_DIR, f"{title}.{ext}")
                
                # Handle filename conflicts
                if not os.path.exists(file_path):
                    # Try to find the actual file
                    for file in os.listdir(Config.DOWNLOAD_DIR):
                        if video_id in file or title[:50] in file:
                            file_path = os.path.join(Config.DOWNLOAD_DIR, file)
                            break
                
                video_info = {
                    'id': info.get('id'),
                    'title': title,
                    'duration': self.format_duration(info.get('duration', 0)),
                    'thumbnail': info.get('thumbnail'),
                    'uploader': info.get('uploader', 'Unknown'),
                    'url': info.get('webpage_url', url),
                    'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0
                }
                
                return file_path, video_info
                
            except Exception as e:
                logger.error(f"Download error for {url}: {e}")
                return None
            finally:
                self.downloading.pop(video_id, None)
    
    async def download_playlist(self, url: str, format_type: str = "audio", 
                               limit: int = None) -> List[Tuple[str, Dict]]:
        """Download playlist"""
        try:
            ydl_opts = {
                'quiet': True,
                'extract_flat': True,
                'playlistend': limit or Config.MAX_PLAYLIST_SIZE
            }
            
            loop = asyncio.get_event_loop()
            
            def get_playlist():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(url, download=False)
            
            playlist_info = await loop.run_in_executor(None, get_playlist)
            
            if not playlist_info or 'entries' not in playlist_info:
                return []
            
            results = []
            for entry in playlist_info['entries']:
                if entry and entry.get('id'):
                    video_url = f"https://youtube.com/watch?v={entry['id']}"
                    result = await self.download(video_url, format_type)
                    if result:
                        results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Playlist download error: {e}")
            return []
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL"""
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([^&\n?#]+)',
            r'youtube\.com/watch\?.*v=([^&\n?#]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # If it's already a video ID
        if re.match(r'^[a-zA-Z0-9_-]{11}, url):
            return url
        
        return None
    
    def format_duration(self, seconds: int) -> str:
        """Format duration in seconds to MM:SS or HH:MM:SS"""
        if not seconds:
            return "00:00"
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    
    async def get_stream_url(self, url: str, format_type: str = "audio") -> Optional[str]:
        """Get direct stream URL without downloading"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'format': self.get_format_selector(format_type, "best")
            }
            
            loop = asyncio.get_event_loop()
            
            def get_url():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    return info.get('url') if info else None
            
            stream_url = await loop.run_in_executor(None, get_url)
            return stream_url
            
        except Exception as e:
            logger.error(f"Stream URL error: {e}")
            return None
    
    def cleanup_downloads(self, max_age_hours: int = 24):
        """Clean up old downloaded files"""
        try:
            import time
            current_time = time.time()
            
            for filename in os.listdir(Config.DOWNLOAD_DIR):
                filepath = os.path.join(Config.DOWNLOAD_DIR, filename)
                if os.path.isfile(filepath):
                    file_age = current_time - os.path.getctime(filepath)
                    if file_age > (max_age_hours * 3600):
                        os.remove(filepath)
                        logger.info(f"Cleaned up old file: {filename}")
                        
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    def get_download_progress_text(self, d):
        """Format download progress"""
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', 'N/A')
            speed = d.get('_speed_str', 'N/A')
            eta = d.get('_eta_str', 'N/A')
            return f"📥 Downloading... {percent} | Speed: {speed} | ETA: {eta}"
        elif d['status'] == 'finished':
            return "✅ Download completed!"
        elif d['status'] == 'error':
            return "❌ Download failed!"
        else:
            return "📥 Processing..."
