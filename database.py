import os
import json
import aiofiles
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger('discord')

class Database:
    """Simple JSON file-based database for storing user preferences"""
    
    def __init__(self, filename="user_preferences.json"):
        self.filename = filename
        self.data = {'users': {}, 'guilds': {}}
        # Initialize the data synchronously to avoid coroutine warning
        self._load_sync()
    
    def _load_sync(self):
        """Load data from file synchronously"""
        try:
            if os.path.exists(self.filename):
                with open(self.filename, 'r') as f:
                    content = f.read()
                    self.data = json.loads(content)
                logger.info(f"Database loaded from {self.filename}")
            else:
                logger.info(f"No database file found, creating new one at {self.filename}")
                # Create the file synchronously
                with open(self.filename, 'w') as f:
                    f.write(json.dumps(self.data, indent=2))
                logger.info(f"Database saved to {self.filename}")
        except Exception as e:
            logger.error(f"Error loading database: {e}")
            
    async def _load(self):
        """Load data from file asynchronously"""
        try:
            if os.path.exists(self.filename):
                async with aiofiles.open(self.filename, 'r') as f:
                    content = await f.read()
                    self.data = json.loads(content)
                logger.info(f"Database loaded from {self.filename}")
            else:
                logger.info(f"No database file found, creating new one at {self.filename}")
                await self._save()
        except Exception as e:
            logger.error(f"Error loading database: {e}")
    
    async def _save(self):
        """Save data to file"""
        try:
            async with aiofiles.open(self.filename, 'w') as f:
                await f.write(json.dumps(self.data, indent=2))
            logger.info(f"Database saved to {self.filename}")
        except Exception as e:
            logger.error(f"Error saving database: {e}")
    
    async def get_user_language(self, user_id: int) -> str:
        """Get the preferred language for a user"""
        user_id = str(user_id)  # Convert to string for JSON compatibility
        return self.data['users'].get(user_id, {}).get('language', 'en')
    
    async def set_user_language(self, user_id: int, language: str) -> None:
        """Set the preferred language for a user"""
        user_id = str(user_id)  # Convert to string for JSON compatibility
        if user_id not in self.data['users']:
            self.data['users'][user_id] = {}
        self.data['users'][user_id]['language'] = language
        await self._save()
    
    async def get_guild_auto_translate(self, guild_id: int) -> bool:
        """Check if auto-translate is enabled for a guild"""
        guild_id = str(guild_id)  # Convert to string for JSON compatibility
        return self.data['guilds'].get(guild_id, {}).get('auto_translate', False)
    
    async def set_guild_auto_translate(self, guild_id: int, enabled: bool) -> None:
        """Enable or disable auto-translate for a guild"""
        guild_id = str(guild_id)  # Convert to string for JSON compatibility
        if guild_id not in self.data['guilds']:
            self.data['guilds'][guild_id] = {}
        self.data['guilds'][guild_id]['auto_translate'] = enabled
        await self._save()
    
    async def get_guild_channels_auto_translate(self, guild_id: int) -> List[int]:
        """Get channels with auto-translate enabled for a guild"""
        guild_id = str(guild_id)  # Convert to string for JSON compatibility
        return self.data['guilds'].get(guild_id, {}).get('auto_translate_channels', [])
    
    async def add_guild_channel_auto_translate(self, guild_id: int, channel_id: int) -> None:
        """Add a channel to auto-translate list for a guild"""
        guild_id = str(guild_id)  # Convert to string for JSON compatibility
        channel_id = str(channel_id)  # Convert to string for JSON compatibility
        if guild_id not in self.data['guilds']:
            self.data['guilds'][guild_id] = {}
        if 'auto_translate_channels' not in self.data['guilds'][guild_id]:
            self.data['guilds'][guild_id]['auto_translate_channels'] = []
        if channel_id not in self.data['guilds'][guild_id]['auto_translate_channels']:
            self.data['guilds'][guild_id]['auto_translate_channels'].append(channel_id)
            await self._save()
    
    async def remove_guild_channel_auto_translate(self, guild_id: int, channel_id: int) -> None:
        """Remove a channel from auto-translate list for a guild"""
        guild_id = str(guild_id)  # Convert to string for JSON compatibility
        channel_id = str(channel_id)  # Convert to string for JSON compatibility
        if guild_id in self.data['guilds'] and 'auto_translate_channels' in self.data['guilds'][guild_id]:
            if channel_id in self.data['guilds'][guild_id]['auto_translate_channels']:
                self.data['guilds'][guild_id]['auto_translate_channels'].remove(channel_id)
                await self._save()
    
    async def get_message_translations(self, message_id: int) -> Dict[str, str]:
        """Get translations for a message"""
        message_id = str(message_id)  # Convert to string for JSON compatibility
        return self.data.get('messages', {}).get(message_id, {}).get('translations', {})
    
    async def add_message_translation(self, message_id: int, language: str, translation: str) -> None:
        """Add a translation for a message"""
        message_id = str(message_id)  # Convert to string for JSON compatibility
        if 'messages' not in self.data:
            self.data['messages'] = {}
        if message_id not in self.data['messages']:
            self.data['messages'][message_id] = {'translations': {}}
        self.data['messages'][message_id]['translations'][language] = translation
        await self._save()

# Create database instance
db = Database()
