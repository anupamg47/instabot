import instaloader
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters
)
import os
import requests
import logging
import time
import random
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# States for conversation handler
ASK_USERNAME, = range(1)

class InstagramHelper:
    def __init__(self):
        self.L = instaloader.Instaloader()
        self.L.context.sleep = True
        self.L.context.max_connection_attempts = 2
        self.last_request = datetime.now() - timedelta(minutes=5)
        
        # Try to load session if credentials exist
        if os.getenv('IG_USERNAME') and os.getenv('IG_PASSWORD'):
            try:
                self.L.login(os.getenv('IG_USERNAME'), os.getenv('IG_PASSWORD'))
                logger.info("Logged in to Instagram")
            except Exception as e:
                logger.warning(f"Instagram login failed: {e}")

    def get_profile(self, username):
        try:
            # Rate limiting
            now = datetime.now()
            if (now - self.last_request).seconds < random.uniform(5, 15):
                wait_time = random.uniform(5, 15) - (now - self.last_request).seconds
                if wait_time > 0:
                    time.sleep(wait_time)
            
            self.last_request = datetime.now()
            return instaloader.Profile.from_username(self.L.context, username)
        except Exception as e:
            logger.error(f"Instagram error: {e}")
            raise

instagram = InstagramHelper()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message"""
    await update.message.reply_text(
        "👋 Hi! I can fetch public Instagram profile pictures.\n\n"
        "⚠️ Note: Private profiles cannot be accessed.\n\n"
        "Send /instagram to get started!"
    )

async def start_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start Instagram profile picture conversation"""
    await update.message.reply_text(
        "📸 Please send me a public Instagram username (without @):"
    )
    return ASK_USERNAME

async def get_instagram_pic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Fetch and send Instagram profile picture"""
    username = update.message.text.strip().lower()
    
    try:
        await update.message.reply_text(f"🔍 Searching for @{username}...")
        
        profile = instagram.get_profile(username)
        
        if profile.is_private:
            await update.message.reply_text(
                "🔒 This profile is private. I can't access private profiles.\n\n"
                "If this is your account, you can:\n"
                "1. Temporarily make it public\n"
                "2. Upload the photo manually"
            )
            return ConversationHandler.END
        
        pic_url = profile.profile_pic_url
        await update.message.reply_text("📥 Downloading profile picture...")
        
        # Add headers to mimic browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(pic_url, headers=headers, stream=True, timeout=15)
        response.raise_for_status()
        
        temp_file = f"temp_{username}.jpg"
        with open(temp_file, 'wb') as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        
        with open(temp_file, 'rb') as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=f"📸 Profile picture of @{username}"
            )
        
        os.remove(temp_file)
        
    except instaloader.exceptions.ProfileNotExistsException:
        await update.message.reply_text("❌ This username doesn't exist. Please check the spelling.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        await update.message.reply_text("⚠️ Instagram is limiting requests. Please try again in a few minutes.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        await update.message.reply_text("❌ An unexpected error occurred. Please try again later.")
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the current operation"""
    await update.message.reply_text("🚫 Operation cancelled.")
    return ConversationHandler.END

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors and send user notification"""
    logger.error("Exception while handling an update:", exc_info=context.error)
    if update and hasattr(update, 'message'):
        await update.message.reply_text("❌ An error occurred. Please try again later.")

def main() -> None:
    """Run the bot."""
    BOT_TOKEN = "7622416649:AAGThevZBBmwDJPHIFrGdeUoqPJjJQvQ3nY"
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_error_handler(error_handler)
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('instagram', start_instagram)],
        states={
            ASK_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_instagram_pic)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    
    logger.info("Starting bot...")
    application.run_polling()

if __name__ == '__main__':
    main()