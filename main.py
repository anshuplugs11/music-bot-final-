#!/usr/bin/env python3
import asyncio
import os
import sys
import logging
from keep_alive import keep_alive
from config import Config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """Main function to run the bot"""
    try:
        # Start keep alive server
        keep_alive()
        
        # Create necessary directories
        Config.create_dirs()
        
        # Import and start the bot
        from bot import bot
        
        # Initialize music player
        await bot.music_player.initialize(bot.app)
        
        # Initialize broadcast manager
        await bot.broadcast_manager.initialize_assistant()
        
        # Start the bot
        await bot.start_bot()
        
        # Keep the bot running
        await bot.app.idle()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        try:
            await bot.db.disconnect()
            await bot.app.stop()
            if bot.broadcast_manager.assistant_client:
                await bot.broadcast_manager.assistant_client.stop()
        except:
            pass

if __name__ == "__main__":
    # Check for required environment variables
    required_vars = ["API_ID", "API_HASH", "BOT_TOKEN", "OWNER_ID"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
    
    # Run the bot
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        sys.exit(1)
