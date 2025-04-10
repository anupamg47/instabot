import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import asyncio
from datetime import datetime

# Dictionary to store tracking requests
tracking_requests = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to Flipkart Price Tracker Bot!\n"
        "Send me a Flipkart product link and your target price like this:\n"
        "/track https://www.flipkart.com/product-example 20000"
    )

async def track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.message.chat_id
        if len(context.args) < 2:
            await update.message.reply_text("Usage: /track <product_url> <target_price>")
            return
            
        url = context.args[0]
        target_price = float(context.args[1])
        
        if "flipkart.com" not in url:
            await update.message.reply_text("Please provide a valid Flipkart product URL")
            return
        
        tracking_requests[chat_id] = {
            'url': url,
            'target_price': target_price,
            'active': True
        }
        
        await update.message.reply_text(f"Started tracking product at {url} for price ₹{target_price}")
        
        # Start tracking in background
        asyncio.create_task(track_price(chat_id, url, target_price, context.bot))
        
    except ValueError:
        await update.message.reply_text("Please enter a valid target price (numbers only)")

async def track_price(chat_id: int, url: str, target_price: float, bot):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    while tracking_requests.get(chat_id, {}).get('active', False):
        try:
            page = requests.get(url, headers=headers, timeout=10)
            page.raise_for_status()
            soup = BeautifulSoup(page.content, 'html.parser')
            
            # Update these selectors based on current Flipkart page
            price_element = soup.find("div", {"class": "_30jeq3 _16Jk6d"})
            if not price_element:
                await bot.send_message(
                    chat_id=chat_id,
                    text="Could not find price information. The product page structure might have changed."
                )
                break
                
            price = float(price_element.text.replace('₹', '').replace(',', ''))
            product_name = soup.find("span", {"class": "B_NuCI"}).text.strip()
            
            if price <= target_price:
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"🎉 Price Alert! 🎉\n\n{product_name}\n\nPrice dropped to ₹{price} (Your target: ₹{target_price})\n\n{url}"
                )
                break
                
            # Check every 6 hours (with more frequent active checks)
            for _ in range(6 * 60):  # 6 hours with 1-minute checks
                if not tracking_requests.get(chat_id, {}).get('active', False):
                    return
                await asyncio.sleep(60)
                
        except requests.RequestException as e:
            await bot.send_message(
                chat_id=chat_id,
                text=f"Error accessing product page: {str(e)}. Will retry in 1 hour."
            )
            await asyncio.sleep(3600)
        except Exception as e:
            await bot.send_message(
                chat_id=chat_id,
                text=f"Unexpected error: {str(e)}. Stopping tracking."
            )
            break

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id in tracking_requests:
        tracking_requests[chat_id]['active'] = False
        await update.message.reply_text("Stopped tracking your product")
    else:
        await update.message.reply_text("No active tracking for your account")

def main():
    # Replace with your Telegram bot token
    TOKEN = "7860591814:AAFThxv4ynKNCqBA_KhZuHzxmyDEPM1j1q4"
    
    # Create the Application
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("track", track))
    application.add_handler(CommandHandler("stop", stop))
    
    # Run the bot
    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()