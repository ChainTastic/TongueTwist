import os
import json
import aiofiles
import logging
from typing import Dict, List, Any, Optional, Union

logger = logging.getLogger('discord')

class Database:
    """Simple JSON file-based database for storing user preferences"""
    
    def __init__(self, filename="user_preferences.json"):
        self.filename = filename
        self.data = {'users': {}, 'guilds': {}, 'messages': {}}
        # Initialize the data synchronously to avoid coroutine warning
        self._load_sync()
    
    def _load_sync(self):
        """Load data from file synchronously"""
        try:
            if os.path.exists(self.filename):
                with open(self.filename, 'r') as f:
                    content = f.read()
                    if content.strip():  # Check if file is not empty
                        self.data = json.loads(content)
                    else:
                        # File exists but is empty, initialize with default data
                        logger.info(f"Database file {self.filename} is empty, initializing with defaults")
                        with open(self.filename, 'w') as f:
                            f.write(json.dumps(self.data, indent=2))
                logger.info(f"Database loaded from {self.filename}")
            else:
                logger.info(f"No database file found, creating new one at {self.filename}")
                # Create the file synchronously
                with open(self.filename, 'w') as f:
                    f.write(json.dumps(self.data, indent=2))
                logger.info(f"Database saved to {self.filename}")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in database file, recreating with defaults")
            with open(self.filename, 'w') as f:
                f.write(json.dumps(self.data, indent=2))
        except Exception as e:
            logger.error(f"Error loading database: {e}")
            # Ensure database file exists with valid JSON
            with open(self.filename, 'w') as f:
                f.write(json.dumps(self.data, indent=2))
            
    async def _load(self):
        """Load data from file asynchronously"""
        try:
            if os.path.exists(self.filename):
                async with aiofiles.open(self.filename, 'r') as f:
                    content = await f.read()
                    if content.strip():  # Check if file is not empty
                        self.data = json.loads(content)
                    else:
                        # File exists but is empty, initialize with default data
                        logger.info(f"Database file {self.filename} is empty, initializing with defaults")
                        await self._save()
                logger.info(f"Database loaded from {self.filename}")
            else:
                logger.info(f"No database file found, creating new one at {self.filename}")
                await self._save()
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in database file, recreating with defaults")
            await self._save()
        except Exception as e:
            logger.error(f"Error loading database: {e}")
            # Ensure database file exists with valid JSON
            await self._save()
    
    async def _save(self):
        """Save data to file"""
        try:
            async with aiofiles.open(self.filename, 'w') as f:
                await f.write(json.dumps(self.data, indent=2))
            logger.info(f"Database saved to {self.filename}")
        except Exception as e:
            logger.error(f"Error saving database: {e}")
    
    async def get_user_language(self, user_id: Union[int, str]) -> str:
        """Get the preferred language for a user"""
        user_id_str = str(user_id)  # Convert to string for JSON compatibility
        return self.data['users'].get(user_id_str, {}).get('language', 'en')
    
    async def set_user_language(self, user_id: Union[int, str], language: str) -> None:
        """Set the preferred language for a user"""
        user_id_str = str(user_id)  # Convert to string for JSON compatibility
        if user_id_str not in self.data['users']:
            self.data['users'][user_id_str] = {}
        self.data['users'][user_id_str]['language'] = language
        await self._save()
    
    async def get_guild_auto_translate(self, guild_id: Union[int, str]) -> bool:
        """Check if auto-translate is enabled for a guild"""
        guild_id_str = str(guild_id)  # Convert to string for JSON compatibility
        return self.data['guilds'].get(guild_id_str, {}).get('auto_translate', False)
    
    async def set_guild_auto_translate(self, guild_id: Union[int, str], enabled: bool) -> None:
        """Enable or disable auto-translate for a guild"""
        guild_id_str = str(guild_id)  # Convert to string for JSON compatibility
        if guild_id_str not in self.data['guilds']:
            self.data['guilds'][guild_id_str] = {}
        self.data['guilds'][guild_id_str]['auto_translate'] = enabled
        await self._save()
    
    async def get_guild_channels_auto_translate(self, guild_id: Union[int, str]) -> List[str]:
        """Get channels with auto-translate enabled for a guild"""
        guild_id_str = str(guild_id)  # Convert to string for JSON compatibility
        return self.data['guilds'].get(guild_id_str, {}).get('auto_translate_channels', [])
    
    async def add_guild_channel_auto_translate(self, guild_id: Union[int, str], channel_id: Union[int, str]) -> None:
        """Add a channel to auto-translate list for a guild"""
        guild_id_str = str(guild_id)  # Convert to string for JSON compatibility
        channel_id_str = str(channel_id)  # Convert to string for JSON compatibility
        if guild_id_str not in self.data['guilds']:
            self.data['guilds'][guild_id_str] = {}
        if 'auto_translate_channels' not in self.data['guilds'][guild_id_str]:
            self.data['guilds'][guild_id_str]['auto_translate_channels'] = []
        if channel_id_str not in self.data['guilds'][guild_id_str]['auto_translate_channels']:
            self.data['guilds'][guild_id_str]['auto_translate_channels'].append(channel_id_str)
            await self._save()
    
    async def remove_guild_channel_auto_translate(self, guild_id: Union[int, str], channel_id: Union[int, str]) -> None:
        """Remove a channel from auto-translate list for a guild"""
        guild_id_str = str(guild_id)  # Convert to string for JSON compatibility
        channel_id_str = str(channel_id)  # Convert to string for JSON compatibility
        if guild_id_str in self.data['guilds'] and 'auto_translate_channels' in self.data['guilds'][guild_id_str]:
            if channel_id_str in self.data['guilds'][guild_id_str]['auto_translate_channels']:
                self.data['guilds'][guild_id_str]['auto_translate_channels'].remove(channel_id_str)
                await self._save()
    
    async def get_message_translations(self, message_id: Union[int, str]) -> Dict[str, str]:
        """Get translations for a message"""
        message_id_str = str(message_id)  # Convert to string for JSON compatibility
        return self.data.get('messages', {}).get(message_id_str, {}).get('translations', {})
    
    async def add_message_translation(self, message_id: Union[int, str], language: str, translation: str) -> None:
        """Add a translation for a message"""
        message_id_str = str(message_id)  # Convert to string for JSON compatibility
        if 'messages' not in self.data:
            self.data['messages'] = {}
        if message_id_str not in self.data['messages']:
            self.data['messages'][message_id_str] = {'translations': {}}
        self.data['messages'][message_id_str]['translations'][language] = translation
        await self._save()

# Create database instance
db = Database()
