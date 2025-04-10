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

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# States for conversation handler
ASK_USERNAME, = range(1)

# Your Telegram Bot Token (replace with your actual token)
BOT_TOKEN = "7622416649:AAGThevZBBmwDJPHIFrGdeUoqPJjJQvQ3nY"  # ⚠️ Remove before sharing code!

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
        # Initialize Instaloader
        L = instaloader.Instaloader()
        L.context.sleep = True  # Be gentle with requests
        
        await update.message.reply_text(f"🔍 Searching for @{username}...")
        profile = instaloader.Profile.from_username(L.context, username)
        
        if profile.is_private:
            await update.message.reply_text(
                "🔒 This profile is private. I can't access private profiles.\n\n"
                "If this is your account, you can:\n"
                "1. Temporarily make it public\n"
                "2. Upload the photo manually"
            )
            return ConversationHandler.END
        
        # Get and download profile picture
        pic_url = profile.profile_pic_url
        await update.message.reply_text("📥 Downloading profile picture...")
        
        response = requests.get(pic_url, stream=True, timeout=10)
        response.raise_for_status()  # Raise exception for bad status codes
        
        # Save temporarily and send
        temp_file = f"temp_{username}.jpg"
        with open(temp_file, 'wb') as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        
        with open(temp_file, 'rb') as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=f"📸 Profile picture of @{username}"
            )
        
        # Clean up
        os.remove(temp_file)
        
    except instaloader.exceptions.ProfileNotExistsException:
        await update.message.reply_text("❌ This username doesn't exist. Please check the spelling.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        await update.message.reply_text("⚠️ Couldn't download the image. Please try again later.")
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
    # Create Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add error handler first
    application.add_error_handler(error_handler)
    
    # Add conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('instagram', start_instagram)],
        states={
            ASK_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_instagram_pic)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    
    # Run the bot
    logger.info("Starting bot...")
    application.run_polling()

if __name__ == '__main__':
    main()