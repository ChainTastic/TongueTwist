import discord
from typing import Optional
import logging

from config import CONFIG, LANGUAGE_TO_FLAG
from utils.language_utils import get_language_name

logger = logging.getLogger('discord')

async def send_translated_message(
    channel: discord.TextChannel,
    original_message: discord.Message,
    translated_text: str,
    target_lang: str,
    requester: Optional[discord.User] = None
) -> Optional[discord.Message]:
    """Send a translated version of a message"""
    try:
        # Get the flag emoji for the target language
        flag = LANGUAGE_TO_FLAG.get(target_lang, "🌐")
        
        # Prepare the embed
        embed = discord.Embed(
            description=translated_text,
            color=discord.Color(CONFIG['embed_color'])
        )
        
        # Add timestamp from original message
        embed.timestamp = original_message.created_at
        
        # Add author info from original message
        embed.set_author(
            name=original_message.author.display_name,
            icon_url=original_message.author.display_avatar.url
        )
        
        # Add footer with language and requester info
        footer_text = f"Translated to {get_language_name(target_lang)}"
        if requester:
            footer_text += f" • Requested by {requester.display_name}"
        embed.set_footer(text=footer_text)
        
        # Send the message, replying to the original
        return await channel.send(
            content=f"{flag} **Translation:**",
            embed=embed,
            reference=original_message,
            mention_author=False
        )
    except Exception as e:
        logger.error(f"Error sending translated message: {e}")
        return None
