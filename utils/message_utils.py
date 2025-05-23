import discord
from typing import Optional
import logging

from config import CONFIG, LANGUAGE_TO_FLAG
from translation import translation_service
from utils.language_utils import get_language_name

logger = logging.getLogger('discord')

def language_code_to_flag(code: str) -> str:
    if not code or len(code) < 2:
        return "🌐"
    code = code[:2].upper()
    return chr(ord(code[0]) + 127397) + chr(ord(code[1]) + 127397)

async def send_translated_message(
    channel: discord.TextChannel,
    original_message: discord.Message,
    translated_text: str,
    source_lang: str,
    target_lang: str
):
    try:
        # Get language flags
        from config import LANGUAGE_TO_FLAG
        source_flag = language_code_to_flag(source_lang)
        target_flag = language_code_to_flag(target_lang)

        # Get webhooks (or create one if missing)
        webhooks = await channel.webhooks()
        webhook = discord.utils.get(webhooks, name="TongueTwist")
        if webhook is None:
            webhook = await channel.create_webhook(name="TongueTwist")

        # Username with translation label
        display_name = original_message.author.display_name
        username = f"{source_flag} → {target_flag} {original_message.author.display_name}"

        # Send message impersonating original user
        await webhook.send(
            content=f"{translated_text}\n\n[🔗 Jump to Original]({original_message.jump_url})",
            username=username,
            avatar_url=original_message.author.display_avatar.url
        )
    except Exception as e:
        logging.getLogger("discord").error(f"Webhook error: {e}")


#         channel: discord.TextChannel,
#         original_message: discord.Message,
#         translated_text: str,
#         target_lang: str,
#         requester: Optional[discord.User] = None
# ) -> Optional[discord.Message]:
#     """Send a translated version of a message as an embed"""
#     try:
#         # Detect source language
#         source_lang = await translation_service.detect_language(original_message.content)
#
#         # Get flags
#         source_flag = LANGUAGE_TO_FLAG.get(source_lang, source_lang.upper())
#         target_flag = LANGUAGE_TO_FLAG.get(target_lang, target_lang.upper())
#
#         # Language label: e.g., "fr → en"
#         lang_label = f"{source_flag} → {target_flag}"
#
#         # Build the embed
#         embed = discord.Embed(
#             description=translated_text,
#             color=discord.Color(CONFIG['embed_color']),
#             timestamp=original_message.created_at
#         )
#
#         # Set author (who originally said the message)
#         embed.set_author(
#             name=f"{original_message.author.display_name} ({lang_label})",
#             icon_url=original_message.author.display_avatar.url
#         )
#
#         # Footer: extra info
#         footer_text = f"Translated to {get_language_name(target_lang)}"
#         if requester:
#             footer_text += f" • Requested by {requester.display_name}"
#         embed.set_footer(text=footer_text)
#
#         # Send the message, referencing the original
#         return await channel.send(
#             content=f"{target_flag} **Translated Message:**",
#             embed=embed,
#             reference=original_message,
#             mention_author=False
#         )
#     except Exception as e:
#         logger.error(f"Error sending translated message: {e}")
#         return None
