from typing import List, Dict, Optional
from discord import app_commands

from config import LANGUAGES

# Language names mapping (ISO 639-1 code to English language name)
LANGUAGE_NAMES = {
    'en': 'English',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'it': 'Italian',
    'pt': 'Portuguese',
    'ru': 'Russian',
    'ja': 'Japanese',
    'ko': 'Korean',
    'zh-CN': 'Chinese (Simplified)',
    'zh-TW': 'Chinese (Traditional)',
    'ar': 'Arabic',
    'hi': 'Hindi',
    'tr': 'Turkish',
    'nl': 'Dutch',
    'sv': 'Swedish',
    'pl': 'Polish',
    'id': 'Indonesian',
    'th': 'Thai',
    'vi': 'Vietnamese',
    # Add more languages as needed
}

def get_language_name(language_code: str) -> str:
    """Get the English name of a language from its ISO 639-1 code"""
    return LANGUAGE_NAMES.get(language_code, language_code)

def get_language_choices(include_auto: bool = False) -> List[app_commands.Choice[str]]:
    """Get a list of language choices for Discord slash commands"""
    choices = []
    
    # Add auto-detect option if requested
    if include_auto:
        choices.append(app_commands.Choice(name="Auto-detect", value="auto"))
    
    # Add all languages
    for lang_code in sorted(set(LANGUAGES.values())):
        choices.append(app_commands.Choice(
            name=get_language_name(lang_code), 
            value=lang_code
        ))
    
    return choices

def is_rtl_language(language_code: str) -> bool:
    """Check if a language is written right-to-left"""
    rtl_languages = ['ar', 'he', 'fa', 'ur']
    return language_code in rtl_languages
