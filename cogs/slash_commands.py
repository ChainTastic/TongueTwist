import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import Optional, List

from config import CONFIG, LANGUAGES, LANGUAGE_TO_FLAG
from database import db
from translation import translation_service
from utils.language_utils import get_language_name, get_language_choices

logger = logging.getLogger('discord')

class SlashCommands(commands.Cog):
    """Handles slash commands for translation"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="translate", description="Translate text to another language")
    @app_commands.describe(
        text="The text to translate",
        target="The target language (default: your preferred language)",
        source="The source language (default: auto-detect)",
        private="Whether to show the translation only to you (default: False)"
    )
    @app_commands.choices(
        target=get_language_choices(),
        source=get_language_choices(include_auto=True)
    )
    async def translate(
        self, 
        interaction: discord.Interaction, 
        text: str, 
        target: Optional[str] = None, 
        source: Optional[str] = None,
        private: Optional[bool] = False
    ):
        """Translate text to another language with a slash command"""
        await interaction.response.defer(ephemeral=private)
        
        try:
            # If target language is not specified, use the user's preferred language
            if not target:
                target_lang = await db.get_user_language(interaction.user.id)
            else:
                target_lang = target
            
            # Detect source language if not specified
            if not source or source == "auto":
                source_lang = await translation_service.detect_language(text)
            else:
                source_lang = source
            
            # No need to translate if the source and target languages are the same
            if source_lang == target_lang:
                await interaction.followup.send(
                    f"⚠️ The text is already in {get_language_name(target_lang)} ({target_lang}).",
                    ephemeral=private
                )
                return
            
            # Translate the text
            translated_text = await translation_service.translate(text, target_lang, source_lang)
            
            # Create embed
            embed = discord.Embed(
                title="Translation",
                description=translated_text,
                color=discord.Color(CONFIG['embed_color'])
            )
            
            source_flag = LANGUAGE_TO_FLAG.get(source_lang, "🌐")
            target_flag = LANGUAGE_TO_FLAG.get(target_lang, "🌐")
            
            embed.add_field(
                name=f"{source_flag} Original ({get_language_name(source_lang)})",
                value=text[:1024],
                inline=False
            )
            
            embed.set_footer(
                text=f"Translated from {get_language_name(source_lang)} to {get_language_name(target_lang)}"
            )
            
            await interaction.followup.send(embed=embed, ephemeral=private)
            
        except Exception as e:
            logger.error(f"Error in translate command: {e}")
            await interaction.followup.send(
                "❌ An error occurred during translation. Please try again later.",
                ephemeral=True
            )
    
    @app_commands.command(name="setlanguage", description="Set your preferred language for translations")
    @app_commands.describe(language="Your preferred language")
    @app_commands.choices(language=get_language_choices())
    async def set_language(self, interaction: discord.Interaction, language: str):
        """Set your preferred language for translations"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            await db.set_user_language(interaction.user.id, language)
            
            flag = LANGUAGE_TO_FLAG.get(language, "🌐")
            language_name = get_language_name(language)
            
            await interaction.followup.send(
                f"✅ Your preferred language has been set to {flag} {language_name} (`{language}`).",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error in setlanguage command: {e}")
            await interaction.followup.send(
                "❌ An error occurred while setting your language. Please try again later.",
                ephemeral=True
            )
    
    @app_commands.command(name="language", description="Show your current preferred language")
    async def show_language(self, interaction: discord.Interaction):
        """Show your current preferred language"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            language = await db.get_user_language(interaction.user.id)
            flag = LANGUAGE_TO_FLAG.get(language, "🌐")
            language_name = get_language_name(language)
            
            await interaction.followup.send(
                f"Your current preferred language is {flag} {language_name} (`{language}`).",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error in language command: {e}")
            await interaction.followup.send(
                "❌ An error occurred while retrieving your language. Please try again later.",
                ephemeral=True
            )
    
    @app_commands.command(name="languages", description="Show available languages for translation")
    async def languages(self, interaction: discord.Interaction):
        """Show available languages for translation"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Create language list
            languages_text = ""
            for lang_code in sorted(set(LANGUAGES.values())):
                flag = LANGUAGE_TO_FLAG.get(lang_code, "🌐")
                language_name = get_language_name(lang_code)
                languages_text += f"{flag} {language_name} (`{lang_code}`)\n"
            
            # Create embed
            embed = discord.Embed(
                title="Available Languages",
                description=languages_text,
                color=discord.Color(CONFIG['embed_color'])
            )
            
            embed.set_footer(text="Use /setlanguage to set your preferred language")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Error in languages command: {e}")
            await interaction.followup.send(
                "❌ An error occurred while retrieving languages. Please try again later.",
                ephemeral=True
            )
    
    @commands.command(name="sync", hidden=True)
    @commands.is_owner()
    async def sync(self, ctx):
        """Sync slash commands (owner only)"""
        try:
            await self.bot.tree.sync()
            await ctx.send("✅ Slash commands synced.")
        except Exception as e:
            logger.error(f"Error syncing slash commands: {e}")
            await ctx.send(f"❌ Error syncing slash commands: {e}")

async def setup(bot):
    await bot.add_cog(SlashCommands(bot))
