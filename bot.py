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

# States for conversation handler
ASK_USERNAME, = range(1)

async def start_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the Instagram profile picture conversation"""
    await update.message.reply_text(
        "Please send me an Instagram username (without @):"
    )
    return ASK_USERNAME

async def get_instagram_pic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Fetch and send Instagram profile picture"""
    username = update.message.text.strip()
    
    try:
        # Create instaloader instance
        L = instaloader.Instaloader()
        
        # Try to load the profile
        await update.message.reply_text(f"🔍 Searching for @{username}...")
        profile = instaloader.Profile.from_username(L.context, username)
        
        if not profile.is_private:
            # Get the profile picture URL
            pic_url = profile.profile_pic_url
            
            # Download the image
            await update.message.reply_text("📥 Downloading profile picture...")
            response = requests.get(pic_url, stream=True)
            
            if response.status_code == 200:
                # Save temporarily
                temp_file = f"{username}_profile_pic.jpg"
                with open(temp_file, 'wb') as f:
                    f.write(response.content)
                
                # Send to user
                with open(temp_file, 'rb') as photo:
                    await update.message.reply_photo(
                        photo=photo,
                        caption=f"Profile picture of @{username}"
                    )
                
                # Clean up
                os.remove(temp_file)
            else:
                await update.message.reply_text("❌ Couldn't download the profile picture.")
        else:
            await update.message.reply_text("🔒 This profile is private. I can't access private profiles.")
    
    except instaloader.exceptions.ProfileNotExistsException:
        await update.message.reply_text("❌ This Instagram username doesn't exist.")
    except Exception as e:
        await update.message.reply_text(f"❌ An error occurred: {str(e)}")
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the conversation"""
    await update.message.reply_text('Okay, cancelled.')
    return ConversationHandler.END

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    await update.message.reply_text("Hi! Send /instagram to get started.")

def main() -> None:
    """Start the bot."""
    # Create the Application
    application = Application.builder().token("7622416649:AAEbUMQxHCZ1AnuNEjLkQozTPc73NBVTbSs").build()

    # Add conversation handler for Instagram feature
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('instagram', start_instagram)],
        states={
            ASK_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_instagram_pic)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    
    # Start the Bot
    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()