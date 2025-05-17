import os
import asyncio
import logging
import discord
from discord.ext import commands
from discord import app_commands

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('discord')

# Import config
from config import CONFIG

# Create bot instance with all intents
intents = discord.Intents.default()
intents.message_content = True  # Privileged intent
intents.reactions = True
intents.members = True  # Privileged intent
intents.guilds = True
# Note: You must enable these intents in the Discord Developer Portal at
# https://discord.com/developers/applications/YOUR_APP_ID/bot

class TranslatorBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=CONFIG['prefix'],
            intents=intents,
            help_command=None,
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name=f"{CONFIG['prefix']}help | /translate"
            )
        )
        self.initial_extensions = [
            'cogs.auto_translate',
            'cogs.reaction_translate',
            'cogs.slash_commands'
        ]
        
    async def setup_hook(self):
        """Setup hook is called when the bot is first starting up"""
        for extension in self.initial_extensions:
            try:
                await self.load_extension(extension)
                logger.info(f"Loaded extension {extension}")
            except Exception as e:
                logger.error(f"Failed to load extension {extension}: {e}")
        
        # Sync slash commands
        logger.info("Syncing slash commands...")
        try:
            # Sync commands with Discord
            await self.tree.sync()
            logger.info("Slash commands synced successfully!")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
            
    async def on_ready(self):
        """Called when the bot is ready"""
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        logger.info(f'Connected to {len(self.guilds)} guilds')
        logger.info(f'Bot is ready to translate!')

async def main():
    # Create the bot instance
    bot = TranslatorBot()
    
    # Run the bot with the token
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        logger.error("No Discord bot token found. Please set the DISCORD_BOT_TOKEN environment variable.")
        logger.info("Checking for token in .env file...")
        try:
            from dotenv import load_dotenv
            # Try to reload in case it was updated
            load_dotenv(override=True)
            token = os.getenv("DISCORD_BOT_TOKEN")
            if token:
                logger.info("Found Discord bot token in .env file")
            else:
                logger.error("No Discord bot token found in .env file either.")
                return
        except Exception as e:
            logger.error(f"Error loading from .env: {e}")
            return
    
    try:
        logger.info("Starting bot...")
        await bot.start(token)
    except discord.errors.LoginFailure:
        logger.error("Invalid Discord bot token. Please check your token and try again.")
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
    finally:
        if not bot.is_closed():
            await bot.close()

if __name__ == "__main__":
    asyncio.run(main())
