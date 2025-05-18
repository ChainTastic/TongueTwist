import discord
from discord.ext import commands
import logging
import asyncio
from typing import Dict, List, Union

from config import CONFIG, LANGUAGES
from database import db
from translation import translation_service
from utils.message_utils import send_translated_message

logger = logging.getLogger('discord')

class AutoTranslate(commands.Cog):
    """Automatically translates messages in channels where auto-translate is enabled"""
    
    def __init__(self, bot):
        self.bot = bot
        self.message_cache = {}  # Store original messages that have been translated
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listen for messages and auto-translate if necessary"""
        # Don't process messages from bots (including self)
        if message.author.bot:
            return
            
        # Only process guild messages (not DMs)
        if not message.guild:
            return
            
        # Check if auto-translate is enabled for this guild
        auto_translate_enabled = await db.get_guild_auto_translate(message.guild.id)
        if not auto_translate_enabled:
            return
            
        # Check if auto-translate is enabled for this channel
        auto_translate_channels = await db.get_guild_channels_auto_translate(message.guild.id)
        if str(message.channel.id) not in auto_translate_channels:
            return
            
        # Get message content
        content = message.content
        if not content or len(content.strip()) == 0:
            return
            
        try:
            # Detect the language of the message
            source_lang = await translation_service.detect_language(content)
            
            # Get members who will receive translated messages
            members = [member for member in message.channel.members if not member.bot]
            
            # Track translations to avoid duplicates
            translations = {}
            
            # Translate for each member with a different language preference
            for member in members:
                # Get member's preferred language
                target_lang = await db.get_user_language(member.id)
                
                # Skip if member's language is the same as source, or already translated
                if target_lang == source_lang or target_lang in translations:
                    continue
                    
                # Translate the message
                translated_text = await translation_service.translate(content, target_lang, source_lang)
                translations[target_lang] = translated_text
                
                # Store translation in database for future reference
                await db.add_message_translation(message.id, target_lang, translated_text)
            
            # Send notifications for available translations if any were made
            if translations:
                # Add original message to cache
                self.message_cache[message.id] = {
                    'original': content,
                    'source_lang': source_lang,
                    'translations': translations
                }
                
                # Add a reaction to indicate translation is available
                await message.add_reaction('🌐')
                
                # Store original message reference
                await db.add_message_translation(message.id, source_lang, content)


                # Replace the original message with a translated version
                # for exemple : chaintastic (fr ➜ en)
                # APP
                #  — 11:31 PM
                # Good morning
                # Send translated messages to the channel
                for target_lang, translated_text in translations.items():
                    # Check if the translated text exceeds Discord's character limit
                    if len(translated_text) > CONFIG['max_message_length']:
                        # Split the message into chunks
                        chunks = [
                            translated_text[i:i + CONFIG['max_message_length']]
                            for i in range(0, len(translated_text), CONFIG['max_message_length'])
                        ]
                        for chunk in chunks:
                            await send_translated_message(
                                channel=message.channel,
                                original_message=message,
                                translated_text=chunk,
                                target_lang=target_lang
                            )
                    else:
                        await send_translated_message(
                            channel=message.channel,
                            original_message=message,
                            translated_text=translated_text,
                            target_lang=target_lang
                        )
                # Send a message to the channel indicating translations are available
                embed = discord.Embed(
                    title="Translations Available",
                    description="Click the 🌐 reaction to receive translations in your preferred language.",
                    color=discord.Color(CONFIG['embed_color'])
                )
                embed.add_field(name="Original Message", value=content[:1024])
                embed.set_footer(text=f"Translated from {source_lang} to {', '.join(translations.keys())}")
                await message.channel.send(embed=embed)
            else:
                # No translations were made, so just send the original message
                embed = discord.Embed(
                    title="Original Message",
                    description=content[:1024],
                    color=discord.Color(CONFIG['embed_color'])
                )
                embed.set_footer(text=f"Language: {source_lang}")
                await message.channel.send(embed=embed)
        except discord.Forbidden:
            # Handle permission errors (e.g., bot cannot send messages)
            logger.error(f"Permission error: {message.channel.name} - {message.content}")
        except discord.NotFound:
            # Handle message not found errors
            logger.error(f"Message not found: {message.channel.name} - {message.content}")
        except discord.HTTPException as e:
            # Handle Discord API errors
            logger.error(f"Discord API error: {e}")
        except asyncio.TimeoutError:
            # Handle timeout errors
            logger.error("Timeout error while processing message.")
        except KeyError as e:
            # Handle missing keys in translations
            logger.error(f"Key error in translations: {e}")
        except ValueError as e:
            # Handle value errors (e.g., invalid language codes)
            logger.error(f"Value error in translations: {e}")
        except Exception as e:
            logger.error(f"Error in auto-translate: {e}")
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Listen for reactions to auto-translated messages"""
        # Don't process reactions from bots
        if payload.user_id == self.bot.user.id:
            return
            
        # Only process 🌐 reactions
        if str(payload.emoji) != '🌐':
            return
            
        try:
            # Get the channel and message
            channel = self.bot.get_channel(payload.channel_id)
            if not channel:
                return
                
            message = await channel.fetch_message(payload.message_id)
            if not message:
                return
                
            # Check if message is in cache or in database
            cached_message = self.message_cache.get(message.id)
            if cached_message:
                # Get user's preferred language
                user = await self.bot.fetch_user(payload.user_id)
                target_lang = await db.get_user_language(user.id)
                
                # Get translation if it exists
                translation = cached_message['translations'].get(target_lang)
                if not translation:
                    # Translate now if not already translated
                    translation = await translation_service.translate(
                        cached_message['original'], 
                        target_lang, 
                        cached_message['source_lang']
                    )
                    cached_message['translations'][target_lang] = translation
                    await db.add_message_translation(message.id, target_lang, translation)
                
                # Send the translation as a DM
                embed = discord.Embed(
                    title="Message Translation",
                    description=translation,
                    color=discord.Color(CONFIG['embed_color'])
                )
                embed.add_field(name="Original", value=cached_message['original'][:1024])
                embed.add_field(
                    name="Channel", 
                    value=f"[Jump to message]({message.jump_url})", 
                    inline=False
                )
                embed.set_footer(text=f"Translated from {cached_message['source_lang']} to {target_lang}")
                
                try:
                    await user.send(embed=embed)
                except discord.Forbidden:
                    # Cannot DM the user
                    pass
            else:
                # Try to get translations from database
                translations = await db.get_message_translations(message.id)
                if translations:
                    # Get user's preferred language
                    user = await self.bot.fetch_user(payload.user_id)
                    target_lang = await db.get_user_language(user.id)
                    
                    # Get translation if it exists
                    translation = translations.get(target_lang)
                    if translation:
                        # Send the translation as a DM
                        embed = discord.Embed(
                            title="Message Translation",
                            description=translation,
                            color=discord.Color(CONFIG['embed_color'])
                        )
                        embed.add_field(name="Original", value=message.content[:1024])
                        embed.add_field(
                            name="Channel", 
                            value=f"[Jump to message]({message.jump_url})", 
                            inline=False
                        )
                        embed.set_footer(text=f"Translated to {target_lang}")
                        
                        try:
                            await user.send(embed=embed)
                        except discord.Forbidden:
                            # Cannot DM the user
                            pass
        except Exception as e:
            logger.error(f"Error handling reaction for auto-translated message: {e}")
    
    @commands.group(name="autotranslate", aliases=["at"], invoke_without_command=True)
    @commands.has_permissions(manage_channels=True)
    async def auto_translate(self, ctx):
        """Manage auto-translation settings"""
        enabled = await db.get_guild_auto_translate(ctx.guild.id)
        channels = await db.get_guild_channels_auto_translate(ctx.guild.id)
        
        # Format channel list
        channel_list = ""
        for channel_id in channels:
            channel = ctx.guild.get_channel(int(channel_id))
            if channel:
                channel_list += f"- {channel.mention}\n"
        
        if not channel_list:
            channel_list = "No channels configured"
        
        # Create embed
        embed = discord.Embed(
            title="Auto-Translation Settings",
            description=f"Auto-translation is currently **{'enabled' if enabled else 'disabled'}** for this server.",
            color=discord.Color(CONFIG['embed_color'])
        )
        embed.add_field(name="Configured Channels", value=channel_list)
        embed.add_field(
            name="Commands", 
            value=(
                f"`{ctx.prefix}autotranslate enable` - Enable auto-translation\n"
                f"`{ctx.prefix}autotranslate disable` - Disable auto-translation\n"
                f"`{ctx.prefix}autotranslate add #channel` - Add a channel\n"
                f"`{ctx.prefix}autotranslate remove #channel` - Remove a channel"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @auto_translate.command(name="enable")
    @commands.has_permissions(manage_channels=True)
    async def auto_translate_enable(self, ctx):
        """Enable auto-translation for the server"""
        await db.set_guild_auto_translate(ctx.guild.id, True)
        await ctx.send("✅ Auto-translation enabled for this server.")
    
    @auto_translate.command(name="disable")
    @commands.has_permissions(manage_channels=True)
    async def auto_translate_disable(self, ctx):
        """Disable auto-translation for the server"""
        await db.set_guild_auto_translate(ctx.guild.id, False)
        await ctx.send("✅ Auto-translation disabled for this server.")
    
    @auto_translate.command(name="add")
    @commands.has_permissions(manage_channels=True)
    async def auto_translate_add(self, ctx, channel: discord.TextChannel):
        """Add a channel to auto-translation"""
        await db.add_guild_channel_auto_translate(ctx.guild.id, channel.id)
        await ctx.send(f"✅ Auto-translation enabled for {channel.mention}.")
    
    @auto_translate.command(name="remove")
    @commands.has_permissions(manage_channels=True)
    async def auto_translate_remove(self, ctx, channel: discord.TextChannel):
        """Remove a channel from auto-translation"""
        await db.remove_guild_channel_auto_translate(ctx.guild.id, channel.id)
        await ctx.send(f"✅ Auto-translation disabled for {channel.mention}.")

async def setup(bot):
    await bot.add_cog(AutoTranslate(bot))
