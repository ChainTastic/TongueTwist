import discord
from discord.ext import commands
import logging
import asyncio
from typing import Dict, Optional

from config import CONFIG, LANGUAGES, LANGUAGE_TO_FLAG
from database import db
from translation import translation_service
from utils.message_utils import send_translated_message
from utils.language_utils import get_language_name

logger = logging.getLogger('discord')

class ReactionTranslate(commands.Cog):
    """Handles translation triggered by flag emoji reactions"""
    
    def __init__(self, bot):
        self.bot = bot
        self.pending_translations = {}  # Store messages that are being processed for translation
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Listen for flag emoji reactions to translate messages"""
        # Don't process our own reactions
        if payload.user_id == self.bot.user.id:
            return
            
        # Check if the emoji is a flag emoji we support
        emoji = str(payload.emoji)
        if emoji not in LANGUAGES:
            return
            
        # Get the target language from the flag emoji
        target_lang = LANGUAGES[emoji]
        
        try:
            # Get the channel and message
            channel = self.bot.get_channel(payload.channel_id)
            if not channel:
                return
                
            message = await channel.fetch_message(payload.message_id)
            if not message:
                return
                
            # Don't translate empty messages or bot messages (except our own translations)
            if not message.content or (message.author.bot and not message.author.id == self.bot.user.id):
                return
                
            # Check if this is a message we already translated
            if message.author.id == self.bot.user.id and message.reference:
                # This is our own translation message, ignore
                return
                
            # Create a unique key for this translation request
            translation_key = f"{payload.message_id}:{target_lang}"
            
            # Check if we're already processing this translation
            if translation_key in self.pending_translations:
                return
                
            # Mark as pending
            self.pending_translations[translation_key] = True
            
            try:
                # Check if we already have this translation in the database
                translations = await db.get_message_translations(message.id)
                if translations and target_lang in translations:
                    translated_text = translations[target_lang]
                else:
                    # Detect source language
                    source_lang = await translation_service.detect_language(message.content)
                    
                    # No need to translate if the target language is the same as the source
                    if source_lang == target_lang:
                        del self.pending_translations[translation_key]
                        return
                        
                    # Translate the message
                    translated_text = await translation_service.translate(message.content, target_lang, source_lang)
                    
                    # Store the translation
                    await db.add_message_translation(message.id, target_lang, translated_text)
                
                # Get the user who requested the translation
                user = await self.bot.fetch_user(payload.user_id)
                
                # Send the translated message
                await send_translated_message(
                    channel=channel,
                    original_message=message,
                    translated_text=translated_text,
                    target_lang=target_lang,
                    requester=user
                )
            finally:
                # Remove from pending regardless of success/failure
                del self.pending_translations[translation_key]
                
        except Exception as e:
            # Make sure we remove from pending if there's an error
            translation_key = f"{payload.message_id}:{target_lang}"
            if translation_key in self.pending_translations:
                del self.pending_translations[translation_key]
            logger.error(f"Error in reaction translation: {e}")
    
    @commands.command(name="flags", aliases=["languages", "langs"])
    async def show_flags(self, ctx):
        """Shows a list of flag emojis and their corresponding languages"""
        flags_per_page = 10
        flags = list(LANGUAGES.items())
        pages = [flags[i:i + flags_per_page] for i in range(0, len(flags), flags_per_page)]
        
        current_page = 0
        
        # Create the initial embed
        embed = self._create_flags_embed(pages[current_page], current_page, len(pages))
        message = await ctx.send(embed=embed)
        
        # Only add reactions if there are multiple pages
        if len(pages) > 1:
            await message.add_reaction("◀️")
            await message.add_reaction("▶️")
            
            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ["◀️", "▶️"] and reaction.message.id == message.id
            
            while True:
                try:
                    reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
                    
                    if str(reaction.emoji) == "▶️" and current_page < len(pages) - 1:
                        current_page += 1
                        embed = self._create_flags_embed(pages[current_page], current_page, len(pages))
                        await message.edit(embed=embed)
                        await message.remove_reaction(reaction, user)
                        
                    elif str(reaction.emoji) == "◀️" and current_page > 0:
                        current_page -= 1
                        embed = self._create_flags_embed(pages[current_page], current_page, len(pages))
                        await message.edit(embed=embed)
                        await message.remove_reaction(reaction, user)
                        
                except asyncio.TimeoutError:
                    break
    
    def _create_flags_embed(self, flags_page, current_page, total_pages):
        """Creates an embed for a page of flags"""
        embed = discord.Embed(
            title="Translation Flag Reactions",
            description="React to messages with these flags to translate them",
            color=discord.Color(CONFIG['embed_color'])
        )
        
        for flag, lang_code in flags_page:
            lang_name = get_language_name(lang_code)
            embed.add_field(name=f"{flag} {lang_name}", value=f"Code: `{lang_code}`", inline=True)
            
        embed.set_footer(text=f"Page {current_page + 1}/{total_pages} | React with a flag to translate messages")
        return embed

async def setup(bot):
    await bot.add_cog(ReactionTranslate(bot))
