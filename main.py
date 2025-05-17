import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import discord
import asyncio
import threading
import logging
from dotenv import load_dotenv
from datetime import datetime


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
from utils.language_utils import get_language_name
from bot import TranslatorBot

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Import and initialize database models
from models import db, User, Server, Channel, TranslationLog, BotSetting, APIKey
db.init_app(app)

# Initialize database and settings
def initialize_database():
    """Initialize database tables and basic settings"""
    try:
        db.create_all()
        
        # Initialize settings
        if not BotSetting.query.filter_by(key='default_language').first():
            db.session.execute(db.insert(BotSetting).values(
                key='default_language',
                value='en'
            ))
        
        # Add bot token if available
        discord_token = os.environ.get("DISCORD_BOT_TOKEN", "")
        if discord_token and not BotSetting.query.filter_by(key='discord_bot_token').first():
            db.session.execute(db.insert(BotSetting).values(
                key='discord_bot_token',
                value=discord_token
            ))
        
        # Add API keys from environment if they exist
        google_key = os.environ.get("GOOGLE_TRANSLATE_API_KEY", "")
        if google_key and not APIKey.query.filter_by(service='google').first():
            db.session.execute(db.insert(APIKey).values(
                service='google',
                key=google_key,
                is_active=True
            ))
        
        libre_key = os.environ.get("LIBRETRANSLATE_API_KEY", "")
        if libre_key and not APIKey.query.filter_by(service='libre').first():
            db.session.execute(db.insert(APIKey).values(
                service='libre',
                key=libre_key,
                is_active=True
            ))
        
        db.session.commit()
        logger.info("Database initialized successfully")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error initializing database: {e}")

# Create database tables
with app.app_context():
    initialize_database()

# Global variables
bot_instance = None
bot_thread = None
status_lock = threading.Lock()
bot_status = {
    "running": False,
    "connected_servers": 0,
    "error": None,
    "last_update": datetime.now().timestamp()
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

                # Log servers in database
                with app.app_context():  # <-- ✅ Add this line
                    for guild in bot_instance.guilds:
                        # Check if server exists in database
                        server = Server.query.filter_by(discord_id=str(guild.id)).first()
                        if not server:
                            # Add server to database
                            new_server = Server(
                                discord_id=str(guild.id),
                                name=guild.name,
                                auto_translate_enabled=False
                            )
                            db.session.add(new_server)

                    # Commit all server changes
                    try:
                        db.session.commit()
                    except Exception as e:
                        db.session.rollback()
                        logger.error(f"Error saving servers to database: {e}")
            
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
    # Get settings from database
    token_setting = BotSetting.query.filter_by(key='discord_bot_token').first()
    
    # Get API keys from database
    google_api_key = APIKey.query.filter_by(service='google').first()
    libre_api_key = APIKey.query.filter_by(service='libre').first()
    
    # Check if settings are set
    token_set = bool(token_setting and token_setting.value)
    google_api_key_set = bool(google_api_key and google_api_key.key)
    libre_api_key_set = bool(libre_api_key and libre_api_key.key)
    
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
    
    # Get stats from database if available
    stats = {
        "total_servers": Server.query.count(),
        "total_users": User.query.count(),
        "total_translations": TranslationLog.query.count(),
        "recent_translations": TranslationLog.query.order_by(TranslationLog.timestamp.desc()).limit(5).all()
    }
    
    return render_template(
        'index.html',
        bot_status=bot_status,
        token_set=token_set,
        google_api_key_set=google_api_key_set,
        libre_api_key_set=libre_api_key_set,
        languages=languages,
        config=CONFIG,
        stats=stats
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
    global bot_status, bot_instance, status_lock
    
    try:
        # Use lock to prevent race conditions
        with status_lock:
            # Update status if bot instance exists
            if bot_instance and not bot_instance.is_closed():
                bot_status["running"] = True
                bot_status["connected_servers"] = len(bot_instance.guilds) if bot_instance.guilds else 0
                bot_status["last_update"] = datetime.now().timestamp()
            elif bot_status["running"]:
                # Bot was running but isn't responding
                bot_status["running"] = False
                bot_status["error"] = "Bot connection lost"
                
            # Create a safe copy
            status_copy = bot_status.copy()
            
        return jsonify(status_copy)
    except Exception as e:
        logger.error(f"Error getting bot status: {e}")
        return jsonify({
            "running": False, 
            "connected_servers": 0, 
            "error": str(e),
            "last_update": datetime.now().timestamp()
        })

@app.route('/help')
def help_page():
    """Show help information"""
    return render_template('help.html')

@app.route('/bot_setup')
def bot_setup():
    """Show bot setup guide"""
    return render_template('bot_setup.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
