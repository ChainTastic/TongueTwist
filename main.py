import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import discord
import asyncio
import threading
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('discord_bot_dashboard')

# Import bot modules
from config import CONFIG, LANGUAGES, LANGUAGE_TO_FLAG
from database import db
from utils.language_utils import get_language_name
from bot import TranslatorBot

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Global variables
bot_instance = None
bot_thread = None
bot_status = {
    "running": False,
    "connected_servers": 0,
    "error": None
}

def run_bot_forever(token):
    """Run the bot in a separate thread"""
    global bot_instance, bot_status
    
    async def start_bot():
        # Use global inside the async function
        global bot_instance
        try:
            # Create and start the bot
            bot_instance = TranslatorBot()
            bot_status["running"] = True
            bot_status["error"] = None
            
            # Update connected servers count when bot is ready
            @bot_instance.event
            async def on_ready():
                bot_status["connected_servers"] = len(bot_instance.guilds)
                logger.info(f'Bot connected to {len(bot_instance.guilds)} guilds')
            
            # Start the bot with token
            await bot_instance.start(token)
        except discord.errors.LoginFailure:
            bot_status["running"] = False
            bot_status["error"] = "Invalid Discord bot token. Please check your token and try again."
            logger.error("Invalid Discord bot token")
        except Exception as e:
            bot_status["running"] = False
            bot_status["error"] = f"Error starting bot: {str(e)}"
            logger.error(f"Error starting bot: {e}")
        finally:
            if bot_instance and not bot_instance.is_closed():
                await bot_instance.close()
            bot_status["running"] = False
    
    # Create a new event loop for the bot
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_bot())

def stop_bot():
    """Stop the bot if it's running"""
    global bot_instance, bot_thread, bot_status
    
    if bot_instance and not bot_instance.is_closed():
        asyncio.run_coroutine_threadsafe(bot_instance.close(), bot_instance.loop)
    
    if bot_thread and bot_thread.is_alive():
        bot_thread.join(timeout=5)
    
    bot_instance = None
    bot_thread = None
    bot_status["running"] = False
    bot_status["connected_servers"] = 0
    logger.info("Bot stopped")

@app.route('/')
def index():
    """Main dashboard page"""
    discord_token = os.environ.get("DISCORD_BOT_TOKEN", "")
    google_key = os.environ.get("GOOGLE_TRANSLATE_API_KEY", "")
    libre_key = os.environ.get("LIBRETRANSLATE_API_KEY", "")
    
    token_set = bool(discord_token)
    google_api_key_set = bool(google_key)
    libre_api_key_set = bool(libre_key)
    
    # Get available languages
    languages = []
    for lang_code in sorted(set(LANGUAGES.values())):
        flag = LANGUAGE_TO_FLAG.get(lang_code, "🌐")
        language_name = get_language_name(lang_code)
        languages.append({
            "code": lang_code,
            "flag": flag,
            "name": language_name
        })
    
    return render_template(
        'index.html',
        bot_status=bot_status,
        token_set=token_set,
        google_api_key_set=google_api_key_set,
        libre_api_key_set=libre_api_key_set,
        languages=languages,
        config=CONFIG
    )

@app.route('/start_bot', methods=['POST'])
def start_bot():
    """Start the Discord bot"""
    global bot_thread, bot_status
    
    # Check if bot is already running
    if bot_status["running"]:
        flash("Bot is already running!", "warning")
        return redirect(url_for('index'))
    
    # Get token from environment or form
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        token = request.form.get('token')
        if token:
            # Save to .env file
            with open('.env', 'a') as f:
                f.write(f"\nDISCORD_BOT_TOKEN={token}\n")
            os.environ["DISCORD_BOT_TOKEN"] = token
        else:
            flash("No Discord bot token provided!", "danger")
            return redirect(url_for('index'))
    
    # Start the bot in a separate thread
    bot_thread = threading.Thread(target=run_bot_forever, args=(token,))
    bot_thread.daemon = True
    bot_thread.start()
    
    flash("Bot starting...", "success")
    return redirect(url_for('index'))

@app.route('/stop_bot', methods=['POST'])
def stop_bot_route():
    """Stop the Discord bot"""
    global bot_status
    
    # Check if bot is running
    if not bot_status["running"]:
        flash("Bot is not running!", "warning")
        return redirect(url_for('index'))
    
    # Stop the bot
    stop_bot()
    
    flash("Bot stopped successfully!", "success")
    return redirect(url_for('index'))

@app.route('/set_api_keys', methods=['POST'])
def set_api_keys():
    """Set API keys for translation services"""
    google_key = request.form.get('google_key')
    libre_key = request.form.get('libre_key')
    libre_url = request.form.get('libre_url')
    
    # Update .env file
    env_content = []
    env_updated = False
    
    # Try to read existing .env file
    try:
        with open('.env', 'r') as f:
            env_content = f.readlines()
    except FileNotFoundError:
        # Create new .env file
        env_content = ["# Discord bot configuration\n"]
    
    # Update or add environment variables
    for i, line in enumerate(env_content):
        if google_key and line.startswith('GOOGLE_TRANSLATE_API_KEY='):
            env_content[i] = f"GOOGLE_TRANSLATE_API_KEY={google_key}\n"
            os.environ['GOOGLE_TRANSLATE_API_KEY'] = google_key
            env_updated = True
        
        if libre_key and line.startswith('LIBRETRANSLATE_API_KEY='):
            env_content[i] = f"LIBRETRANSLATE_API_KEY={libre_key}\n"
            os.environ['LIBRETRANSLATE_API_KEY'] = libre_key
            env_updated = True
        
        if libre_url and line.startswith('LIBRETRANSLATE_URL='):
            env_content[i] = f"LIBRETRANSLATE_URL={libre_url}\n"
            os.environ['LIBRETRANSLATE_URL'] = libre_url
            env_updated = True
    
    # Add keys if they weren't in the file
    if google_key and not any(line.startswith('GOOGLE_TRANSLATE_API_KEY=') for line in env_content):
        env_content.append(f"GOOGLE_TRANSLATE_API_KEY={google_key}\n")
        os.environ['GOOGLE_TRANSLATE_API_KEY'] = google_key
        env_updated = True
    
    if libre_key and not any(line.startswith('LIBRETRANSLATE_API_KEY=') for line in env_content):
        env_content.append(f"LIBRETRANSLATE_API_KEY={libre_key}\n")
        os.environ['LIBRETRANSLATE_API_KEY'] = libre_key
        env_updated = True
    
    if libre_url and not any(line.startswith('LIBRETRANSLATE_URL=') for line in env_content):
        env_content.append(f"LIBRETRANSLATE_URL={libre_url}\n")
        os.environ['LIBRETRANSLATE_URL'] = libre_url
        env_updated = True
    
    # Write updated content back to .env file
    if env_updated:
        with open('.env', 'w') as f:
            f.writelines(env_content)
        flash("API keys updated successfully!", "success")
    else:
        flash("No changes were made to API keys.", "info")
    
    return redirect(url_for('index'))

@app.route('/bot_status')
def get_bot_status():
    """Get current bot status as JSON"""
    return jsonify(bot_status)

@app.route('/help')
def help_page():
    """Show help information"""
    return render_template('help.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)