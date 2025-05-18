import discord
from typing import Optional
import logging

from config import CONFIG, LANGUAGE_TO_FLAG
from translation import translation_service
from utils.language_utils import get_language_name

logger = logging.getLogger('discord')


async def send_translated_message(
        channel: discord.TextChannel,
        original_message: discord.Message,
        translated_text: str,
        target_lang: str,
        requester: Optional[discord.User] = None
) -> Optional[discord.Message]:
    """Send a translated version of a message as an embed"""
    try:
        # Detect source language
        source_lang = await translation_service.detect_language(original_message.content)

        # Get flags
        source_flag = LANGUAGE_TO_FLAG.get(source_lang, source_lang.upper())
        target_flag = LANGUAGE_TO_FLAG.get(target_lang, target_lang.upper())

        # Language label: e.g., "fr → en"
        lang_label = f"{source_flag} → {target_flag}"

        # Build the embed
        embed = discord.Embed(
            description=translated_text,
            color=discord.Color(CONFIG['embed_color']),
            timestamp=original_message.created_at
        )

        # Set author (who originally said the message)
        embed.set_author(
            name=f"{original_message.author.display_name} ({lang_label})",
            icon_url=original_message.author.display_avatar.url
        )

        # Footer: extra info
        footer_text = f"Translated to {get_language_name(target_lang)}"
        if requester:
            footer_text += f" • Requested by {requester.display_name}"
        embed.set_footer(text=footer_text)

        # Send the message, referencing the original
        return await channel.send(
            content=f"{target_flag} **Translated Message:**",
            embed=embed,
            reference=original_message,
            mention_author=False
        )
    except Exception as e:
        logger.error(f"Error sending translated message: {e}")
        return None
